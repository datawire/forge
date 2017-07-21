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

import os, yaml
from collections import OrderedDict
from .jinja2 import render
from .docker import image

def containers(services):
    for svc in services:
        for container in svc.containers:
            yield svc, svc.image(container), container

class Service(object):

    def __init__(self, version, descriptor, containers):
        self.version = version
        self.descriptor = descriptor
        self.containers = containers

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
        build["images"] = OrderedDict()
        for container in self.containers:
            img = image(registry, repo, self.image(container), self.version)
            build["images"][container] = img
        return metadata

    def deployment(self, registry, repo, target):
        k8s_dir = os.path.join(self.root, "k8s")
        metadata = self.metadata(registry, repo)
        render(k8s_dir, target, **metadata)

    def info(self):
        with open(self.descriptor, "read") as f:
            return yaml.load(f)

    @property
    def requires(self):
        value = self.info().get("requires", ())
        if isinstance(value, basestring):
            return [value]
        else:
            return value

    def json(self):
        return {'name': self.name,
                'owner': self.name,
                'version': self.version,
                'descriptor': self.info(),
                'tasks': []}

    def __repr__(self):
        return "%s:%s" % (self.name, self.version)
