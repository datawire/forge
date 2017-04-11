#!/usr/bin/python

import eventlet
eventlet.monkey_patch()

import logging
import socket
import time

import dpath
import yaml
import requests

from flask import Flask, send_from_directory, request, jsonify, json
from flask_cors import CORS
from flask_socketio import SocketIO

service_spec = yaml.load("""---
name: hellomd

artifact:
  type: docker
  registry: docker.io
  image: datawire/hellomd
  resolver:
    type: provided

update:
  strategy: rolling

network:
  frontends:
    - name: public
      type: external:load-balancer
      ports:
        - port: 80
          backend: api
  backends:
    - name: api
      port: 5001
      protocol: tcp

requires:
  - type: terraform
    alias: mydb
    name: postgresql96
    version: 1
    params:
      allocated_storage: 20
""")

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

logging.info("MCP initializing on %s (resolved %s)" % (MyHostName, MyResolvedName))

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

class RichStatus (object):
    def __init__(self, ok, **kwargs):
        self.ok = ok
        self.info = kwargs
        self.info['hostname'] = MyHostName
        self.info['resolvedname'] = MyResolvedName

    # Remember that __getattr__ is called only as a last resort if the key
    # isn't a normal attr.
    def __getattr__(self, key):
        return self.info.get(key)

    def __nonzero__(self):
        return self.ok

    def __str__(self):
        attrs = ["%=%s" % (key, self.info[key]) for key in sorted(self.info.keys())]
        astr = " ".join(attrs)

        if astr:
            astr = " " + astr

        return "<RichStatus %s%s>" % ("OK" if self else "BAD", astr)

    def toDict(self):
        d = { 'ok': self.ok }

        for key in self.info.keys():
            d[key] = self.info[key]

        return d

    @classmethod
    def fromError(self, error, **kwargs):
        kwargs['error'] = error
        return RichStatus(False, **kwargs)

    @classmethod
    def OK(self, **kwargs):
        return RichStatus(True, **kwargs)

def populate2():
    for svc in (Service('auth', 'alice@org.io'),
                Service('users', 'bob@org.io'),
                Service('search', 'carol@org.io'),
                Service('ratings', 'dan@org.io')):
        SERVICES[svc.name] = svc

def populate():
    SERVICES.clear()
    r = requests.get("https://api.github.com/orgs/twitface/repos")
    json = r.json()
    print json
    for repo in json:
        name = repo["name"]
        clone_url = repo["clone_url"]
        owner = repo["owner"]["login"]
        svc = Service(name, owner)
        SERVICES[svc.name] = svc

@app.route("/deployments/<deployment_id>")
def get_deployment(deployment_id):
    return jsonify({
        'id': deployment_id,
        'service': service_spec,
        'fabric':  {}
    })


GITHUB = []

@app.route('/githook', methods=['POST'])
def githook():
    GITHUB.append(request.json)
    populate()
    return ('', 204)

@app.route('/gitevents')
def gitevents():
    populate()
    return (jsonify(GITHUB), 200)

def dpath_get(obj, glob, default=None):
    try:
        return dpath.util.get(obj, glob)
    except KeyError:
        return default

def dpath_set(obj, glob, value):
    return dpath.util.new(obj, glob, value)

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

STATE = {}

@app.route('/state', methods=[ 'PUT', 'GET' ])
def handle_state_root():
    global STATE
    
    rc = RichStatus.fromError("impossible error")
    logging.debug("handle_state_root: method %s" % request.method)
    
    rc = RichStatus.fromError("impossible error")

    try:
        if request.method == 'GET':
            rc = RichStatus.OK(state=STATE)
        elif request.method == 'PUT':
            STATE = request.get_json(force=True)

            logging.debug('state now %s', STATE)

            rc = RichStatus.OK(state=STATE)
    except Exception as e:
        rc = RichStatus.fromError("%s all state failed: %s" % (request.method, e))

    return jsonify(rc.toDict())

@app.route('/state/<path:path>', methods=[ 'PUT', 'GET', 'DELETE' ])
def handle_state(path):
    rc = RichStatus.fromError("impossible error")

    try:
        if request.method == 'GET':
            rc = RichStatus.OK(state=dpath.util.search(STATE, path))
        elif request.method == 'PUT':
            value = request.get_json(force=True)

            dpath_set(STATE, path, value)

            logging.debug('state now %s', STATE)

            rc = RichStatus.OK(state=dpath.util.search(STATE, path))
        elif request.method == 'DELETE':
            try:
                dpath.util.delete(STATE, path)
                rc = RichStatus.OK(deleted=path)
            except dpath.exceptions.PathNotFound:
                rc = RichStatus.fromError("path %s not found to delete" % path)
    except Exception as e:
        rc = RichStatus.fromError("%s %s failed: %s" % (request.method, path, e))

    return jsonify(rc.toDict())

@app.route('/feedback', methods=[ 'POST' ])
def handle_feedback():
    rc = RichStatus.fromError("unsupported")

    logging.debug("feedback request: %s" % request.get_json(force=True))

    return jsonify(rc.toDict())

def next_num(n):
    return (n + random.uniform(0, 10))*random.uniform(0.9, 1.1)

def sim(stats):
    return Stats(good=next_num(stats.good), bad=0.5*next_num(stats.bad), slow=0.5*next_num(stats.slow))

def background():
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
    populate()
    print('spawning')
    eventlet.spawn(background)

if __name__ == "__main__":
    setup()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
