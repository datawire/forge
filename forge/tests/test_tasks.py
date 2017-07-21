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

from forge.tasks import (
    cull,
    execution,
    gather,
    get,
    project,
    setup,
    sh,
    status,
    summarize,
    sync,
    task,
    ERROR,
    OMIT,
    PENDING,
    TaskError,
    ChildError
)

setup()

import time

# used to check success cases
@task("Noop")
def noop(x):
    return x

# used to check failure cases
@task("Oops")
def oops(x):
    return x/0

def test_success_sync():
    assert noop(3) == 3

def test_success_async():
    exe = noop.go(3)
    assert exe.result == PENDING
    exe.wait()
    assert exe.result == 3
    assert exe.exception is None
    assert exe.get() == 3

def test_failure_sync():
    try:
        oops(3)
        assert False, "should have failed"
    except ZeroDivisionError, e:
        pass

def test_failure_async():
    exe = oops.go(3)
    assert exe.result == PENDING
    exe.wait()
    assert exe.result == ERROR
    assert exe.exception
    assert exe.exception[0] == ZeroDivisionError
    try:
        exe.get()
        assert False, "should have failed"
    except ZeroDivisionError, e:
        pass

@task()
def background_oops(x):
    oops.go(x)

def test_background_failure():
    try:
        background_oops(1)
        assert False, "should have failed"
    except ChildError, e:
        assert "1 child task(s) errored" == str(e)
        pass

# used to check sync
@task("Scatter")
def scatter(n):
    results = [noop.go(i) for i in range(n)]
    sync()
    return [r.result for r in results]

def test_sync():
    gathered = scatter(10)
    for i, x in enumerate(gathered):
        assert i == x

@task()
def steps():
    status("step 1")
    time.sleep(0.1)
    status("step 2")
    time.sleep(0.1)
    status("step 3")

class Filter(object):

    def __init__(self, visitor, *events):
        self.visitor = visitor
        self.events = set(events)
        self.log = []

    def default(self, ctx, evt):
        if evt in self.events:
            self.visitor(ctx, evt)

def test_status():
    exe = steps.go()
    statuses = []
    exe.handler = Filter(lambda e, evt: statuses.append(e.status), "status")
    exe.wait()
    assert exe.result is not ERROR, exe.render()
    assert statuses == ["step 1", "step 2", "step 3"]

def test_render():
    gathered = scatter.go(10)
    gathered.wait()
    assert """Scatter: 10 -> [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
  Noop: 0 -> 0
  Noop: 1 -> 1
  Noop: 2 -> 2
  Noop: 3 -> 3
  Noop: 4 -> 4
  Noop: 5 -> 5
  Noop: 6 -> 6
  Noop: 7 -> 7
  Noop: 8 -> 8
  Noop: 9 -> 9""" == "\n".join(gathered.render())

@task()
def nested_oops_sync():
    noop(1)
    oops(2)
    noop(3)

@task()
def nested_oops_async():
    noop.go(1)
    oops.go(2)
    noop.go(3)

import re

# replace filename and line number references in stack traces so they
# are less brittle/system dependend and we can assert on them
def massage(text):
    return re.sub(r', line [0-9]+',
                  r', line <NNN>',
                  re.sub(r'File "(?:([^"].*)/([^/"].*))"',
                         r'File "<PATH>/\2"',
                         text))

def test_massage():
    assert massage('File "fdsa.py"') == 'File "fdsa.py"'
    assert massage('File "asdf/fdsa.py"') == 'File "<PATH>/fdsa.py"'
    assert massage('File "/asdf/fdsa.py"') == 'File "<PATH>/fdsa.py"'
    assert massage('File "/blah/asdf/fdsa.py"') == 'File "<PATH>/fdsa.py"'
    assert massage('File "asdf.py", line 123') == 'File "asdf.py", line <NNN>'

def test_nested_exception_sync():
    exe = nested_oops_sync.go()
    exe.wait()
    assert """nested_oops_sync: 1 child task(s) errored
  Noop: 1 -> 1
  Oops: 2 -> unexpected error
  
    Traceback (most recent call last):
      File "<PATH>/test_tasks.py", line <NNN>, in nested_oops_sync
        oops(2)
      File "<PATH>/test_tasks.py", line <NNN>, in oops
        return x/0
    ZeroDivisionError: integer division or modulo by zero
    """ == massage("\n".join(exe.render()))

def test_nested_exception_async():
    exe = nested_oops_async.go()
    exe.wait()
    assert """nested_oops_async: 1 child task(s) errored
  Noop: 1 -> 1
  Oops: 2 -> unexpected error
  
    Traceback (most recent call last):
      File "<PATH>/test_tasks.py", line <NNN>, in nested_oops_async
        oops.go(2)
      File "<PATH>/test_tasks.py", line <NNN>, in oops
        return x/0
    ZeroDivisionError: integer division or modulo by zero
    
  Noop: 3 -> 3""" == massage("\n".join(exe.render()))

def test_sh():
    assert "hello" == sh("echo", "-n", "hello").output

