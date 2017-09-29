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

import os, time
from forge.tasks import TaskError
from forge.docker import Docker
from .common import mktree

registry = "registry.hub.docker.com"
namespace = "forgeorg"
user = "forgetest"
password = "forgetest"

def test_remote_exists_true():
    dr = Docker(registry, namespace, user, password)
    assert not dr.remote_exists("nosuchrepo", "nosuchversion")

def test_remote_exists_false():
    dr = Docker("registry.hub.docker.com", "datawire", user, password)
    assert dr.remote_exists("forge-setup-test", "1")

def test_remote_exists_auth_failed():
    dr = Docker(registry, "forgetest", "nosuchuser", "badpassword")
    try:
        dr.remote_exists("nonexistent", "nosuchversion")
    except TaskError, e:
        assert "problem authenticating" in str(e)

def test_validate():
    dr = Docker(registry, namespace, user, password)
    dr.validate()

START_TIME = time.time()

DOCKER_SOURCE_TREE = """
@@Dockerfile
FROM alpine:3.5
COPY timestamp.txt .
ENTRYPOINT ["echo"]
CMD ["timstamp.txt"]
@@

@@timestamp.txt
START_TIME
@@
"""

def test_build_push():
    dr = Docker(registry, namespace, user, password)
    directory = mktree(DOCKER_SOURCE_TREE, START_TIME=time.ctime(START_TIME))
    name = "dockertest"
    version = "t%s" % START_TIME
    dr.build(directory, os.path.join(directory, "Dockerfile"), name, version)
    dr.push(name, version)
    assert dr.remote_exists(name, version)

DOCKER_SOURCE_TREE_BAD = """
@@Dockerfile
XXXFROM alpine:3.5
COPY timestamp.txt .
ENTRYPOINT ["echo"]
CMD ["timstamp.txt"]
@@

@@timestamp.txt
START_TIME
@@
"""

def test_build_error():
    dr = Docker(registry, namespace, user, password)
    directory = mktree(DOCKER_SOURCE_TREE_BAD, START_TIME=time.ctime(START_TIME))
    name = "dockertestbad"
    version = "t%s" % START_TIME
    try:
        dr.build(directory, os.path.join(directory, "Dockerfile"), name, version)
    except TaskError, e:
        msg = str(e)
        assert "command 'docker build" in msg
        assert "nknown instruction: XXXFROM" in msg
