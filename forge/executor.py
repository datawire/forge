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
from contextlib import contextmanager
from .sentinel import Sentinel

traceback = eventlet.import_patched('traceback')
output = eventlet.import_patched('forge.output')

"""A sentinal value used to indicate that the task is not yet complete."""
PENDING = Sentinel("PENDING")

"""A sentinal value used to indicate that the task terminated with an error of some kind."""
ERROR = Sentinel("ERROR")

class ChildError(Exception):

    """
    Used to indicate that a background task has had an error. The
    details are reported at the source of the error, so this error
    message is intentionally sparse.
    """

    def __init__(self, parent, *children):
        self.parent = parent
        self.children = children
        Exception.__init__(self, "%s child task(s) errored" % len(self.children))

class Result(object):

    def __init__(self, executor, parent):
        self.executor = executor
        self.parent = parent
        self.children = []
        if self.parent:
            self.parent.children.append(self)
        self.child_errors = 0

        self.value = PENDING
        self.exc_info = None
        self.thread = None
        self.stack = None

    @property
    def exception(self):
        return self.exc_info

    @exception.setter
    def exception(self, exc_info):
        self.exc_info = exc_info
        if self.parent:
            self.parent.child_errors += 1

    # XXX: deprecated
    @property
    def result(self):
        return self.value

    def _capture_stack(self):
        self.stack = traceback.extract_stack()

    def wait(self):
        if self.value is PENDING:
            if self.thread not in (None, eventlet.getcurrent()):
                self.thread.wait()
        for ch in self.children:
            ch.wait()
        if self.child_errors > 0 and self.value is not ERROR:
            self.value = ERROR
            self.exception = (ChildError, ChildError(self, self.leaf_errors), None)

    def get(self):
        self.wait()
        if self.value is ERROR:
            raise self.exception[0], self.exception[1], self.exception[2]
        else:
            return self.value

    @property
    def traversal(self):
        yield self
        for c in self.children:
            for d in c.traversal:
                yield d

    @property
    def errors(self):
        return [r for r in self.traversal if r.is_leaf_error()]

    @property
    def leaf_errors(self):
        return [ch for ch in self.traversal if ch is not self and ch.is_leaf_error()]

    def is_leaf_error(self):
        if self.result is ERROR:
            if issubclass(self.exception[0], ChildError):
                return False
            for ch in self.children:
                if ch.value is ERROR and ch.exception[1] == self.exception[1]:
                    return False
            return True
        else:
            return False

    def is_signal(self, (filename, lineno, funcname, text)):
        noise = {"forge/executor.py": ("run", "do_run", "_capture_stack"),
                 "forge/tasks.py": ("go", "__call__"),
                 "eventlet/greenthread.py": ("main",)}
        for k, v in noise.items():
            if filename.endswith(k) and funcname in v:
                return False
        return True

    def get_traceback(self):
        if not self.is_leaf_error():
            return None

        stack = []
        result = self
        while result:
            if not stack:
                stack = traceback.extract_tb(result.exception[2])
                stack[:0] = result.stack
            elif result.parent and result.executor.async:
                stack[:0] = result.stack
            result = result.parent

        # Noise is considered to be dispatch/glue code that clutters
        # stack traces due to bugs in the actual business logic of
        # tasks. We only filter out noise if the last line of the
        # stack is business logic. That way if there is a bug in the
        # dispatch/glue code it doesn't get filtered out.
        if self.is_signal(stack[-1]):
            stack = filter(self.is_signal, stack)
        return "".join(["Traceback (most recent call last):\n"] + traceback.format_list(stack) +
                       traceback.format_exception_only(*self.exception[:2]))

    @property
    def terminal(self):
        return executor.MUXER.terminal

    def report(self, autocolor=True):
        total = 0
        errors = []
        for r in self.traversal:
            total += 1
            if r.is_leaf_error():
                exc = r.exception[1]
                indent = "  "
                if getattr(exc, "report_traceback", True):
                    tb = "\n\n" + r.get_traceback().strip()
                    errors.append("%s%s: unexpected error%s" % (indent, r.executor.name,
                                                                tb.replace("\n", "\n  " + indent)))
                else:
                    errors.append("%s%s: %s" % (indent, r.executor.context, exc))

        if autocolor:
            if errors:
                color = self.terminal.bold_red
            else:
                color = self.terminal.green
        else:
            color = lambda x: x

        result = "\n".join(["%s tasks run, %s errors" % (total, len(errors))] + errors)

        return "\n".join([color(line) for line in result.splitlines()])

    def __repr__(self):
        if self.exception is None:
            return "Value(%r)" % self.value
        else:
            return repr(self.exception[1])

class _Muxer(object):

    def __init__(self, stream):
        assert not isinstance(stream, _Muxer)
        self.previous = None
        self.stream = stream
        self.terminal = output.Terminal()
        self.default_color = lambda x: x

    def write(self, bytes):
        exe = executor.current()
        if exe is None:
            context = None
            color = self.default_color
        else:
            context = exe.context
            color = exe.color
        if self.previous != context:
            if context is not None:
                self.stream.write(color(u"\u2554\u2550") + color(context) + "\n")
        self.stream.write(bytes)
        self.previous = context

    def flush(self):
        self.stream.flush()

    def isatty(self):
        return self.stream.isatty()