def test_sh_nonexist():
    try:
        sh("nonexistent-command")
    except TaskError, e:
        assert 'error executing command' in str(e)

def test_sh_error():
    try:
        sh("ls", "nonexistentfile")
    except TaskError, e:
        assert 'command failed' in str(e)

def test_sh_expected_error():
    sh("ls", "nonexistentfile", expected=(2,))

def test_get():
    response = get("https://httpbin.org/get")
    assert response.json()["url"] == "https://httpbin.org/get"

class C(object):

    def __init__(self, x, y):
        self.x = x
        self.y = y

    @task("C.task")
    def task(self, a):
        return self.x + self.y + a

def test_task_method_sync():
    c = C(1, 2)
    assert 6 == c.task(3)

def test_task_method_async():
    c = C(1, 2)
    exe = c.task.go(3)
    assert exe.result == PENDING
    assert exe.get() == 6

@task()
def gatherer(n):
    return gather(noop.go(i) for i in range(n))

def test_gather():
    result = gatherer(10)
    assert range(10) == list(result)

@task()
def even_project(n):
    if (n % 2) == 0:
        return n
    else:
        return OMIT

def test_project():
    assert [0, 2, 4, 6, 8] == list(project(even_project, range(10)))

@task()
def is_even(n):
    return (n % 2) == 0

def test_cull():
    assert [0, 2, 4, 6, 8] == list(cull(is_even, range(10)))

@task()
def appender(lst, item):
    lst.append(item)

@task()
def mutable_scatter(n):
    result = []
    for i in range(n):
        appender.go(result, i)
    return result

# test that the event loop doesn't crap out early for some reason this
# only happens when *n* is 1
def test_autosync_async(n=1):
    exe = mutable_scatter.go(n)
    exe.wait()
    assert exe.result == range(n)

def test_autosync_async_10():
    test_autosync_async(10)

@task()
def sleeper(span):
    time.sleep(span)

@task()
def steps_summary(x):
    status("step 1")
    time.sleep(0.1)
    status("step 2")
    sleeper.go(0.1)
    summarize("done")

def test_summary():
    exe = steps_summary.go("arg")
    frames = []
    exe.handler = Filter(lambda e, ops: frames.append("\n".join(exe.render())), "status", "finished")
    exe.wait()
    assert exe.get() is None
    assert ['steps_summary: step 1',
            'steps_summary: step 2',
            'steps_summary: step 2\n  sleeper: 0.1',
            'steps_summary: done\n  sleeper: 0.1'] == frames

@task()
def root(node_async, leaf_async):
    if node_async:
        node.go(leaf_async)
    else:
        node(leaf_async)

@task()
def node(leaf_async):
    if leaf_async:
        leaf.go()
    else:
        leaf()

class LeafError(Exception):
    pass

@task()
def leaf():
    raise LeafError("barf")

def exception_render(node_async, leaf_async, expected):
    exe = root.go(node_async, leaf_async)
    exe.wait()
    assert exe.result is ERROR
    massaged = massage("\n".join(exe.render()))
    assert massaged == expected

def test_exception_render_TT():
    exception_render(True, True, """root: True True -> 1 child task(s) errored
  node: True -> 1 child task(s) errored
    leaf: unexpected error
    
      Traceback (most recent call last):
        File "<PATH>/test_tasks.py", line <NNN>, in root
          node.go(leaf_async)
        File "<PATH>/test_tasks.py", line <NNN>, in node
          leaf.go()
        File "<PATH>/test_tasks.py", line <NNN>, in leaf
          raise LeafError("barf")
      LeafError: barf
      """)

def test_exception_render_TF():
    exception_render(True, False, """root: True False -> 1 child task(s) errored
  node: False -> 1 child task(s) errored
    leaf: unexpected error
    
      Traceback (most recent call last):
        File "<PATH>/test_tasks.py", line <NNN>, in root
          node.go(leaf_async)
        File "<PATH>/test_tasks.py", line <NNN>, in node
          leaf()
        File "<PATH>/test_tasks.py", line <NNN>, in leaf
          raise LeafError("barf")
      LeafError: barf
      """)

def test_exception_render_FT():
    exception_render(False, True, """root: False True -> 1 child task(s) errored
  node: True -> 1 child task(s) errored
    leaf: unexpected error
    
      Traceback (most recent call last):
        File "<PATH>/test_tasks.py", line <NNN>, in root
          node(leaf_async)
        File "<PATH>/test_tasks.py", line <NNN>, in node
          leaf.go()
        File "<PATH>/test_tasks.py", line <NNN>, in leaf
          raise LeafError("barf")
      LeafError: barf
      """)

def test_exception_render_FF():
    exception_render(False, False, """root: False False -> 1 child task(s) errored
  node: False -> 1 child task(s) errored
    leaf: unexpected error
    
      Traceback (most recent call last):
        File "<PATH>/test_tasks.py", line <NNN>, in root
          node(leaf_async)
        File "<PATH>/test_tasks.py", line <NNN>, in node
          leaf()
        File "<PATH>/test_tasks.py", line <NNN>, in leaf
          raise LeafError("barf")
      LeafError: barf
      """)
