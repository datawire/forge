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

from .schema import Any, Class, Field, Union, Constant, Map, Scalar, Sequence, String, Base64, SchemaError, OMIT, \
    Boolean

REBUILD = Class(
    "rebuild",
    """
    Rebuild metadata for containers. When you specify the appropriate
    rebuild properties, forge will use these to perform fast incremental
    container builds.
    """,
    Field("root", String(), default=OMIT,
          docs="The root path where sources live inside the container. All files and directories listed in the sources array are copied to this location prior to executing a build."),
    Field("command", String(), default=OMIT,
          docs="The command that is executed inside the container in order to perform a build."),
    Field("sources", Sequence(String()), default=OMIT,
          docs="An array of files or directories that will be copied into the container prior to performing a build.")
)

CONTAINER = Class(
    "container",
    """
    Defines and describes the build inputs for a container.
    """,
    Field("dockerfile", String(), docs="The path to the dockerfile."),
    Field("name", String(), default=OMIT, docs="The name to use for the container."),
    Field("context", String(), default=OMIT, docs="The build context."),
    Field("args", Map(String("string", "integer", "float")), default=OMIT, docs="Build arguments."),
    Field("rebuild", REBUILD, default=OMIT)
)

PROFILE = Map(Any())

ISTIO = Class(
    "istio",
    """
    Configures how istioctl kube-inject is called before applying yaml.
    """,
    Field("enabled", Boolean(), default=OMIT, docs="If true run istioctl kube-inject before applying yaml."),
    Field("includeIPRanges", Sequence(String()), default=OMIT, docs="Comma separated list of IP ranges in CIDR form passed to istioctl kube-inject.")
)

SERVICE = Class(
    "service.yaml",
    """
    Service configuration.
    """,
    Field("name", String(), docs="The name of the service."),
    Field("requires", Union(Sequence(String()), String()), default=OMIT,
          docs="A list of any services require for this service to function"),
    Field("containers", Sequence(Union(String(), CONTAINER)), default=OMIT,
          docs="A list of containers that form this service. If this is not supplied then any Dockerfile is assumed."),
    Field("profiles", Map(PROFILE), default=OMIT,
          docs="A mapping from profile name to profile-specific values."),
    Field("branches", Map(String()), default=OMIT, docs="A mapping from branch pattern to profile name."),
    Field("config", Any(), default=OMIT, docs="Arbitrary application defined configuration parameters for a service."),
    Field("istio", Union(Boolean(), ISTIO), default=OMIT, docs="Run istioctl kube-inject with the specified settings before applying yaml."),
    strict=False
)

def load(*args, **kwargs):
    return SERVICE.load(*args, **kwargs)
