#!/usr/bin/python

import eventlet
eventlet.monkey_patch()

import logging
import socket
import time

import dpath
import os
import requests
import shutil
import stat
import yaml, collections

from flask import Flask, send_from_directory, request, jsonify, json
from flask_cors import CORS
from flask_socketio import SocketIO

_mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

def dict_representer(dumper, data):
    return dumper.represent_dict(data.iteritems())

def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))

yaml.add_representer(collections.OrderedDict, dict_representer)
yaml.add_constructor(_mapping_tag, dict_constructor)

try:
    MyHostName = socket.gethostname()
    MyResolvedName = socket.gethostbyname(socket.gethostname())
except socket.gaierror:
    MyHostName = "unknown"
    MyResolvedName = "unknown"

logging.basicConfig(
    # filename=logPath,
    level=logging.INFO, # if appDebug else logging.INFO,
    format="%(asctime)s skunkworks 0.0.1 %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logging.info("blackbird initializing on %s (resolved %s)" % (MyHostName, MyResolvedName))

NOISY = ('socketio', 'engineio')
for n in NOISY:
    logging.getLogger(n).setLevel(logging.WARNING)

app = Flask(__name__, static_url_path='')
CORS(app)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@app.route('/')
def root():
    return send_from_directory('static', 'index.html')

import random, workstream
from collections import OrderedDict
from model import *

SERVICES = OrderedDict()
WORK = os.path.join(os.path.dirname(__file__), "work")
with open(os.environ.get("DOCKER_PASSWORD_FILE", "/etc/secrets/docker_password")) as f:
    DOCKER_PASSWORD = f.read()

def emitwork():
    socketio.emit('work', LOG.json())

LOG = workstream.Workstream(emitwork)

import sys, traceback
from eventlet.queue import Queue

WORK_QUEUE = Queue()

def worker():
    while True:
        try:
            fun, args = WORK_QUEUE.get()
            logging.info("dispatching %s(%s)" % (fun.__name__, ", ".join(repr(a) for a in args)))
            fun(*args)
        except:
            logging.error(traceback.format_exc())

def schedule(fun, *args):
    WORK_QUEUE.put((fun, args))

def remove_service(name):
    del SERVICES[svc.name]
    socketio.emit('deleted', svc.json())
    shutil.rmtree(os.path.join(WORK, svc.name), ignore_errors=True)

def update_service(svc):
    if not os.path.exists(WORK):
        os.makedirs(WORK)
    wdir = os.path.join(WORK, svc.name)
    clone = False
    if (os.path.exists(wdir)):
        result = LOG.call("git", "pull", cwd=wdir)
        if result.code:
            shutil.rmtree(wdir, ignore_errors=True)
            clone = True
    else:
        clone = True
    if clone:
        result = LOG.call("git", "clone", svc.clone_url, "-o", svc.name, cwd=WORK)
    if result.code == 0:

        descriptor_path = os.path.join(wdir, "service.yaml")
        if os.path.exists(descriptor_path):
            with open(descriptor_path) as f:
                descriptor = yaml.load(f)
            svc.descriptor = descriptor
            SERVICES[svc.name] = svc
            socketio.emit('dirty', svc.json())

            if not descriptor.get("template", False):
                schedule(deploy, svc, wdir)

def sync(reason):
    r = requests.get("https://api.github.com/orgs/twitface/repos")
    repos = r.json()
    new = OrderedDict()
    for repo in repos:
        name = repo["name"]
        clone_url = repo["clone_url"]
        owner = repo["owner"]["login"]
        svc = Service(name, owner)
        svc.clone_url = clone_url
        new[svc.name] = svc

    for svc in SERVICES.values()[:]:
        if svc.name not in new:
            schedule(remove_service, svc.name)
        else:
            new[svc.name].stats = svc.stats

    for svc in new.values():
        schedule(update_service, svc)

def image_exists(name, version):
    result = LOG.call("curl", "-s", "-u", "_json_key:%s" % DOCKER_PASSWORD,
                      "https://gcr.io/v2/datawire-sandbox/%s/manifests/%s" % (name, version))
    if result.code: return False
    stuff = json.loads(result.output)
    if "errors" in stuff and stuff["errors"][0]["code"] == "MANIFEST_UNKNOWN":
        return False
    return True

def dockerize(name, version, source, wdir):
    dockerfile = os.path.join(wdir, source)
    base = os.path.dirname(dockerfile)
    image = "gcr.io/datawire-sandbox/%s:%s" % (name, version)
    if image_exists(name, version):
        logging.info("%s exists" % image)
        return image

    logging.info("dockerizing %s, %s -> %s" % (name, version, image))
    if not os.path.exists(dockerfile):
        logging.error("no such file: %s" % source)
        return None

    result = LOG.call("docker", "build", ".", "-t", image, cwd=base)
    if result.code: return None
    LOG.call("docker", "login", "-u", "_json_key", "-p", DOCKER_PASSWORD, "gcr.io")
    result = LOG.call("docker", "push", image)
    if result.code: return None
    return image

AMBASSADOR_URL = "http://%s:%s" % (os.environ["AMBASSADOR_SERVICE_HOST"], os.environ["AMBASSADOR_SERVICE_PORT"])

def route_exists(name, prefix):
    result = LOG.call("curl", "-s", "%s/ambassador/service/%s" % (AMBASSADOR_URL, name))
    if result.code:
        return False
    stuff = json.loads(result.output)
    return stuff["ok"]

def create_route(name, prefix):
    LOG.call("curl", "-s", "-XPOST", "-H", "Content-Type: application/json",
             "-d", '{ "prefix": "/%s/" }' % prefix,
             "%s/ambassador/service/%s" % (AMBASSADOR_URL, name))

def deploy(svc, wdir):
    result = LOG.call("git", "rev-parse", "HEAD", cwd=wdir)
    if result.code: return
    svc.version = result.output.strip()

    if "containers" in svc.descriptor:
        containers = svc.descriptor["containers"]
    else:
        containers = [{"name": svc.name, "source": "Dockerfile"}]

    images = OrderedDict()
    for info in containers:
        image = dockerize(info["name"], svc.version, info["source"], wdir)
        if image is None:
            return
        images[info["name"]] = image

    svc.images = images

    deployment = os.path.join(wdir, "deployment")
    if (os.path.exists(deployment)):
        metadata = os.path.join(wdir, "metadata.yaml")
        with open(metadata, "write") as f:
            yaml.dump(svc.json(), f)
        result = LOG.call("./deployment", "metadata.yaml", cwd=wdir)
        if result.code: return
        deployment_yaml = os.path.join(wdir, "deployment.yaml")
        with open(deployment_yaml, "write") as y:
            y.write(result.output)
        result = LOG.call("kubectl", "apply", "-f", "deployment.yaml", cwd=wdir)

    if "prefix" in svc.descriptor:
        name, prefix = svc.name, svc.descriptor["prefix"]
        if not route_exists(name, prefix):
            create_route(name, prefix)

GITHUB = []

@app.route('/githook', methods=['POST'])
def githook():
    GITHUB.append(request.json)
    schedule(sync, 'github hook')
    return ('', 204)

@app.route('/gitevents')
def gitevents():
    return (jsonify(GITHUB), 200)

@app.route('/sync')
def do_sync():
    schedule(sync, 'manual sync')
    return ('', 204)

@app.route('/worklog')
def worklog():
    return (jsonify(LOG.json()), 200)

KEY="435e0fbfd363b23a4bbe6769e37519df87dabef0"

@app.route('/create')
def create():
    logging.info(request.args)
    template = request.args["template"]
    tdir = os.path.join(WORK, template)
    name = request.args["__PROJECT_NAME__"]
    wdir = os.path.join(WORK, "__INSTANTIATIONS__", name)

    for root, dirs, files in os.walk(tdir):
        dirs.remove(".git")
        copy = root.replace(tdir, wdir)
        if not os.path.exists(copy):
            os.makedirs(copy)
            for fname in files:
                orig = os.path.join(root, fname)
                with open(orig) as f:
                    if fname == "service.yaml":
                        obj = yaml.load(f)
                        del obj['template']
                        content = yaml.dump(obj)
                    else:
                        content = f.read()
                munged = content
                for key in request.args:
                    if key.startswith("__") and key.endswith("__"):
                        munged = munged.replace(str(key), str(request.args[key]))
                dup = os.path.join(copy, fname)
                with open(dup, "write") as f:
                    f.write(munged)
                os.chmod(dup, os.stat(orig).st_mode)

    LOG.call("git", "init", cwd=wdir)
    LOG.call("git", "add", ".", cwd=wdir)
    LOG.call("git", "config", "user.name", "Rafael Schloming", cwd=wdir)
    LOG.call("git", "config", "user.email", "rhs@datawire.io", cwd=wdir)
    LOG.call("git", "commit", "-m", "service creation", cwd=wdir)

    LOG.call("curl", "-s", "-XPOST", "-H", "Authorization: token %s" % KEY, "https://api.github.com/orgs/twitface/repos",
             "-d", '{"name": "%s"}' % name)

    LOG.call("git", "remote", "add", "origin", "https://%s:x-oauth-basic@github.com/twitface/%s.git" % (KEY, name), cwd=wdir)
    LOG.call("git", "push", "-u", "origin", "master", cwd=wdir)

    return ('', 204)

@app.route('/update')
def update():
    name = request.args["name"]
    service = SERVICES[name]
    descriptor = json.loads(request.args["descriptor"])
    artifact = descriptor["artifact"]
    resources = [Resource(name=r["name"], type=r["type"])
                 for r in descriptor["resources"]]
    service.add(Descriptor(artifact=artifact, resources=resources))
    socketio.emit('dirty', service.json())
    return ('', 204)

@app.route('/get')
def get():
    return (jsonify([s.json() for s in SERVICES.values()]), 200)

def next_num(n):
    return (n + random.uniform(0, 10))*random.uniform(0.9, 1.1)

def sim(stats):
    return Stats(good=next_num(stats.good), bad=0.5*next_num(stats.bad), slow=0.5*next_num(stats.slow))

def background():
    schedule(sync, 'startup')
    count = 0
    while True:
        count = count + 1
        socketio.emit('message', '%s Mississippi' % count, broadcast=True)
        if SERVICES:
            nup = random.randint(0, len(SERVICES))
            for i in range(nup):
                service = random.choice(list(SERVICES.values()))
                service.stats = sim(service.stats)
                socketio.emit('dirty', service.json())
        time.sleep(1.0)

def setup():
    print('spawning')
    eventlet.spawn(background)
    for i in range(10):
        eventlet.spawn(worker)

if __name__ == "__main__":
    setup()
    socketio.run(app, host="0.0.0.0", port=5000)
