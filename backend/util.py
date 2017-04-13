from eventlet.green import subprocess
import time

class Result(object):

    def __init__(self, command, context, code, output):
        self.command = command
        self.context = context
        self.code = code
        self.output = output
        self.start = None
        self.end = None

    def json(self):
        return {"command": self.command,
                "context": self.context,
                "code": self.code,
                "output": self.output,
                "start": self.start,
                "end": self.end}

def call(*args, **kwargs):
    try:
        start = time.time()
        result = Result(args, kwargs, 0, subprocess.check_output(args, stderr=subprocess.STDOUT, **kwargs))
    except subprocess.CalledProcessError, e:
        result = Result(args, kwargs, e.returncode, e.output)
    result.start = start
    result.end = time.time()
    return result

class Worker(object):

    def __init__(self):
        self.log = []

    def call(self, *args, **kwargs):
        result = call(*args, **kwargs)
        self.log.append(result)
        return result
