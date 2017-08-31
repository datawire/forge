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

import os
from forge.tasks import TaskError
from forge.jinja2 import render, renders
from .common import mktree

TEMPLATE_TREE = """
@@template_dir/file1
{{hello}} {{world}}!
@@

@@template_dir/file2
{{hello}} {{world}}!
@@

@@template_dir/sub/file3
{{hello}} {{world}}!
@@

@@template_file.in
{{hello}} {{world}}!
@@

@@template_err.in
{{foo.bar}}
@@
"""

def test_render_dir():
    root = mktree(TEMPLATE_TREE)
    source = os.path.join(root, "template_dir")
    target = os.path.join(root, "template_out")
    render(source, target, hello="Hello", world="World")
    for path in ("file1", "file2", "sub/file3"):
        assert open(os.path.join(target, path)).read() == "Hello World!"

def test_render_file():
    root = mktree(TEMPLATE_TREE)
    source = os.path.join(root, "template_file.in")
    target = os.path.join(root, "template_file")
    render(source, target, hello="Hello", world="World")
    assert open(target).read() == "Hello World!"

def test_render_error():
    root = mktree(TEMPLATE_TREE)
    source = os.path.join(root, "template_err.in")
    try:
        render(source, os.path.join(root, "template_err"), hello="Hello", world="World")
        assert False, "should error"
    except TaskError, e:
        assert "template_err.in: 'foo' is undefined" in str(e)

def test_renders():
    assert renders("foo", "{{hello}} {{world}}!", hello="Hello", world="World") == "Hello World!"

def test_renders_err():
    try:
        renders("foo", "{{foo.bar}}")
        assert False, "should error"
    except TaskError, e:
        assert "foo: 'foo' is undefined" in str(e)
