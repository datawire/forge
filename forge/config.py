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

from .schema import Class, Field, Union, Constant, Sequence, String, Base64, SchemaError

class Registry(object):

    def __init__(self, type, url, user, password, namespace=None):
        self.type = type
        self.url = url
        self.user = user
        self.password = password
        self.namespace = namespace

DOCKER = Class(
    "registry:docker",
    """A generic docker registry.""",
    Registry,
    Field("type", Constant('docker'), docs="This must be 'docker' for docker registries"),
    Field("url", String(), docs="The url of the docker registry."),
    Field("user", String(), docs="The docker user."),
    Field("password", Base64(), docs="The docker password, base64 encoded."),
    Field("namespace", String(), default=None)
)

class GCRRegistry(object):

    def __init__(self, type, url, project, key):
        self.type = type
        self.url = url
        self.project = project
        self.key = key

GCR = Class(
    "registry:gcr",
    """A google cloud registry.""",
    GCRRegistry,
    Field("type", Constant('gcr'), docs="The type of the registry, this will be 'gcr' for google registries"),
    Field("url", String(), docs="The url of the registry, e.g. `gcr.io`."),
    Field("project", String(), docs="The google project name."),
    Field("key", Base64(), docs="The base64 encoded json key used for authentication.")
)

class ECRRegistry(object):

    def __init__(self, type, account=None, region=None, aws_access_key_id=None, aws_secret_access_key=None):
        self.type = type
        self.account = account
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key

ECR = Class(
    "registry:ecr",
    """An amazon ECR registry.""",
    ECRRegistry,
    Field("type", Constant('ecr'), docs="The type of the registry, this will be 'ecr' for amazon registires"),
    Field("account", String("string", "integer"), default=None, docs="The amazon account id to use."),
    Field("region", String(), default=None, docs="The amazon region to use."),
    Field("aws_access_key_id", String(), default=None, docs="The id of the aws access key to use."),
    Field("aws_secret_access_key", String(), default=None, docs="The aws secrete access key.")
)

class Config(object):

    def __init__(self, search_path=None, registry=None, docker_repo=None, user=None, password=None, workdir=None):
        self.search_path = search_path or ()

        if registry:
            if docker_repo:
                raise SchemaError("cannot specify both registry and docker-repo")
            if user:
                raise SchemaError("cannot specify both registry and user")
            if password:
                raise SchemaError("cannot specify both registry and password")
        else:
            if "/" not in docker_repo:
                raise SchemaError("docker-repo must be in the form <registry-url>/<namespace>")
            url, namespace = docker_repo.split("/", 1)
            registry = Registry(type="docker",
                                url=url,
                                namespace=namespace,
                                user=user,
                                password=password)

        self.registry = registry

CONFIG = Class(
    "forge.yaml",
    """
    Global forge configuration. Currently this consits of docker
    registry configuration and credentials.
    """,
    Config,
    Field("search-path", Sequence(String()), "search_path", default=None, docs="Search path for service dependencies."),
    Field("registry", Union(DOCKER, GCR, ECR), default=None),
    Field("docker-repo", String(), "docker_repo", default=None, docs="Deprecated, use registry instead."),
    Field("user", String(), default=None, docs="Deprecated, use registry instead."),
    Field("password", Base64(), default=None, docs="Deprecated, use registry instead."),
    Field("workdir", String(), default=None, docs="deprecated")
)

def load(*args, **kwargs):
    return CONFIG.load(*args, **kwargs)
