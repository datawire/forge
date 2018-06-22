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
from forge.docker import Docker, ECRDocker
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
        assert ("problem authenticating" in str(e)) or ("unauthorized" in str(e))

def test_validate():
    dr = Docker(registry, namespace, user, password)
    dr.validate()

def test_gcr():
    dr = Docker("gcr.io", "forgetest-project", "_json_key", """
{
  "type": "service_account",
  "project_id": "forgetest-project",
  "private_key_id": "c49f1dd1c0c55418796c510af2cc7f46c4327058",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDymqNXy8GUKSDx\n8/QBPTziiOyZExO1LNa31I5mc+ut4/KPEHzVtCHETpE610utxleUoyt64b9SgYEv\nySEjBJz1Nt36NNM8Pb2/+ju0L6Ha+Cui5iqfKmkHxSbCFIk25s7bh6zWWoQLw3hH\nkK7dSAJ4yeX8/xaExuYOJx9q4mkn7uNuBkIhx/YE17p2NRmuDQR8YxUadz9QgcEL\ntDXb5zBudh1MsLgBK98gZTedDNtlJMHE2zLhIJTPJ7VNwcaPP34OD5W06wcllAjZ\nxmA3eKnl/M8jdLtfrYBituNtQi2UMsNKbAffYWq1XLAvaBMLs+l9Bz4NWCxJJtTB\n0UpGt/BzAgMBAAECggEARNJgdxYKzrySJ4E0nathG8SLFeunAhT7vn+Se/bzi0to\ncnRTbY5hq9477czIn73t93EIcx4aV838N3GfsF7tJdUQSJv2tpavPwg+KqH+kO8o\n9dfEjI2L6RPhKFqKCGSWlwlYmyBnaCzl8KtXJ9f3N4vS7h/xI+6GscogbAJZoWVi\nfODsXZQqO854NwbtsjZj0xBE9ZCEc2MpcXOPn3zYcj5oRP5bNYHd8zsQ6iWGmNnp\n1IloaAFmQDIwijqraGaYHFEATB/2QwXwTjvdr0NVo7tmMkUwJ/wMxxTLgALeddu4\nfuwh1ithkzS8KRK77S/D4PSfpvtUSEu5gkZmslbZ3QKBgQD96FAysHywri/QvElg\nuqhzOmBs2pNmkt9tS5wKSc+oVZ0FlL0qMPomZOZqn2g7Os3p60LMbsriEqn/rvQO\nd3oYjWht2drdqIRPy1R7nVv7/34AYr0SIKJ/W/l3o0FllLN7hJLiJvgxCERyj1Id\na6PWbXYEW8hkbfZi+X5flMSWrwKBgQD0mnom2By5j/SzGg1doMCqb7tCxptF5tFc\nKYBtPORihm34iA77AJK5HBb7Wb4k/WwWXYGOliqRXvQ+MlDcM/iyCvfoHuqz/BWe\nYc+21GKhgbbRJz3XX1uS8UBSaEDmgHLAfXkGLvqtst+ra8MicJ+Ycfc8qNa5wRhy\nTkbwAAKzfQKBgQD0AECxtbDeCUaiDY9miXo/4aWwdgyY0iQsYDDAIlaQqlWPe3Se\nCxsZsnVLmY0M/mHLne4/j2khAFamA3c+P8rxtVLZ3jXaNYuRMxEpCfvPm6N2s2yG\n8x21zqlaM2UxPUmONcUB1/lDBXLhtKFw7HQyKFb1sU5OVO4mByVOrSSOuQKBgQDq\nWNoxPxp+OkrCEXK+wlX0tOmfd3KqTRNGjkiJ4C4bqxnPZGOd3ZW1HhFyrS98dwRI\nhTusJXkRH/03XbOU1YIu6k1LqdtJp3n67VE5pE/+1q0Vw9f+8VBl/xeWHGYZsPTA\nMTZzUy0+n8KllLA23do6Du5Fwqk+/J50XUSfihMMbQKBgH5lRaF14hj1oGckYt3P\nM45hTlW+/wUC1kJGd1gxtdpIMm3RHVGdGl9BGOwJVvAAIigbO8w01279xImcXcCb\nD+XBlvw1pDT3QfFs1t7T+x8blVqoflxsfnQW6eQB5W9arZ9CZBpSzzECppOdus46\n6J1fVJxDL9Nq5ykxjYhDYXY1\n-----END PRIVATE KEY-----\n",
  "client_email": "forge-test@forgetest-project.iam.gserviceaccount.com",
  "client_id": "106271144892298981142",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://accounts.google.com/o/oauth2/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/forge-test%40forgetest-project.iam.gserviceaccount.com"
}
    """)
    dr.validate()

START_TIME = time.time()

def test_ecr():
    dr = ECRDocker(account='020846367509', region='us-east-1',
                   aws_access_key_id=os.environ['FORGE_ECR_KEY_ID'],
                   aws_secret_access_key=os.environ['FORGE_ECR_SECRET_KEY'])
    dr.validate()
    name = "forge_test_{}".format(START_TIME)
    assert not dr.remote_exists(name, "dummy")
    dr.validate(name=name)

    describe_repos = dr.ecr.get_paginator('describe_repositories')
    for response in describe_repos.paginate():
        for repo in response['repositories']:
            repositoryName=repo['repositoryName']
            if repositoryName.startswith('forge_test_'):
                dr.ecr.delete_repository(repositoryName=repositoryName, force=True)

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
