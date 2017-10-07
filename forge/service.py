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

import hashlib, jsonschema, os, pathspec, util, yaml
from collections import OrderedDict
from .jinja2 import render, renders
from .docker import image
from .tasks import sh, task, TaskError

with open(os.path.join(os.path.dirname(__file__), "service.json")) as f:
    SCHEMA = yaml.load(f)

def load_service_yaml(path):
    with open(path, "read") as f:
        return load_service_yamls(path, f.read())

@task()
def load_service_yamls(name, content):
    rendered = renders(name, content, env=os.environ)
    try:
        info = yaml.load(rendered)
    except yaml.parser.ParserError, e:
        task.echo("==unparseable service yaml==")
        for idx, line in enumerate(rendered.splitlines()):
            task.echo("%s: %s" % (idx + 1, line))
        task.echo("============================")
        raise TaskError("error parsing service yaml: %s" % e)

    try:
        jsonschema.validate(info, SCHEMA)
        return info
    except jsonschema.ValidationError, e:
        best = jsonschema.exceptions.best_match(e.context)
        raise TaskError("error loading %s: %s" % (name, (best or e).message))

def get_ignores(directory):
    ignorefiles = [os.path.join(directory, ".gitignore"),
                   os.path.join(directory, ".forgeignore")]
    ignores = []
    for path in ignorefiles:
        if os.path.exists(path):
            with open(path) as fd:
                ignores.extend(fd.readlines())
    return ignores

def get_ancestors(path, stop="/"):
    path = os.path.abspath(path)
    stop = os.path.abspath(stop)
    if os.path.samefile(path, stop):
        return
    else:
        parent = os.path.dirname(path)
        for d in get_ancestors(parent, stop):
            yield d
        yield parent

class Discovery(object):

    def __init__(self):
        self.services = OrderedDict()

    @task()
    def search(self, directory):
        directory = os.path.abspath(directory)
        if not os.path.exists(directory):
            raise TaskError("no such directory: %s" % directory)
        if not os.path.isdir(directory):
            raise TaskError("not a directory: %s" % directory)

        base_ignores = [".git", ".forge"]
        gitdir = util.search_parents(".git", directory)
        if gitdir is None:
            gitroot = directory
        else:
            gitroot = os.path.dirname(gitdir)

        for d in get_ancestors(directory, gitroot):
            base_ignores.extend(get_ignores(d))

        found = []
        def descend(path, parent, ignores):
            if not os.path.exists(path): return

            ignores += get_ignores(path)
            spec = pathspec.PathSpec.from_lines('gitwildmatch', ignores)
            names = [n for n in os.listdir(path) if not spec.match_file(os.path.join(path, n))]

            if "service.yaml" in names:
                svc = Service(os.path.join(path, "service.yaml"))
                if svc.name not in self.services:
                    self.services[svc.name] = svc
                found.append(svc)
                parent = svc

            if "Dockerfile" in names and parent:
                parent.dockerfiles.append(os.path.relpath(os.path.join(path, "Dockerfile"), parent.root))

            for n in names:
                child = os.path.join(path, n)
                if os.path.isdir(child):
                    descend(child, parent, ignores)
                elif parent:
                    parent.files.append(os.path.relpath(child, parent.root))

        descend(directory, None, base_ignores)
        return found

    def resolve(self, svc, dep):
        gh = Github(None)
        target = os.path.join(svc.root, ".forge", dep)
        if not os.path.exists(target):
            url = gh.remote(svc.root)
            if url is None: return False
            parts = url.split("/")
            prefix = "/".join(parts[:-1])
            remote = prefix + "/" + dep + ".git"
            if gh.exists(remote):
                gh.clone(remote, target)
        found = self.search(target)
        return dep in [svc.name for svc in found]

    @task()
    def dependencies(self, targets):
        todo = [self.services[t] for t in targets]
        visited = set()
        added = []
        missing = []
        while todo:
            svc = todo.pop()
            if svc in visited:
                continue
            visited.add(svc)
            for r in svc.requires:
                if r not in self.services:
                    if not self.resolve(svc, r): missing.append(r)
                if r not in targets and r not in added:
                    added.append(r)
                if r in self.services:
                    todo.append(self.services[r])

        if missing:
            raise TaskError("required service(s) missing: %s" % ", ".join(missing))
        else:
            return added

def shafiles(root, files):
    result = hashlib.sha1()
    result.update("files %s\0" % len(files))
    for name in files:
        result.update("file %s\0" % name)
        try:
            with open(os.path.join(root, name)) as fd:
                result.update(fd.read())
        except IOError, e:
            if e.errno != errno.ENOENT:
                raise
    return result.hexdigest()

def is_git(path):
    if os.path.exists(os.path.join(path, ".git")):
        return True
    elif path not in ('', '/'):
        return is_git(os.path.dirname(path))
    else:
        return False

def get_version(path, dirty):
    if is_git(path):
        result = sh("git", "diff", "--quiet", "HEAD", ".", cwd=path, expected=(0, 1))
        if result.code == 0:
            line = sh("git", "log", "-n1", "--format=oneline", "--", ".", cwd=path).output.strip()
            if line:
                version = line.split()[0]
                return "%s.git" % version
    return dirty

class Service(object):

    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.dockerfiles = []
        self.files = []
        self._info = None
        self._version = None

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

    @property
    def version(self):
        if self._version is None:
            self._version = get_version(self.root, "%s.sha" % shafiles(self.root, self.files))
        return self._version

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

    @property
    def manifest_dir(self):
        return os.path.join(self.root, "k8s")

    def deployment(self, registry, repo, target):
        k8s_dir = self.manifest_dir
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
        for idx, c in enumerate(containers):
            if isinstance(c, basestring):
                yield Container(self, c, index=idx)
            else:
                yield Container(self, c["dockerfile"], c.get("context", None), c.get("args", None),
                                c.get("rebuild", None), index=idx)

    def json(self):
        return {'name': self.name,
                'owner': self.name,
                'version': self.version,
                'descriptor': self.info(),
                'tasks': []}

    def __repr__(self):
        return "%s:%s" % (self.name, self.version)

class Container(object):

    def __init__(self, service, dockerfile, context=None, args=None, rebuild=None, index=None):
        self.service = service
        self.dockerfile = dockerfile
        self.context = context or os.path.dirname(self.dockerfile)
        self.args = args or {}
        self.rebuild_root = rebuild.get("root", "/") if rebuild else None
        self.rebuild_sources = rebuild.get("sources", ()) if rebuild else ()
        self.rebuild_command = rebuild.get("command") if rebuild else None
        self.index = index

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

    @property
    def rebuild(self):
        return self.rebuild_sources or self.rebuild_command

    @task()
    def build(self, forge):
        if self.rebuild:
            builder = forge.docker.builder(self.abs_context, self.abs_dockerfile, self.image, self.version, self.args)
            builder.run("mkdir", "-p", self.rebuild_root)
            for src in self.rebuild_sources:
                abs_src = os.path.join(self.service.root, src)
                tgt_src = os.path.join(self.rebuild_root, src)
                if os.path.isdir(abs_src):
                    builder.run("rm", "-rf", tgt_src)
                builder.cp(abs_src, tgt_src)
            if self.rebuild_command:
                builder.run("/bin/sh", "-c", self.rebuild_command)
            builder.commit(self.image, self.version)
        else:
            forge.docker.build(self.abs_context, self.abs_dockerfile, self.image, self.version, self.args)
