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
from eventlet.corolocal import local
from eventlet.green import time

logging = eventlet.import_patched('logging')
traceback = eventlet.import_patched('traceback')
blessed = eventlet.import_patched('blessed')

# XXX: need better default for logfile
def setup(logfile='/tmp/forge.log'):
    """
    Setup the task system. This will perform eventlet monkey patching as well as set up logging.
    """

    eventlet.sleep() # workaround for import cycle: https://github.com/eventlet/eventlet/issues/401
    eventlet.monkey_patch()

    if 'pytest' not in sys.modules:
        import getpass
        getpass.os = eventlet.patcher.original('os') # workaround for https://github.com/eventlet/eventlet/issues/340

    logging.getLogger("tasks").addFilter(TaskFilter())
    logging.basicConfig(filename=logfile,
                        level=logging.INFO,
                        format='%(levelname)s %(task_id)s: %(message)s')

class TaskError(Exception):
    pass

class Sentinel(object):

    """A convenience class that can be used for creating constant values that str/repr using their constant name."""

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

"""A sentinal value used to indicate that the task is not yet complete."""
PENDING = Sentinel("PENDING")

"""A sentinal value used to indicate that the task terminated with an error of some kind."""
ERROR = Sentinel("ERROR")

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
            exe.log_record(record)
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

     - Convenience APIs for status updates and progress indicators
       allow tasks to trivially provide good user feedback.

     - Convenience APIs for executing tasks in parallel.

     - Convenience for safely executing shell and http requests with
       good error reporting and user feedback.

    Any python function can be marked as a task and invoked in the
    normal way you would invoke any function, e.g.:

        @task("Normalize Path")
        def normpath(path):
            status("splitting path: %s" % path)
            parts = [p for p in path.split("/") if p]
            status("filtered path: %s" % ", ".join(parts))
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

    def __init__(self, name = None):
        self.name = name
        self.logger = logging.getLogger("tasks")
        self.count = 0

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
        return execution.call(self.task, self._munge(args), kwargs)

    def go(self, *args, **kwargs):
        return execution.spawn(self.task, self._munge(args), kwargs)

    def run(self, *args, **kwargs):
        task_include = kwargs.pop("task_include", lambda x: True)
        terminal = blessed.Terminal()
        previous = []

        exe = self.go(*args, **kwargs)

        for _ in exe.events:
            lines = exe.render(task_include).splitlines()
            screenful = lines[-terminal.height:]

            common_head = 0
            for old, new in zip(previous, screenful):
                if old == new:
                    common_head += 1
                else:
                    break

            sys.stdout.write(terminal.move_up*(len(previous)-common_head))

            for line in screenful[common_head:]:
                # XXX: should really wrap this properly somehow, but
                #      writing out more than the terminal width will mess up
                #      the movement logic
                delta = len(line) - terminal.length(line)
                sys.stdout.write(line[:terminal.width+delta])
                sys.stdout.write(terminal.clear_eol + terminal.move_down)

            sys.stdout.write(terminal.clear_eos)
            previous = screenful

        return exe

