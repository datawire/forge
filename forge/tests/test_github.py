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

token = "8c91e6c758b16e7b5d7f0676d3475f9fa33693dd"

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
