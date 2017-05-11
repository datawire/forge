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

def image(registry, repo, name, version):
    return "%s/%s/%s:%s" % (registry, repo, name, version)

def containers(services):
    for svc in services:
        for container in svc.containers:
            yield svc, svc.image(container), container

class Stats(object):

    def __init__(self, good=0.0, bad=0.0, slow=0.0):
        self.good = good
        self.bad = bad
        self.slow = slow

    def json(self):
        return {'good': self.good, 'bad': self.bad, 'slow': self.slow}

class Service(object):

    def __init__(self, version, descriptor, containers):
        self.version = version
        self.descriptor = descriptor
        self.containers = containers
        self.stats = Stats()

    @property
    def root(self):
        return os.path.dirname(self.descriptor)

    @property
    def name(self):
        return os.path.basename(self.root)

    def image(self, container):
        pfx = os.path.dirname(container)
        name = os.path.join(self.name, pfx) if pfx else self.name
        return name

    def metadata(self, registry, repo):
        filename = os.path.join(self.root, "metadata.yaml")
        metadata = OrderedDict()
        metadata["name"] = self.name
        metadata["images"] = OrderedDict()
        for container in self.containers:
            img = image(registry, repo, self.image(container), self.version)
            metadata["images"][container] = img
            metadata["images"][os.path.dirname(container) or self.name] = img
        return filename, metadata

    def info(self):
        with open(self.descriptor, "read") as f:
            return yaml.load(f)

    def json(self):
        return {'name': self.name,
                'owner': self.name,
                'version': self.version,
                'descriptor': self.info(),
                'stats': self.stats.json(),
                'tasks': []}

    def __repr__(self):
        return "Service(%r, %r, %r)" % (self.version, self.descriptor, self.containers)

class Prototype(object):

    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.stats = Stats()

    @property
    def root(self):
        return os.path.dirname(self.descriptor)

    @property
    def name(self):
        return os.path.basename(self.root)

    def info(self):
        with open(self.descriptor, "read") as f:
            return yaml.load(f)

    def json(self):
        return {'name': self.name,
                'descriptor': self.info()}

    def __repr__(self):
        return "Prototype(%r)" % self.descriptor
