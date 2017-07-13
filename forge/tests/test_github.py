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

import time, os
from forge.tasks import TaskError
from forge.github import Github
from .common import mktree
from tempfile import mkdtemp
from shutil import rmtree

# github will deactivate this token if it detects it in our source, so
# we obfuscate it slightly
numbers = [48, 49, 51, 99, 99, 101, 52, 51, 48, 53, 54, 100, 57, 56, 97, 50,
           55, 97, 54, 53, 55, 55, 49, 48, 49, 55, 48, 54, 55, 102, 100, 48,
           102, 57, 49, 51, 97, 48, 102, 51]
token = "".join(chr(c) for c in numbers)

def test_list():
    gh = Github(token)
    repos = gh.list("forgeorg")
    assert repos == [(u'forgeorg/foo', u'https://github.com/forgeorg/foo.git')]

def test_pull():
    gh = Github(token)
    repos = gh.list("forgeorg")
    name, url = repos[0]
    output = mkdtemp()
    gh.pull(url, os.path.join(output, name))
    assert os.path.exists(os.path.join(output, name, "README.md"))
    rmtree(output)

def test_exists():
    gh = Github(token)
    assert gh.exists("https://github.com/forgeorg/foo.git")
    assert not gh.exists("https://github.com/forgeorg/nosuchrepo.git")
    unauth_gh = Github(None)
    try:
        unauth_gh.exists("https://github.com/forgeorg/nosuchrepo.git")
        assert False
    except TaskError, e:
        assert "Authentication failed" in str(e)

def test_clone():
    gh = Github(token)
    output = mkdtemp()
    gh.clone("https://github.com/forgeorg/foo.git", os.path.join(output, 'foo'))
    assert os.path.exists(os.path.join(output, 'foo', "README.md"))
    rmtree(output)

def test_remote():
    gh = Github(token)
    base = mkdtemp()
    target = os.path.join(base, 'foo')
    gh.clone("https://github.com/forgeorg/foo.git", target)
    assert os.path.exists(os.path.join(target, "README.md"))
    # XXX: this is necessary because of the injected token
    remote = gh.remote(target)
    assert remote.endswith("github.com/forgeorg/foo.git"), remote
    assert gh.remote(base) == None
    rmtree(base)
