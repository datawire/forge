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

import eventlet, sys
from contextlib import contextmanager
from eventlet.corolocal import local
from eventlet.green import time
from .sentinel import Sentinel

logging = eventlet.import_patched('logging')
traceback = eventlet.import_patched('traceback')
output = eventlet.import_patched('forge.output')
emod = eventlet.import_patched('forge.executor')
executor = emod.executor
Result = emod.Result

# XXX: need better default for logfile
def setup(logfile='/tmp/forge.log'):
    """
    Setup the task system. This will perform eventlet monkey patching as well as set up logging.
    """

    logging.getLogger("tasks").addFilter(TaskFilter())
    logging.basicConfig(filename=logfile,
                        level=logging.INFO,
                        format='%(levelname)s %(task_id)s: %(message)s')
    executor.setup()

class TaskError(Exception):

    report_traceback = False

    """
    Used to signal anticipated errors has occured. A task error will
    be rendered without it's stack trace, so it should include enough
    information in the error message to diagnose the issue.
    """

    pass

ChildError = emod.ChildError

PENDING = emod.PENDING
ERROR = emod.ERROR

def elapsed(delta):
    """
    Return a pretty representation of an elapsed time.
    """
    minutes, seconds = divmod(delta, 60)
    hours, minutes = divmod(minutes, 60)
    return "%d:%02d:%02d" % (hours, minutes, seconds)

class TaskFilter(logging.Filter):

    """
    This logging filter augments log records with useful context when
    log statements are made within a task. It also captures the log
    messages made within a task and records them in the execution
    object for a task invocation.

    """

    def filter(self, record):
        exe = execution.current()
        if exe:
            record.task_id = exe.id
        else:
            record.task_id = "(none)"
        return True

class task(object):

    """A decorator used to mark a given function or method as a task.

    A task can really be any python code, however it is expected that
    tasks will perform scripting, coordination, integration, and
    general glue-like activities that are used to automate tasks on
    behalf of humans.

    This kind of code generally suffers from a number of problems:

     - There is rarely good user feedback for what is happening at any
       given moment.

     - When integration assumptions are violated (e.g. remote system
       barfs) the errors are often swallowed/opaque.

     - Because of the way it is incrementally built via growing
       convenience scripts it is often opaque and difficult to debug.

     - When parallel workflows are needed, they are difficult to code
       in a way that preserves clear user feedback on progress and
       errors.

    Using the task decorator provides a number of conveniences useful
    for this kind of code.

     - Task arguments/results are automatically captured for easy
       debugging.

     - Convenience APIs for executing tasks in parallel.

     - Convenience for safely executing shell and http requests with
       good error reporting and user feedback.

    Any python function can be marked as a task and invoked in the
    normal way you would invoke any function, e.g.:

        @task()
        def normpath(path):
            parts = [p for p in path.split("/") if p]
            normalized = "/".join(parts)
            if path.startswith("/"):
              return "/" + normalized
            else:
              return normalized

        print normpath("/foo//bar/baz") -> "/foo/bar/baz"

    The decorator however provides several other convenient ways you
    can invoke a task:

        # using normpath.go, I can launch subtasks in parallel
        normalized = normpath.go("asdf"), normpath.go("fdsa"), normpath.go("bleh")
        # now I can fetch the result of an individual subtask:
        result = normalized[0].get()
        # or sync on any outstanding sub tasks:
        sync()

    You can also run a task. This will render progress indicators,
    status, and errors to the screen as the task and any subtasks
    proceed:

        normpath.run("/foo//bar/baz")

    """

    def __init__(self, name = None, context = None):
        self.name = name
        self.context_template = context
        self.logger = logging.getLogger("tasks")
        self.count = 0

    @staticmethod
    @contextmanager
    def context(name):
        exe = executor.current()
        saved = getattr(exe, "_default_name", None)
        exe._default_name = name
        yield
        exe._default_name = saved

    def _context(self, args, kwargs):
        exe = executor.current()
        if exe and getattr(exe, "_default_name", None) is not None:
            return exe._default_name
        if self.context_template is None:
            return None
        return self.context_template.format(*args, **kwargs)

    def generate_id(self):
        self.count += 1
        return self.count

    def __call__(self, function):
        self.function = function
        if self.name is None:
            self.name = self.function.__name__
        return decorator(self)

_UNBOUND = Sentinel("_UNBOUND")

