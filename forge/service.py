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

import jsonschema, os, yaml
from collections import OrderedDict
from .jinja2 import render, renders
from .docker import image
from .tasks import task, TaskError

with open(os.path.join(os.path.dirname(__file__), "service.json")) as f:
    SCHEMA = yaml.load(f)

def load_service_yaml(path):
    with open(path, "read") as f:
        return load_service_yamls(path, f.read())

@task()
def load_service_yamls(name, content):
    try:
        info = yaml.load(renders(name, content, env=os.environ))
        jsonschema.validate(info, SCHEMA)
        return info
    except jsonschema.ValidationError, e:
        best = jsonschema.exceptions.best_match(e.context)
        raise TaskError((best or e).message)

class Service(object):

    def __init__(self, version, descriptor):
        self.version = version
        self.descriptor = descriptor
        self.dockerfiles = []
        self._info = None

    @property
    def root(self):
        return os.path.dirname(self.descriptor)

    @property
    def name(self):
        info = self.info()
        if "name" in info:
            return info["name"]
        else:
            return os.path.basename(self.root)

    def image(self, container):
        pfx = os.path.dirname(container)
        name = os.path.join(self.name, pfx) if pfx else self.name
        name = name.replace("/", "-")
        return name

    def metadata(self, registry, repo):
        metadata = OrderedDict()
        metadata["env"] = os.environ
        metadata["service"] = self.info()
        if "name" not in metadata["service"]:
            metadata["service"]["name"] = self.name
        build = OrderedDict()
        metadata["build"] = build
        build["version"] = self.version
        build["images"] = OrderedDict()
        for container in self.dockerfiles:
            img = image(registry, repo, self.image(container), self.version)
            build["images"][container] = img
        return metadata

    def deployment(self, registry, repo, target):
        k8s_dir = os.path.join(self.root, "k8s")
        metadata = self.metadata(registry, repo)
        render(k8s_dir, target, **metadata)

    def info(self):
        if self._info is None:
            self._info = load_service_yaml(self.descriptor)
        return self._info

    @property
    def requires(self):
        value = self.info().get("requires", ())
        if isinstance(value, basestring):
            return [value]
        else:
            return value

    @property
    def containers(self):
        info = self.info()
        containers = info.get("containers", self.dockerfiles)
        for c in containers:
            if isinstance(c, basestring):
                yield Container(self, c)
            else:
                yield Container(self, c["dockerfile"], c.get("context", None), c.get("args", None))

    def json(self):
        return {'name': self.name,
                'owner': self.name,
                'version': self.version,
                'descriptor': self.info(),
                'tasks': []}

    def __repr__(self):
        return "%s:%s" % (self.name, self.version)

class Container(object):

    def __init__(self, service, dockerfile, context=None, args=None):
        self.service = service
        self.dockerfile = dockerfile
        self.context = context or os.path.dirname(self.dockerfile)
        self.args = args or {}

    @property
    def version(self):
        return self.service.version

    @property
    def image(self):
        return self.service.image(self.dockerfile)

    @property
    def abs_dockerfile(self):
        return os.path.join(self.service.root, self.dockerfile)

    @property
    def abs_context(self):
        return os.path.join(self.service.root, self.context)
