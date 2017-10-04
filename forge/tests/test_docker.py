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
from forge.tasks import sh, TaskError
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
    dr.build(directory, os.path.join(directory, "Dockerfile"), name, version, {})
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
        dr.build(directory, os.path.join(directory, "Dockerfile"), name, version, {})
    except TaskError, e:
        msg = str(e)
        assert "command 'docker build" in msg
        assert "nknown instruction: XXXFROM" in msg

BUILDER_SOURCE_TREE = """
@@Dockerfile
FROM alpine:3.5
COPY timestamp.txt .
RUN echo original_content > content.txt
ENTRYPOINT ["cat"]
CMD ["content.txt"]
@@

@@timestamp.txt
START_TIME
@@
"""

def test_builder():
    dr = Docker(registry, namespace, user, password)
    directory = mktree(BUILDER_SOURCE_TREE, START_TIME=str(START_TIME))
    name = "buildertest_%s" % START_TIME
    version = "t%s" % START_TIME
    builder = dr.builder(directory, os.path.join(directory, "Dockerfile"), name, version, {})
    try:
        # create a builder container based on the Dockerfile
        result = builder.run("cat", "timestamp.txt")
        assert result.output == str(START_TIME)

        # create an image from the builder with no incremental mods
        builder.commit(name, version)
        # check the image has the correct timestamp and
        result = dr.run(name, version, "cat", "timestamp.txt")
        assert result.output == str(START_TIME)
        # check that the original CMD and ENTRYPOINT are preserved
        result = sh("docker", "run", "--rm", "-it", dr.image(name, version))
        assert result.output.strip() == "original_content"


        # update the timestamp in the builder image
        builder.run("/bin/sh", "-c", "echo updated > timestamp.txt")
        result = builder.run("cat", "timestamp.txt")
        assert result.output.strip() == "updated"
        # create a new image from the updated builder
        builder.commit(name, version + "_updated")
        result = dr.run(name, version + "_updated", "cat", "timestamp.txt")
        assert result.output.strip() == "updated"
        # check that the original CMD and ENTRYPOINT are preserved in
        # the image created from the updated container
        result = sh("docker", "run", "--rm", "-it", dr.image(name, version + "_updated"))
        assert result.output.strip() == "original_content"

        # now let's update the Dockerfile and make sure we launch a new builder
        with open(os.path.join(directory, "Dockerfile"), "write") as fd:
            fd.write("""FROM alpine:3.5
COPY timestamp.txt .
RUN echo updated_content > content.txt
ENTRYPOINT ["cat"]
CMD ["content.txt"]
""")

        builder = dr.builder(directory, os.path.join(directory, "Dockerfile"), name, version, {})
        builder.commit(name, version)
        # check that the updated CMD and ENTRYPOINT are present
        result = sh("docker", "run", "--rm", "-it", dr.image(name, version))
        assert result.output.strip() == "updated_content"
    finally:
        builder.kill()