class decorator(object):

    def __init__(self, task, object = _UNBOUND):
        self.task = task
        self.object = object

    def __get__(self, object, clazz):
        return decorator(self.task, object)

    def _munge(self, args):
        if self.object is _UNBOUND:
            return args
        else:
            return (self.object,) + args

    def __call__(self, *args, **kwargs):
        exe = executor(self.task._context(args, kwargs))
        result = exe.run(self.task.function, *self._munge(args), **kwargs)
        return result.get()

    def go(self, *args, **kwargs):
        exe = executor(self.task._context(args, kwargs), async=True)
        result = exe.run(self.task.function, *self._munge(args), **kwargs)
        return result

    def run(self, *args, **kwargs):
        result = self.go(*args, **kwargs)
        result.wait()
        result.executor.echo(result.report())
        return result

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

class execution(object):

    def log(self, *args, **kwargs):
        self.task.logger.log(*args, **kwargs)

    def info(self, *args, **kwargs):
        self.task.logger.info(*args, **kwargs)

def sync():
    """
    Wait until all child tasks have terminated.
    """
    return executor.current().wait()

def log(*args, **kwargs):
    """
    Log a message for the current task.
    """
    execution.current().log(*args, **kwargs)

def info(*args, **kwargs):
    """
    Log an info message for the current task.
    """
    execution.current().info(*args, **kwargs)

def debug(*args, **kwargs):
    """
    Log a debug message for the current task.
    """
    execution.current().debug(*args, **kwargs)

def warn(*args, **kwargs):
    """
    Log a warn message for the current task.
    """
    execution.current().warn(*args, **kwargs)

def error(*args, **kwargs):
    """
    Log an error message for the current task.
    """
    execution.current().error(*args, **kwargs)

def gather(sequence):
    """
    Resolve a sequence of asynchronously executed tasks.
    """
    for obj in sequence:
        if isinstance(obj, Result):
            yield obj.get()
        else:
            yield obj

OMIT = Sentinel("OMIT")

def _taskify(obj):
    if isinstance(obj, decorator):
        return obj
    else:
        @task()
        def applicator(*args, **kwargs):
            return obj(*args, **kwargs)
        return applicator

def project(task, sequence):
    task = _taskify(task)
    execs = []
    for obj in sequence:
        execs.append(task.go(obj))
    for e in execs:
        obj = e.get()
        if obj is not OMIT:
            yield obj

def cull(task, sequence):
    task = _taskify(task)
    execs = []
    for obj in sequence:
        execs.append((task.go(obj), obj))
    for e, obj in execs:
        if e.get():
            yield obj

## common tasks

from eventlet.green.subprocess import Popen, STDOUT, PIPE

class SHResult(object):

    def __init__(self, command, code, output):
        self.command = command
        self.code = code
        self.output = output

    def __str__(self):
        if self.code != 0:
            code = "[exit %s]" % self.code
            if self.output:
                return "%s: %s" % (code, self.output)
            else:
                return code
        else:
            return self.output

@task("CMD")
def sh(*args, **kwargs):
    import os
    expected = kwargs.pop("expected", (0,))
    cmd = tuple(str(a) for a in args)

    kwcopy = kwargs.copy()
    parts = []
    cwd = kwcopy.pop("cwd", None)
    if cwd is not None and not os.path.samefile(cwd, os.getcwd()):
        parts.append("[%s]" % cwd)
    env = kwcopy.pop("env", None)
    if env is not None:
        for k, v in env.items():
            if v != os.environ.get(k, None):
                parts.append("%s=%s" % (k, v))

    parts.extend(cmd)
    command = " ".join(parts)

    print command

    try:
        p = Popen(cmd, stderr=STDOUT, stdout=PIPE, **kwargs)
        output = ""
        for line in p.stdout:
            output += line
            print line[:-1]
        p.wait()
        result = SHResult(command, p.returncode, output)
    except OSError, e:
        raise TaskError("error executing command '%s': %s" % (command, e))
    if p.returncode in expected:
        return result
    else:
        raise TaskError("command '%s' failed[%s]: %s" % (command, result.code, result.output))

requests = eventlet.import_patched('requests.__init__') # the .__init__ is a workaround for: https://github.com/eventlet/eventlet/issues/208

@task("GET")
def get(url, **kwargs):
    print "GET %s" % url
    try:
        response = requests.get(str(url), **kwargs)
        return response
    except requests.RequestException, e:
        raise TaskError(e)
