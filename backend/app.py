#!/usr/bin/python

import eventlet
eventlet.monkey_patch()

from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import time
import yaml

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

def populate():
    for svc in (Service('auth', 'alice@org.io'),
                Service('users', 'bob@org.io'),
                Service('search', 'carol@org.io'),
                Service('ratings', 'dan@org.io')):
        SERVICES[svc.name] = svc


@app.route("/deployments/<deployment_id>")
def get_deployment(deployment_id):
    return jsonify({
        'id': deployment_id,
        'service': service_spec,
        'fabric':  {}
    })


@app.route('/create')
def create():
    name = request.args["name"]
    owner = request.args["owner"]
    service = Service(name, owner)
    SERVICES[name] = service
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
                service = random.choice(SERVICES.values())
                service.stats = sim(service.stats)
                socketio.emit('dirty', service.json())
        time.sleep(1.0)

def setup():
    populate()
    print('spawning')
    eventlet.spawn(background)

if __name__ == "__main__":
    setup()
    socketio.run(app, host="0.0.0.0", port=5000)
