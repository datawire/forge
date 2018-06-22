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

from .schema import Class, Field, Union, Constant, Map, Sequence, Boolean, Integer, String, Base64, SchemaError

class Registry(object):

    def __init__(self, type, url, verify, user, password, namespace=None):
        self.type = type
        self.url = url
        self.verify = verify
        self.user = user
        self.password = password
        self.namespace = namespace

DOCKER = Class(
    "registry:docker",
    """A generic Docker registry.""",
    Registry,
    Field("type", Constant('docker'), docs="This must be 'docker' for docker registries"),
    Field("url", String(), docs="The url of the docker registry."),
    Field("verify", Boolean(), default=True,
          docs="A boolean that indicates whether or not to verify the SSL connection to the registry. This defaults to true. Set this to false if you are using a registry with self-signed certs."),
    Field("user", String(), default=None, docs="The docker user."),
    Field("password", Base64(), default=None, docs="The docker password, base64 encoded."),
    Field("namespace", String(), docs="The namespace for the docker registry. For docker hub this is a user or an organization. This is used as the first path component of the registry URL, for example: registry.hub.docker.com/<namespace>")
)

class GCRRegistry(object):

    def __init__(self, type, url, project, key=None):
        self.type = type
        self.url = url
        self.project = project
        self.key = key

GCR = Class(
    "registry:gcr",
    """A Google Cloud registry.""",
    GCRRegistry,
    Field("type", Constant('gcr'), docs="The type of the registry; this will be 'gcr' for Google registries"),
    Field("url", String(), docs="The url of the registry, e.g. `gcr.io`."),
    Field("project", String(), docs="The Google project name."),
    Field("key", Base64(), default=None, docs="The base64 encoded JSON key used for authentication.")
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
    """An Amazon ECR registry.""",
    ECRRegistry,
    Field("type", Constant('ecr'), docs="The type of the registry; this will be 'ecr' for amazon registries"),
    Field("account", String("string", "integer"), default=None, docs="The amazon account id to use."),
    Field("region", String(), default=None, docs="The Amazon region to use."),
    Field("aws_access_key_id", String(), default=None, docs="The id of the AWS access key to use."),
    Field("aws_secret_access_key", String(), default=None, docs="The AWS secret access key.")
)

class LocalRegistry(object):

    def __init__(self, type):
        self.type = type

LOCAL = Class(
    "registry:local",
    """A local registry.""",
    LocalRegistry,
    Field("type", Constant('local'), docs="The type of the registry; this will be 'local' for local registries")
)

class Profile(object):

    def __init__(self, search_path = None, registry = None):
        self.search_path = search_path or ()
        self.registry = registry

PROFILE = Class(
    "profile",
    """
    Profile-specific settings.
    """,
    Profile,
    Field("search-path", Sequence(String()), "search_path", default=None, docs="Search path for service dependencies."),
    Field("registry", Union(DOCKER, GCR, ECR, LOCAL), default=None)
)

class Config(object):

    def __init__(self, search_path=None, registry=None, docker_repo=None, user=None, password=None, workdir=None,
                 profiles=None, concurrency=None):
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
                                verify=True,
                                namespace=namespace,
                                user=user,
                                password=password)

        self.registry = registry
        self.profiles = profiles or {}
        if "default" not in self.profiles:
            self.profiles["default"] = Profile(search_path=self.search_path, registry=self.registry)
        for p in self.profiles.values():
            if p.search_path is None:
                p.search_path = self.search_path
            if p.registry is None:
                p.registry = self.registry
        self.concurrency = concurrency

CONFIG = Class(
    "forge.yaml",
    """
    The forge.yaml file contains the global Forge configuration information. Currently this consists of Docker Registry configuration and credentials.
    A forge.yaml is automatically created as part of the forge setup process; it can also be created by hand.
    """,
    Config,
    *(tuple(PROFILE.fields.values()) +
      (Field("docker-repo", String(), "docker_repo", default=None, docs="Deprecated, use registry instead."),
       Field("user", String(), default=None, docs="Deprecated, use registry instead."),
       Field("password", Base64(), default=None, docs="Deprecated, use registry instead."),
       Field("workdir", String(), default=None, docs="deprecated"),
       Field("profiles", Map(PROFILE), default=None, docs="A map keyed by profile-name of profile-specific settings."),
       Field("concurrency", Integer(), default=5, docs="This controls the maximum number of parallel builds."),
      ))
)

def load(*args, **kwargs):
    return CONFIG.load(*args, **kwargs)