class executor(object):

    """An executor provides some useful utilities for safely running and
    coordinating code:

        # an executor can run stuff safely:
        exe = executor("my-executor")
        result = exe.run(lambda x: x/0, 1)

        # a result can be an error or a value
        if result.value is ERROR:
            print result.exception
        else:
            print result.value

        # you can retrieve the result just as if you had run the
        # function
        try:
            x = result.get()
            print x
        except ZeroDivisionError, e:
            print e

    An executor can also be used to run asynchronous tasks:

        exe = executor("my-async-executor", async=True)
        result = exe.run(lambda x: x/0, 1)
        # the result is pending
        if result.value is PENDING:
           print "still waiting..."

        # block until the result is available
        result.wait()

        if result.value is ERROR:
            print result.exception
        else:
            print result.value

    When executors are nested, any errors occuring in asynchronous
    tasks are tracked:

        def my_code():
            exe = executor("sub-executor", async=True)
            # lets launch a background task and ignore the result
            exe.run(lambda: 1/0)

        exe = executor("root-executor")
        result = exe.run(my_code)

    The executor tracks all background tasks and should any errors
    occur, the executor constructs a full stack trace that includes
    not only the line of code in the background thread, but the stack
    for the code that launched the background thread:

        print result.report() -->

            root-executor: 1 child task(s) errored
              sub-executor: unexpected error
                
                Traceback (most recent call last):
                  File "<stdin>", line 1, in <module>
                  File "<stdin>", line 4, in my_code
                  File "<stdin>", line 4, in <lambda>
                ZeroDivisionError: integer division or modulo by zero
    """

    CURRENT = local()
    MUXER = _Muxer(sys.stdout)
    COLORS = [getattr(MUXER.terminal, n) for n in ("white",
                                                   "cyan",
                                                   "magenta",
                                                   "blue",
                                                   "bold_cyan",
                                                   "bold_magenta",
                                                   "bold_blue",
                                                   "bold_white",
                                                   "black_on_white",
                                                   "bold_white_on_blue",
                                                   "white_on_blue",
                                                   "white_on_magenta",
                                                   "bold_white_on_magenta")]
    ALLOCATED = {}

    @classmethod
    def allocate_color(cls, name):
        if name in cls.ALLOCATED:
            return cls.ALLOCATED[name]
        else:
            color = cls.COLORS[len(cls.ALLOCATED) % len(cls.COLORS)]
            cls.ALLOCATED[name] = color
            return color

    @classmethod
    def current(cls):
        return getattr(cls.CURRENT, "executor", None)

    @classmethod
    def current_result(cls):
        return getattr(cls.CURRENT, "result", None)

    @classmethod
    def setup(cls):
        eventlet.sleep() # workaround for import cycle: https://github.com/eventlet/eventlet/issues/401
        eventlet.monkey_patch()

        if 'pytest' not in sys.modules:
            import getpass
            getpass.os = eventlet.patcher.original('os') # workaround for https://github.com/eventlet/eventlet/issues/340

        sys.stdout = cls.MUXER

    def __init__(self, name = None, async=False):
        self.name = name
        self.results = []
        self.async = async
        self.messages = []

        self.parent = self.current()

        if self.parent is None:
            self.verbose = False
        else:
            self.verbose = self.parent.verbose

        if self.name is None:
            if self.parent:
                self.context = self.parent.context
            else:
                self.context = None
        else:
            self.context = self.name

        if not self.parent:
            self.context_colors = {}
        self.color = self.allocate_color(self.context)

    @contextmanager
    def _make_current(self, result):
        saved_executor = self.current()
        saved_result = self.current_result()
        self.CURRENT.executor = self
        self.CURRENT.result = result
        yield
        self.CURRENT.executor = saved_executor
        self.CURRENT.result = saved_result

    def echo(self, text="", prefix=u"\u2551 ", newline=True):
        with self._make_current(None):
            msg = self.color(prefix) + text.replace("\n", "\n" + self.color(prefix))
            msg = msg.encode("UTF-8")
            if newline:
                print msg
            else:
                sys.stdout.write(msg)

    def info(self, text):
        if self.verbose:
            self.echo(text)

    def warn(self, text):
        if self.verbose:
            self.echo(text)
        else:
            self.messages.append(text)

    def error(self, text):
        if self.verbose:
            self.echo(text)
        else:
            self.messages.append(text)

    def do_run(self, result, fun, args, kwargs):
        with self._make_current(result):
            try:
                result.value = fun(*args, **kwargs)
            except:
                result.value = ERROR
                result.exception = sys.exc_info()
            result.thread = None
            result.wait()

    def run(self, fun, *args, **kwargs):
        result = Result(self, self.current_result())
        result._capture_stack()
        self.results.append(result)
        if self.async:
            result.thread = eventlet.spawn(self.do_run, result, fun, args, kwargs)
        else:
            self.do_run(result, fun, args, kwargs)
        return result

    def wait(self):
        for r in self.results:
            r.wait()

    def report(self):
        return "\n".join([r.report() for r in self.results])
