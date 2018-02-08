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

import eventlet, functools, sys
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
    normal way you would invoke any function, e.g.::

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
    can invoke a task::

        # using normpath.go, I can launch subtasks in parallel
        normalized = normpath.go("asdf"), normpath.go("fdsa"), normpath.go("bleh")
        # now I can fetch the result of an individual subtask:
        result = normalized[0].get()
        # or sync on any outstanding sub tasks:
        task.sync()

    You can also run a task. This will render progress indicators,
    status, and errors to the screen as the task and any subtasks
    proceed::

        normpath.run("/foo//bar/baz")

    """

    def __init__(self, name = None, context = None):
        self.name = name
        self.context_template = context
        self.logger = logging.getLogger("tasks")
        self.count = 0

    @staticmethod
    @contextmanager
    def verbose(value):
        exe = executor.current()
        saved = exe.verbose
        exe.verbose = value
        yield
        exe.verbose = value

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
        result = decorator(self)
        functools.update_wrapper(result, function)
        return result

    @staticmethod
    def sync():
        """
        Wait until all child tasks have terminated.
        """
        r = executor.current_result()
        r.wait()
        if r.value is ERROR:
            r.get()

    @staticmethod
    def terminal():
        return executor.MUXER.terminal

    @staticmethod
    def echo(*args, **kwargs):
        executor.current().echo(*args, **kwargs)

    @staticmethod
    def info(*args, **kwargs):
        executor.current().info(*args, **kwargs)

    @staticmethod
    def warn(*args, **kwargs):
        executor.current().warn(*args, **kwargs)

    @staticmethod
    def error(*args, **kwargs):
        executor.current().error(*args, **kwargs)


_UNBOUND = Sentinel("_UNBOUND")

class decorator(object):

    def __init__(self, task, object = _UNBOUND):
        self.task = task
        self.object = object
        self.__name__ = getattr(self.task.function, "__name__", "<unknown>")

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

import os

@task("CMD")
def sh(*args, **kwargs):
    output_transform = kwargs.pop("output_transform", lambda l: l)
    expected = kwargs.pop("expected", (0,))
    output_buffer = kwargs.pop("output_buffer", 10)
    cmd = tuple(str(a) for a in args)

    kwcopy = kwargs.copy()
    parts = []
    cwd = kwcopy.pop("cwd", None)
    if cwd is not None and not os.path.samefile(cwd, os.getcwd()):
        relcwd = os.path.relpath(cwd)
        abscwd = os.path.abspath(cwd)
        mincwd = relcwd if len(relcwd) < len(abscwd) else abscwd
        parts.append("[%s]" % mincwd)
    env = kwcopy.pop("env", None)
    if env is not None:
        for k, v in env.items():
            if v != os.environ.get(k, None):
                parts.append("%s=%s" % (k, v))

    parts.extend(str(elide(a)) for a in args)
    command = " ".join(parts)

    try:
        p = Popen(cmd, stderr=STDOUT, stdout=PIPE, **kwargs)
        output = ""
        line_buffer = [command]
        start = time.time()
        for line in p.stdout:
            output += line
            line_buffer.append(output_transform(line[:-1]))
            elapsed = time.time() - start
            if (len(line_buffer) > output_buffer) or (elapsed > 1.0):
                while line_buffer:
                    task.info(line_buffer.pop(0))
            start = time.time()
        while line_buffer:
            task.info(line_buffer.pop(0))
        p.wait()
        result = SHResult(command, p.returncode, output)
    except OSError, e:
        raise TaskError("error executing command '%s': %s" % (command, e))
    if p.returncode in expected:
        return result
    else:
        raise TaskError("command '%s' failed[%s]: %s" % (command, result.code, result.output))

requests = eventlet.import_patched('requests.__init__') # the .__init__ is a workaround for: https://github.com/eventlet/eventlet/issues/208

def json_patch(response, parser):
    def patched():
        try:
            return parser()
        except ValueError, e:
            task.echo("== response could not be parsed as JSON ==")
            task.echo(response.content)
            raise
    return patched

@task("GET")
def get(url, **kwargs):
    task.info("GET %s" % url)
    try:
        response = requests.get(str(url), **kwargs)
        response.json = json_patch(response, response.json)
        return response
    except requests.RequestException, e:
        raise TaskError(e)

import watchdog, watchdog.events

class _Wrapper(watchdog.events.FileSystemEventHandler):

    def __init__(self, action):
        for attr in "on_any_event", "on_created", "on_deleted", "on_modified", "on_moved":
            meth = getattr(action, attr, None)
            if meth:
                setattr(self, attr, meth)

    @task()
    def dispatch(self, event):
        watchdog.events.FileSystemEventHandler.dispatch(self, event)

@task()
def watch(paths, action):
    handler = _Wrapper(action)
    obs = watchdog.observers.Observer()
    for path in paths:
        obs.schedule(handler, path, recursive=True)
    obs.start()
