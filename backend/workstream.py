import time
from eventlet.green.subprocess import Popen, STDOUT, PIPE

class Workitem(object):

    def __init__(self, stream):
        self.stream = stream

    def pending(self):
        assert False, "must override"

def elide(t):
    if "PRIVATE" in t:
        return "ELIDED"
    else:
        return t

class Command(Workitem):

    def __init__(self, stream, command, context):
        Workitem.__init__(self, stream)
        self.command = tuple(elide(t) for t in command)
        self.context = context
        self.created = time.time()
        self.started = None
        self.output = None
        self.updated = None
        self.code = None
        self.finished = None

    def pending(self):
        return self.started is None

    def running(self):
        return self.started is not None and self.finished is None

    def start(self):
        self.output = ""
        self.started = time.time()
        self.updated = self.started
        self.stream.poke()

    def update(self, output):
        self.output += output
        self.updated = time.time()
        self.stream.poke()

    def finish(self, code):
        self.code = code
        self.finished = time.time()
        self.stream.poke()

    def execute(self):
        self.start()
        p = Popen(self.command, stderr=STDOUT, stdout=PIPE, **self.context)
        for line in p.stdout:
            self.update(line)
        p.wait()
        self.finish(p.returncode)

    def json(self):
        return {"command": self.command,
                "context": self.context,
                "code": self.code,
                "output": self.output,
                "started": self.started,
                "finished": self.finished}

class Task(Workitem):
    pass

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
        return cmd

    def json(self):
        return [i.json() for i in self.items]
