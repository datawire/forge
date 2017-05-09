# Copyright 2015 datawire. All rights reserved.
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

import requests, sys, time
from eventlet.green.subprocess import Popen, STDOUT, PIPE

class Workitem(object):

    def __init__(self, stream):
        self.stream = stream
        self.created = time.time()
        self.started = None
        self.updated = None
        self.finished = None

    def pending(self):
        return self.started is None

    def running(self):
        return self.started is not None and self.finished is None

    def start(self):
        sys.stdout.write("%s: %s" % (self.__class__.__name__, self.start_summary))
        sys.stdout.flush()
        self.started = time.time()
        self.updated = self.started
        self.stream.poke()

    def update(self):
        self.updated = time.time()
        self.stream.poke()

    def finish(self):
        sys.stdout.write(" -> %s\n" % self.finish_summary)
        sys.stdout.flush()
        self.updated = time.time()
        self.finished = time.time()
        self.stream.poke()

def elide(t):
    if isinstance(t, Secret):
        return "<ELIDED>"
    elif isinstance(t, Elidable):
        return t.elide()
    else:
        return t

class Secret(str):
    pass

class Elidable(object):

    def __init__(self, *parts):
        self.parts = parts

    def elide(self):
        return "".join(elide(p) for p in self.parts)

    def __str__(self):
        return "".join(str(p) for p in self.parts)

class Command(Workitem):

    def __init__(self, stream, command, context):
        Workitem.__init__(self, stream)
        self.command = command
        self.context = context
        self.output = None
        self.code = None

    @property
    def start_summary(self):
        return " ".join(elide(a) for a in self.command)

    @property
    def finish_summary(self):
        if self.code == 0:
            return "OK"
        else:
            return "BAD[%s]" % self.code

    def execute(self):
        self.output = ""
        self.start()
        p = Popen(tuple(str(a) for a in self.command), stderr=STDOUT, stdout=PIPE, **self.context)
        for line in p.stdout:
            self.output += line
            self.update()
        p.wait()
        self.code = p.returncode
        self.finish()

    def json(self):
        return {"command": tuple(elide(t) for t in self.command),
                "context": self.context,
                "code": self.code,
                "output": self.output,
                "started": self.started,
                "finished": self.finished}

class Request(Workitem):

    def __init__(self, stream, url, context):
        Workitem.__init__(self, stream)
        self.url = url
        self.context = context
        self.expected = context.pop("expected", ())
        self.response = None

    @property
    def start_summary(self):
        return elide(self.url)

    @property
    def finish_summary(self):
        if self.response.ok:
            return "OK"
        elif self.response.status_code in self.expected:
            return "OK[%s]" % self.response.status_code
        else:
            return "BAD[%s]" % self.response.status_code

    def execute(self):
        self.start()
        self.response = requests.get(str(self.url), **self.context)
        self.finish()

class Workstream(object):

    def __init__(self, on_update = lambda: None):
        self.items = []
        self.poke = on_update

    def command(self, *args, **kwargs):
        result = Command(self, args, kwargs)
        self.items.append(result)
        return result

    def call(self, *args, **kwargs):
        cmd = self.command(*args, **kwargs)
        cmd.execute()
        if cmd.code == 0:
            return cmd
        else:
            raise Exception(cmd.output)

    def request(self, url, **kwargs):
        result = Request(self, url, kwargs)
        self.items.append(result)
        return result

    def get(self, url, **kwargs):
        req = self.request(url, **kwargs)
        req.execute()
        response = req.response
        if not response.ok and response.status_code not in req.expected:
            raise Exception(response.content)
        return response

    def json(self):
        return [i.json() for i in self.items]