class execution(object):

    CURRENT = local()

    @classmethod
    def current(cls):
        return getattr(cls.CURRENT, "execution", None)

    @classmethod
    def set(cls, value):
        cls.CURRENT.execution = value

    def __init__(self, task, args, kwargs):
        self.task = task
        self.parent = self.current()
        self.args = args
        self.kwargs = kwargs
        self.children = []
        self.child_errors = 0
        if self.parent is not None:
            self.parent.children.append(self)
            self.thread = self.parent.thread
        else:
            self.thread = None

        self._dirty_events = set()

        # start time
        self.started = None
        # capture the log records emitted during execution
        self.records = []
        # capture the current status
        self.status = None
        # end time
        self.finished = None

        # the return result
        self.result = PENDING
        # any exception that was produced
        self.exception = None

        # outstanding child tasks
        self.outstanding = []

        if self.parent is None:
            self.index = self.task.generate_id()
        else:
            self.index = len([c for c in self.parent.children if c.task == task])

        self.id = ".".join("%s[%s]" % (e.task.name, e.index) for e in self.stack)

    @property
    def traversal(self):
        yield self
        for c in self.children:
            for d in c.traversal:
                yield d

    def fire(self, event):
        self._dirty_events.add(event)
        eventlet.sleep()

    def _pop_events(self):
        result = []
        for e in self.traversal:
            if e._dirty_events:
                popped = list(e._dirty_events)
                popped.sort()
                e._dirty_events.clear()
                for evt in popped:
                    result.append((e, evt))
        return result

    @property
    def events(self):
        while True:
            events = self._pop_events()
            if not events and not self.running:
                return
            yield events
            eventlet.sleep()

    def update_status(self, message):
        self.status = message
        self.fire("status")
        self.info(message)

    def log_record(self, record):
        self.records.append(record)
        self.fire("record")

    def log(self, *args, **kwargs):
        self.task.logger.log(*args, **kwargs)

    def info(self, *args, **kwargs):
        self.task.logger.info(*args, **kwargs)

    @property
    def running(self):
        return self.result is PENDING or self.outstanding

    @classmethod
    def call(cls, task, args, kwargs):
        exe = execution(task, args, kwargs)
        exe.run()
        return exe.get()

    @classmethod
    def spawn(cls, task, args, kwargs):
        exe = execution(task, args, kwargs)
        exe.thread = eventlet.spawn(exe.run)
        if exe.parent:
            exe.parent.outstanding.append(exe)
        return exe

    @property
    def stack(self):
        result = []
        exe = self
        while exe:
            result.append(exe)
            exe = exe.parent
        result.reverse()
        return result

    @property
    def arg_summary(self):
        args = [str(a) for a in self.args]
        args.extend("%s=%s" % (k, v) for k, v in self.kwargs.items())
        return args

    def enter(self):
        self.info("START(%s)" % ", ".join(self.arg_summary))

    def exit(self):
        self.info("RESULT -> %s (%s)" % (self.result, elapsed(self.finished - self.started)))

    def check_children(self):
        if self.result is ERROR:
            return
        if self.child_errors > 0:
            # XXX: this swallows the result, might be nicer to keep it
            # somehow (maybe with partial result concept?)
            errored = [ch.id for ch in self.traversal if ch.result is ERROR]
            self.result = ERROR
            self.exception = (TaskError,
                              TaskError("%s child task(s) errored: %s" % (self.child_errors, ", ".join(errored))),
                              None)

    def run(self):
        self.set(self)
        self.started = time.time()
        self.enter()
        try:
            self.result = self.task.function(*self.args, **self.kwargs)
        except:
            self.result
            self.exception = sys.exc_info()
            self.result = ERROR
            if self.parent:
                self.parent.child_errors += 1
        finally:
            self.sync()
            self.finished = time.time()
            self.check_children()
            self.exit()
            self.set(self.parent)

    def sync(self):
        result = []
        while self.outstanding:
            ch = self.outstanding.pop(0)
            ch.thread.wait()
            result.append(ch)
        return result

    def wait(self):
        if self.thread != None and self.result is PENDING:
            self.thread.wait()

    def get(self):
        self.wait()
        if self.result is ERROR:
            raise self.exception[0], self.exception[1], self.exception[2]
        else:
            return self.result

    def indent(self, include=lambda x: True):
        return "  "*(len([e for e in self.stack if include(e)]) - 1)

    @property
    def error_summary(self):
        return "".join(traceback.format_exception_only(*self.exception[:2])).strip()

    def render_line(self, include=lambda x: True):
        indent = "\n  " + self.indent(include)

        summary = self.status or "(in progress)" if self.result is PENDING else \
                  self.error_summary if self.result is ERROR else \
                  str(self.result) if self.result is not None else \
                  ""

        summary = summary.replace("\n", indent).strip()
        args = self.arg_summary
        if not summary:
            summary = " ".join(args)
        elif "\n" in summary:
            summary = " ".join(args) + indent + summary
        elif args:
            summary = " ".join(args) + " -> " + summary

        result = "%s%s: %s" % (self.indent(include), self.task.name, summary)

        if self.result == ERROR and (self.parent is None or self.thread != self.parent.thread):
            exc = "".join(traceback.format_exception(*self.exception))
            result += "\n" + indent + exc.replace("\n", indent)

        return result

    def render(self, include=lambda x: True):
        return "\n".join([e.render_line(include) for e in self.traversal if include(e)])

def sync():
    """
    Wait until all child tasks have terminated.
    """
    return execution.current().sync()

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

def status(*args, **kwargs):
    """
    Update the status for the current task. This will log an info message with the new status.
    """
    return execution.current().update_status(*args, **kwargs)

def gather(sequence):
    """
    Resolve a sequence of asynchronously executed tasks.
    """
    for obj in sequence:
        if isinstance(obj, execution):
            yield obj.get()
        else:
            yield obj

OMIT = Sentinel("OMIT")

def project(task, sequence):
    execs = []
    for obj in sequence:
        execs.append(task.go(obj))
    for e in execs:
        obj = e.get()
        if obj is not OMIT:
            yield obj

def cull(task, sequence):
    execs = []
    for obj in sequence:
        execs.append((task.go(obj), obj))
    for e, obj in execs:
        if e.get():
            yield obj

## common tasks

from eventlet.green.subprocess import Popen, STDOUT, PIPE

class Result(object):

    def __init__(self, code, output):
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
    expected = kwargs.pop("expected", (0,))
    cmd = tuple(str(a) for a in args)

    try:
        p = Popen(cmd, stderr=STDOUT, stdout=PIPE, **kwargs)
        output = p.stdout.read()
        p.wait()
        result = Result(p.returncode, output)
    except OSError, e:
        ctx = ' %s' % kwargs if kwargs else ''
        raise TaskError("error executing command '%s'%s: %s" % (" ".join(cmd), ctx, e))
    if p.returncode in expected:
        return result
    else:
        raise TaskError("command failed[%s]: %s" % (result.code, result.output))

requests = eventlet.import_patched('requests.__init__') # the .__init__ is a workaround for: https://github.com/eventlet/eventlet/issues/208

@task("GET")
def get(url, **kwargs):
    status(url)
    return requests.get(str(url), **kwargs)
