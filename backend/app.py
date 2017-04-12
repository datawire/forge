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

def sync():
    r = requests.get("https://api.github.com/orgs/twitface/repos")
    json = r.json()
    new = OrderedDict()
    for repo in json:
        name = repo["name"]
        clone_url = repo["clone_url"]
        owner = repo["owner"]["login"]
        svc = Service(name, owner)
        new[svc.name] = svc

    for svc in SERVICES.values()[:]:
        if svc.name not in new:
            del SERVICES[svc.name]
            socketio.emit('deleted', svc.json())
    for svc in new.values():
        SERVICES[svc.name] = svc
        socketio.emit('dirty', svc.json())

GITHUB = []

@app.route('/githook', methods=['POST'])
def githook():
    GITHUB.append(request.json)
    sync()
    return ('', 204)

@app.route('/gitevents')
def gitevents():
    sync()
    return (jsonify(GITHUB), 200)

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
    sync()
    print('spawning')
    eventlet.spawn(background)

if __name__ == "__main__":
    setup()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
