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

class WorkError(Exception): pass
class CommandError(WorkError): pass
class RequestError(WorkError): pass

class Workitem(object):

    def __init__(self, stream, context):
        self.stream = stream
        self.created = time.time()
        self.started = None
        self.updated = None
        self.finished = None
        self.expected = context.pop("expected", None) or ()
        self.verbose = context.pop("verbose", False)
        self.visible = context.pop("visible", True)

    def pending(self):
        return self.started is None

    def running(self):
        return self.started is not None and self.finished is None

    def start(self):
        self.started = time.time()
        self.updated = self.started
        self.stream.started(self)

    def update(self, output):
        self.updated = time.time()
        self.stream.updated(self, output)

    def finish(self):
        self.updated = time.time()
        self.finished = time.time()
        self.stream.finished(self)

    @property
    def ok(self):
        return self.code is not None and (self._is_ok() or self.code in self.expected)

    @property
    def finish_summary(self):
        if self._is_ok():
            return "OK"
        elif self.code in self.expected:
            return "OK[%s]" % self.code
        else:
            if self.code is None:
                return "ERR"
            else:
                return "ERR[%s]" % self.code

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
        Workitem.__init__(self, stream, context)
        self.command = command
        self.context = context
        self.output = None
        self.code = None

    def _is_ok(self):
        return self.code == 0

    @property
    def start_summary(self):
        return " ".join(elide(a) for a in self.command)

    def execute(self):
        self.output = ""
        self.start()

        try:
            p = Popen(tuple(str(a) for a in self.command), stderr=STDOUT, stdout=PIPE, **self.context)
        except OSError, e:
            self.output += str(e)
            self.code = 1
            self.finish()
            return

        try:
            for line in p.stdout:
                self.output += line
                self.update(line)
            p.wait()
        except OSError, e:
            self.output += str(e)

        self.code = p.returncode
        self.finish()

    def json(self):
        return {"command": tuple(elide(t) for t in self.command),
                "context": self.context,
                "code": self.code,
                "output": self.output,
                "started": self.started,
                "finished": self.finished}

class FakeResponse(object):

    def __init__(self, e):
        self.ok = False
        self.status_code = None
        self.content = str(e)

class Request(Workitem):

    def __init__(self, stream, url, context):
        Workitem.__init__(self, stream, context)
        self.url = url
        self.context = context
        self.response = None

    def _is_ok(self):
        return self.response is not None and self.response.ok

    @property
    def code(self):
        return self.response.status_code if self.response is not None else None

    @property
    def output(self):
        return self.response.content if self.response is not None else None

    @property
    def start_summary(self):
        return elide(self.url)

    def execute(self):
        self.start()
        try:
            self.response = requests.get(str(self.url), **self.context)
            self.update(self.response.content)
            self.finish()
        except requests.RequestException, e:
            self.response = FakeResponse(e)
            self.update(self.response.content)
            self.finish()
            raise WorkError(e)

    def json(self):
        return {"command": [elide(self.url)],
                "context": self.context,
                "code": self.code,
                "output": self.output,
                "started": self.started,
                "finished": self.finished}

class Workstream(object):

    def __init__(self):
        self.items = []

    def started(self, item):
        pass

    def updated(self, item):
        pass

    def finished(self, item):
        pass

    def command(self, *args, **kwargs):
        result = Command(self, args, kwargs)
        self.items.append(result)
        return result

    def call(self, *args, **kwargs):
        cmd = self.command(*args, **kwargs)
        cmd.execute()
        if cmd.ok:
            return cmd
        else:
            raise CommandError(cmd.output)

    def request(self, url, **kwargs):
        result = Request(self, url, kwargs)
        self.items.append(result)
        return result

    def get(self, url, **kwargs):
        req = self.request(url, **kwargs)
        req.execute()
        response = req.response
        if not response.ok and response.status_code not in req.expected:
            raise RequestError(response.content)
        return response

    def json(self):
        return [i.json() for i in self.items]
