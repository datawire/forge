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
output = eventlet.import_patched('forge.output')

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

    """
    Used to signal anticipated errors has occured. A task error will
    be rendered without it's stack trace, so it should include enough
    information in the error message to diagnose the issue.
    """

    pass

class ChildError(TaskError):

    """
    Used to indicate that a background task has had an error. The
    details are reported at the source of the error, so this error
    message is intentionally sparse.
    """

    def __init__(self, parent, *children):
        self.parent = parent
        self.children = children
        TaskError.__init__(self, "%s child task(s) errored" % len(self.children))

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
        return execution.call(self.task, self._munge(args), kwargs,
                              ignore_first=self.object is not _UNBOUND,
                              stack = _capture_stack())

    def go(self, *args, **kwargs):
        return execution.spawn(self.task, self._munge(args), kwargs,
                               ignore_first=self.object is not _UNBOUND,
                               stack = _capture_stack())

    def run(self, *args, **kwargs):
        task_include = kwargs.pop("task_include", lambda x: True)
        exe = self.go(*args, **kwargs)

        renderer = Renderer(exe, task_include)

        if not renderer.terminal.does_styling:
            exe.wait()
            print "".join(exe.render(task_include))
        else:
            exe.handler = renderer
            exe.wait()
            renderer.done()

        return exe

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

class BaseHandler(object):

    def default(self, exe, event):
        pass

class Renderer(BaseHandler, output.Drawer):

    def __init__(self, exe, include):
        output.Drawer.__init__(self)
        self.exe = exe
        self.include = include

    def lines(self, trim=True):
        if trim:
            return self.exe.render(self.include, tail=self.terminal.height, wrap=self.terminal.wrap)
        else:
            return self.exe.render(self.include, wrap=self.terminal.wrap)

    def render(self):
        self.draw(self.lines())

    def on_status(self, ctx, evt):
        self.render()

    def on_started(self, ctx, evt):
        self.render()

    def on_finished(self, ctx, evt):
        self.render()

    def done(self):
        self.draw(self.lines(trim=False), trim=False)

def _capture_stack():
    return traceback.extract_stack()

def _truncate(s, limit):
    if len(s) > limit:
        return "%s..." % s[:limit-3]
    else:
        return s

def _format_arg(s):
    if "\n" in s:
        return repr(s)
    else:
        return s

