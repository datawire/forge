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

import os, shutil, yaml
from collections import OrderedDict
from jinja2 import Environment, FileSystemLoader

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
        info = self.info()
        if "name" in info:
            return info["name"]
        else:
            return os.path.basename(self.root)

    def image(self, container):
        pfx = os.path.dirname(container)
        name = os.path.join(self.name, pfx) if pfx else self.name
        return name

    def metadata(self, registry, repo):
        metadata = OrderedDict()
        for k, v in self.info().items():
            metadata[k] = v
        if "name" not in metadata:
            metadata["name"] = self.name
        metadata["images"] = OrderedDict()
        for container in self.containers:
            img = image(registry, repo, self.image(container), self.version)
            metadata["images"][container] = img
            metadata["images"][os.path.dirname(container) or self.name] = img
        return metadata

    def deployment(self, registry, repo, target):
        k8s_dir = os.path.join(self.root, "k8s")

        metadata = self.metadata(registry, repo)
        env = Environment(loader=FileSystemLoader(k8s_dir))

        if os.path.exists(target):
            shutil.rmtree(target)
        os.makedirs(target)

        for path, dirs, files in os.walk(k8s_dir):
            for name in files:
                rendered = env.get_template(name).render(**metadata)
                with open(os.path.join(target, os.path.relpath(path, start=k8s_dir), name), "write") as f:
                    f.write(rendered)

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

def ensure_dir(path):
    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)

def render(source, target, renderer, exclude=(".git", "proto.yaml")):

    def descend(relpath):
        path = os.path.join(source, relpath)
        names = os.listdir(path)

        for x in exclude:
            if x in names:
                names.remove(x)

        dirs = [n for n in names if os.path.isdir(n)]
        files = [n for n in names if not os.path.isdir(n)]

        for name in files:
            orig = os.path.join(source, relpath, name)
            copy = os.path.join(target, renderer(os.path.join(relpath, name)))

            ensure_dir(copy)

            with open(orig, "read") as fd:
                content = renderer(fd.read())
            with open(copy, "write") as fd:
                fd.write(content)

            os.chmod(copy, os.stat(orig).st_mode)

        for name in dirs:
            descend(os.path.join(relpath, name))

    descend("")

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

    def validate(self, args):
        if not args: args = ()

        errors = []
        valid = set()
        info = self.info()
        for p in info.get('parameters', ()):
            name = p['name']
            valid.add(name)
            if name not in args:
                errors.append("missing parameter '%s'" % name)
        for a in args:
            if a not in valid:
                errors.append("extra argument '%s'" % a)
        return errors

    def instantiate(self, target, substitutions):
        def substitute(content):
            for k in substitutions:
                content = content.replace(k, str(substitutions[k]))
            return content
        render(self.root, target, substitute)

    def info(self):
        with open(self.descriptor, "read") as f:
            result = yaml.load(f)

        if 'parameters' in result:
            result['template'] = result['parameters']
        elif 'template' in result:
            result['parameters'] = result['template']
        return result

    def json(self):
        return {'name': self.name,
                'descriptor': self.info()}

    def __repr__(self):
        return "Prototype(%r)" % self.descriptor
