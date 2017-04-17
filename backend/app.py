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
import yaml, collections

from flask import Flask, send_from_directory, request, jsonify, json
from flask_cors import CORS
from flask_socketio import SocketIO

import util

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

socketio_logger = logging.getLogger('socketio')
socketio_logger.setLevel(logging.WARNING)

app = Flask(__name__, static_url_path='')
CORS(app)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@app.route('/')
def root():
    return send_from_directory('static', 'index.html')

import random
from collections import OrderedDict
from model import *

SERVICES = OrderedDict()
WORK = os.path.join(os.path.dirname(__file__), "work")

LOG = util.Worker()

import sys, traceback
from eventlet.queue import Queue

SYNC_QUEUE = Queue()

def worker():
    while True:
        reason = SYNC_QUEUE.get()
        try:
            logging.info("waking up because %s" % reason)
            sync()
        except:
            logging.error(traceback.format_exc())

def trigger(reason):
    SYNC_QUEUE.put(reason)

def sync():
    r = requests.get("https://api.github.com/orgs/twitface/repos")
    json = r.json()
    new = OrderedDict()
    for repo in json:
        name = repo["name"]
        clone_url = repo["clone_url"]
        owner = repo["owner"]["login"]
        svc = Service(name, owner)
        svc.clone_url = clone_url
        new[svc.name] = svc

    for svc in SERVICES.values()[:]:
        if svc.name not in new:
            del SERVICES[svc.name]
            socketio.emit('deleted', svc.json())
            shutil.rmtree(os.path.join(WORK, svc.name), ignore_errors=True)
        else:
            new[svc.name] = svc.stats

    redeploy = []
    for svc in new.values():
        SERVICES[svc.name] = svc
        socketio.emit('dirty', svc.json())
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
        if result.code: continue
        redeploy.append((svc, wdir))

    for svc, wdir in redeploy:
        deploy(svc, wdir)

def dockerize(name, version, source, wdir):
    dockerfile = os.path.join(wdir, source)
    base = os.path.dirname(dockerfile)

    image = "gcr.io/datawire-sandbox/%s:%s" % (name, version)
    result = LOG.call("docker", "build", ".", "-t", image, cwd=base)
    if result.code: return None
    pwfile = os.environ.get("DOCKER_PASSWORD_FILE", "/etc/secrets/docker_password")
    LOG.call("docker", "login", "-u", "_json_key", "-p", open(pwfile).read(), "gcr.io")
    result = LOG.call("docker", "push", image)
    if result.code: return None
    return image

def deploy(svc, wdir):
    result = LOG.call("git", "rev-parse", "HEAD", cwd=wdir)
    if result.code: return
    svc.version = result.output.strip()
    svc_yaml = os.path.join(wdir, "service.yaml")
    if os.path.exists(svc_yaml):
        with open(svc_yaml) as f:
            svc_info = yaml.load(f)
    else:
        svc_info = {"containers": [{"name": svc.name, "source": "Dockerfile"}]}

    containers = svc_info["containers"]

    images = OrderedDict()
    for info in containers:
        logging.info("dockerizing %s" % info)
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

GITHUB = []

@app.route('/githook', methods=['POST'])
def githook():
    GITHUB.append(request.json)
    trigger('github hook')
    return ('', 204)

@app.route('/gitevents')
def gitevents():
    return (jsonify(GITHUB), 200)

@app.route('/sync')
def do_sync():
    trigger('manual trigger')
    return ('', 204)

@app.route('/worklog')
def worklog():
    return (jsonify([r.json() for r in LOG.log]), 200)

@app.route('/create')
def create():
    name = request.args["name"]
    owner = request.args["owner"]
    service = Service(name, owner)
    SERVICES[name] = service
    socketio.emit('dirty', service.json())
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
    trigger('startup')
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
    eventlet.spawn(worker)

if __name__ == "__main__":
    setup()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
