# Copyright 2017 datawire. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import eventlet, logging, random, time
from flask import Flask, send_from_directory, request, jsonify, json, flash, redirect
from flask_cors import CORS
from flask_socketio import SocketIO

import util
from .dispatcher import Dispatcher
from .common import Stats

app = Flask(__name__, static_url_path='')
CORS(app)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

BAKER = None
WORK = Dispatcher()
SERVICES = []

@app.route('/')
def root():
    return send_from_directory('static', 'index.html')

@app.route('/get')
def get():
    return (jsonify([s.json() for s in SERVICES]), 200)

@app.route('/worklog')
def worklog():
    return (jsonify(BAKER.json()), 200)

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
    WORK.schedule(sync, 'manual sync')
    return ('', 204)

def set_services(services):
    names = set([s.name for s in services])

    global SERVICES

    for s in SERVICES:
        if s.name not in names:
            socketio.emit('deleted', s.name)

    SERVICES = services

def sync(reason):
    BAKER.pull()
    prototypes, services = BAKER.scan()
    set_services(prototypes + services)
    BAKER.bake()
    BAKER.push()
    BAKER.deploy()

def next_num(n):
    return (n + random.uniform(0, 10))*random.uniform(0.9, 1.1)

def sim(stats):
    return Stats(good=next_num(stats.good), bad=0.5*next_num(stats.bad), slow=0.5*next_num(stats.slow))

def background():
    WORK.schedule(sync, 'startup')
    count = 0
    while True:
        count = count + 1
        socketio.emit('message', '%s Mississippi' % count, broadcast=True)
        if SERVICES:
            nup = random.randint(0, len(SERVICES))
            for i in range(nup):
                service = random.choice(SERVICES)
                service.stats = sim(service.stats)
                socketio.emit('dirty', service.json())
        time.sleep(1.0)

def setup():
    logging.info('spawning')
    eventlet.spawn(background)
    for i in range(10):
        eventlet.spawn(WORK.work)

def serve(baker):
    global BAKER
    BAKER = baker
    util.setup_logging()
    setup()
    socketio.run(app, host="0.0.0.0", port=5000)