class execution(object):

    CURRENT = local()

    DEFAULT_HANDLER = BaseHandler()

    @classmethod
    def current(cls):
        return getattr(cls.CURRENT, "execution", None)

    @classmethod
    def set(cls, value):
        cls.CURRENT.execution = value

    def __init__(self, task, args, kwargs, ignore_first = False):
        self.task = task
        self.parent = self.current()
        self.args = args
        self.kwargs = kwargs
        self.ignore_first = ignore_first
        self.children = []
        self.child_errors = 0
        if self.parent is not None:
            self.parent.children.append(self)
            self.thread = self.parent.thread
            self.handler = self.parent.handler
        else:
            self.thread = None
            self.handler = self.DEFAULT_HANDLER


        # start time
        self.started = None
        # capture the log records emitted during execution
        self.records = []
        # capture the current status
        self.status = None
        # a summary of the result of the task
        self.summary = None
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
        self.args_formatted = self._format_args()
        self.args_summary = [_truncate(a, 60) for a in self.args_formatted]

    def _format_args(self):
        summarized = self.args[1:] if self.ignore_first else self.args

        args = [_format_arg(str(elide(a))) for a in summarized]
        args.extend("%s=%s" % (k, _format_arg(str(v))) for k, v in self.kwargs.items())

        return args

    @property
    def traversal(self):
        yield self
        for c in self.children:
            for d in c.traversal:
                yield d

    def fire(self, event):
        meth = getattr(self.handler, "on_%s" % event, self.handler.default)
        meth(self, event)

    def update_status(self, message):
        self.status = message
        self.fire("status")
        self.info(message)

    def summarize(self, message):
        self.summary = message
        self.info(message)

    def log_record(self, record):
        self.records.append(record)
        self.fire("log")

    def log(self, *args, **kwargs):
        self.task.logger.log(*args, **kwargs)

    def info(self, *args, **kwargs):
        self.task.logger.info(*args, **kwargs)

    @classmethod
    def call(cls, task, args, kwargs, ignore_first=False, stack = None):
        exe = execution(task, args, kwargs, ignore_first = ignore_first)
        exe._stack = stack
        exe.run()
        return exe.get()

    @classmethod
    def spawn(cls, task, args, kwargs, ignore_first=False, stack = None):
        exe = execution(task, args, kwargs, ignore_first = ignore_first)
        exe._stack = stack
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

    def enter(self):
        self.info("START(%s)" % ", ".join(self.args_formatted))

    def exit(self):
        self.info("RESULT -> %s (%s)" % (self.result, elapsed(self.finished - self.started)))

    def record_exc(self, type, value, traceback):
        self.exception = (type, value, traceback)
        if self.parent:
            self.parent.child_errors += 1

    @property
    def leaf_errors(self):
        return [ch for ch in self.traversal if ch is not self and ch.is_leaf_error()]

    def check_children(self, result):
        if result is ERROR:
            self.result = result
        elif self.child_errors > 0:
            # XXX: this swallows the result, might be nicer to keep it
            # somehow (maybe with partial result concept?)
            self.result = ERROR
            self.record_exc(ChildError, ChildError(self, *self.leaf_errors), None)
        else:
            self.result = result

    def run(self):
        self.set(self)
        self.started = time.time()
        self.enter()
        self.fire("started")
        try:
            result = self.task.function(*self.args, **self.kwargs)
        except:
            self.record_exc(*sys.exc_info())
            result = ERROR
        finally:
            self.sync()
            self.check_children(result)
            self.finished = time.time()
            self.exit()
            self.set(self.parent)
            self.fire("finished")

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
        if not self.is_leaf_error():
            return "%s child task(s) errored" % len(self.leaf_errors)

        if issubclass(self.exception[0], TaskError):
            return str(self.exception[1])
        else:
            return "unexpected error"

    def report(self):
        indent = "\n  "

        if self.result is PENDING or self.summary is None:
            summary = self.status or "(in progress)" if self.result is PENDING else \
                      self.error_summary if self.result is ERROR else \
                      str(self.result) if self.result is not None else \
                      ""

            args = () if self.status else self.args_summary
            if not summary:
                summary = " ".join(args)
            elif "\n" in summary:
                summary = " ".join(args) + indent + summary
            elif args:
                if summary:
                    summary = " ".join(args) + " -> " + summary
                else:
                    summary = " ".join(args)

        else:
            summary = self.summary

        summary = summary.replace("\n", indent).strip()

        result = "%s: %s" % (self.task.name, summary)

        if self.result == ERROR:
            if not issubclass(self.exception[0], TaskError):
                exc = self.get_traceback()
                if exc:
                    result += "\n" + indent + exc.replace("\n", indent)

        return result

    def is_leaf_error(self):
        if self.result is ERROR:
            if issubclass(self.exception[0], ChildError):
                return False
            for ch in self.children:
                if ch.result is ERROR and ch.exception[1] == self.exception[1]:
                    return False
            return True
        else:
            return False

    def is_signal(self, (filename, lineno, funcname, text)):
        noise = {"forge/tasks.py": ("go", "__call__", "_capture_stack", "run", "call"),
                 "eventlet/greenthread.py": ("main",)}
        for k, v in noise.items():
            if filename.endswith(k) and funcname in v:
                return False
        return True

    def get_traceback(self):
        if not self.is_leaf_error():
            return None

        stack = []
        for exe in reversed(self.stack):
            if not stack:
                stack = traceback.extract_tb(exe.exception[2])
                stack[:0] = exe._stack
            elif exe.parent and exe.parent.thread != exe.thread:
                stack[:0] = exe._stack

        # Noise is considered to be dispatch/glue code that clutters
        # stack traces due to bugs in the actual business logic of
        # tasks. We only filter out noise if the last line of the
        # stack is business logic. That way if there is a bug in the
        # dispatch/glue code it doesn't get filtered out.
        if self.is_signal(stack[-1]):
            stack = filter(self.is_signal, stack)
        return "".join(["Traceback (most recent call last):\n"] + traceback.format_list(stack) +
                       traceback.format_exception_only(*self.exception[:2]))

    def render_node(self, indent):
        return indent + self.report().replace("\n", "\n" + indent)

    def render(self, include=lambda x: True, tail=None, wrap=lambda x: [x]):
        def _include(e):
            return include(e) or e.result is ERROR
        exes = [e for e in self.traversal if _include(e)]
        lines = []
        for e in reversed(exes):
            lines[:0] = wrap(e.render_node(e.indent(_include)))
            if tail and len(lines) > tail:
                break
        return lines[:tail or len(lines)]

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

def summarize(*args, **kwargs):
    """
    Provide a summary of the result of the current task. This will log an info message.
    """
    return execution.current().summarize(*args, **kwargs)

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

class Result(object):

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
    expected = kwargs.pop("expected", (0,))
    cmd = tuple(str(a) for a in args)

    argsum = " ".join(execution.current().args_summary)

    try:
        p = Popen(cmd, stderr=STDOUT, stdout=PIPE, **kwargs)
        output = ""
        for line in p.stdout:
            output += line
            status("%s -> (in progress)\n%s" % (argsum, output))
        p.wait()
        result = Result(cmd, p.returncode, output)
    except OSError, e:
        ctx = ' %s' % kwargs if kwargs else ''
        raise TaskError("error executing command '%s'%s: %s" % (" ".join(cmd), ctx, e))
    if p.returncode in expected:
        if output.strip():
            summarize("%s -> %s" % (argsum, output))
        else:
            summarize(argsum)
        return result
    else:
        raise TaskError("command failed[%s]: %s" % (result.code, result.output))

requests = eventlet.import_patched('requests.__init__') # the .__init__ is a workaround for: https://github.com/eventlet/eventlet/issues/208

@task("GET")
def get(url, **kwargs):
    try:
        response = requests.get(str(url), **kwargs)
        summarize("%s -> [%s]" % (" ".join(execution.current().args_summary), response.status_code))
        return response
    except requests.RequestException, e:
        raise TaskError(e)
