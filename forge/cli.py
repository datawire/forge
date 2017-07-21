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

"""
Forge CLI.

Usage:
  forge setup
  forge bake [-v] [--config=<config>]
  forge push [-v] [--config=<config>]
  forge manifest [-v] [--config=<config>]
  forge build [-v] [--config=<config>]
  forge deploy [-v] [--config=<config>] [--dry-run]
  forge -h | --help
  forge --version

Options:
  --config=<config>   Forge config file location.
  --filter=<pattern>  Only operate on services matching <pattern>. [default: *]
  -h --help           Show this screen.
  --version           Show version.
  -v,--verbose        Display more information.
"""

from .tasks import (
    cull,
    get,
    project,
    setup,
    sh,
    status,
    summarize,
    sync,
    task,
    ERROR,
    Elidable,
    Secret,
    TaskError
)

setup()

import getpass

import base64, fnmatch, requests, os, sys, yaml
from docopt import docopt
from dotenv import find_dotenv, load_dotenv
from collections import OrderedDict
from jinja2 import Template, TemplateError

import util
from . import __version__
from .service import Service, containers
from .docker import Docker
from .github import Github
from .istio import istio
from .output import Terminal

ENV = find_dotenv()
if ENV: load_dotenv(ENV)

class CLIError(Exception): pass

SETUP_TEMPLATE = Template("""# Global forge configuration
# DO NOT CHECK INTO GITHUB, THIS FILE CONTAINS SECRETS
workdir: work
docker-repo: {{docker}}
user: {{user}}
password: >
  {{password}}
""")

def file_contents(path):
    try:
        with open(os.path.expanduser(os.path.expandvars(path)), "read") as fd:
            return fd.read()
    except IOError, e:
        print "  %s" % e
        return None

class Forge(object):

    def __init__(self):
        self.terminal = Terminal()
        self.services = OrderedDict()

    def prompt(self, msg, default=None, loader=None, echo=True):
        prompt = "%s: " % msg if default is None else "%s[%s]: " % (msg, default)
        prompter = raw_input if echo else getpass.getpass

        while True:
            value = prompter(prompt) or default
            if value is None: continue
            if loader is not None:
                loaded = loader(value)
                if loaded is None:
                    continue
            if loader:
                return value, loaded
            else:
                return value

    def setup(self):
        print self.terminal.bold("== Checking Kubernetes Setup ==")
        print

        checks = (("kubectl", "version", "--short"),
                  ("kubectl", "get", "service", "kubernetes", "--namespace", "default"))

        for cmd in checks:
            e = sh.run(*cmd)
            if e.result is ERROR:
                print
                raise CLIError(self.terminal.red("== Kubernetes Check Failed ==") +
                               "\n\nPlease make sure kubectl is installed/configured correctly.")

        registry = "registry.hub.docker.com"
        repo = None
        user = os.environ.get("USER", "")
        password = None
        json_key = None

        @task()
        def validate():
            dr = Docker(registry, repo, user, password)
            dr.validate()

        print
        print self.terminal.bold("== Setting up Docker ==")

        while True:
            print
            registry = self.prompt("Docker registry", registry)
            user = self.prompt("Docker user", user)
            repo = self.prompt("Docker organization", user)
            if user == "_json_key":
                json_key, password = self.prompt("Path to json key", json_key, loader=file_contents)
            else:
                password = self.prompt("Docker password", echo=False)

            print
            e = validate.run(task_include=lambda x: x.task.name in ('pull', 'push', 'tag'))
            if e.result is ERROR:
                print
                print self.terminal.red("-- please try again --")
                continue
            else:
                break

        print

        config = SETUP_TEMPLATE.render(
            docker="%s/%s" % (registry, repo),
            user=user,
            password=base64.encodestring(password).replace("\n", "\n  ")
        )

        config_file = "forge.yaml"

        print self.terminal.bold("== Writing config to %s ==" % config_file)

        with open(config_file, "write") as fd:
            fd.write(config)

        print
        print config.strip()
        print

        print self.terminal.bold("== Done ==")

    EXCLUDED = set([".git"])

    def is_git(self, path):
        if os.path.exists(os.path.join(path, ".git")):
            return True
        elif path not in ('', '/'):
            return self.is_git(os.path.dirname(path))
        else:
            return False

    def version(self, root):
        if self.is_git(root):
            result = sh("git", "diff", "--quiet", ".", cwd=root, expected=(0, 1))
            if result.code == 0:
                return "%s.git" % sh("git", "rev-parse", "HEAD", cwd=root).output.strip()
        return "%s.ephemeral" % util.shadir(root)

    @task()
    def scan(self, root):
        workexists = os.path.exists(self.workdir)
        found = []
        def descend(path, parent):
            if not os.path.exists(path): return
            status("searching %s" % path)
            names = os.listdir(path)

            if "service.yaml" in names:
                version = self.version(path)
                svc = Service(version, os.path.join(path, "service.yaml"), [])
                if svc.name not in self.services:
                    self.services[svc.name] = svc
                    found.append(svc.name)
                    status("searching %s, found %s" % (path, svc.name))
                parent = svc
            if "Dockerfile" in names and parent:
                parent.containers.append(os.path.relpath(os.path.join(path, "Dockerfile"), parent.root))

            for n in names:
                child = os.path.join(path, n)
                if n not in self.EXCLUDED and os.path.isdir(child) and (not workexists or
                                                                        not os.path.samefile(child, self.workdir)):
                    descend(child, parent)

        descend(root, None)
        summarize("%s -> %s" % (root, ", ".join(found) or "(no services)"))
        return found

    def resolve(self, svc, dep):
        gh = Github(None)
        target = os.path.join(self.workdir, dep)
        if not os.path.exists(target):
            url = gh.remote(svc.root)
            if url is None: return False
            parts = url.split("/")
            prefix = "/".join(parts[:-1])
            remote = prefix + "/" + dep + ".git"
            if gh.exists(remote):
                gh.clone(remote, target)
        found = self.scan(target)
        return dep in found

    @task()
    def dependencies(self, targets):
        status(", ".join(targets))
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
            summarize("%s -> %s" % (", ".join(targets), ", ".join(added)))
            return added

    @task()
    def bake(self, service):
        status("checking if images exist")
        raw = list(cull(lambda (svc, name, _): not self.docker.exists(name, svc.version), containers([service])))
        baked = []
        if not raw:
            summarize("skipped, images exist")
            return baked

        for svc, name, container in raw:
            status("building %s for %s " % (container, svc.name))
            self.docker.build.go(os.path.join(svc.root, os.path.dirname(container)), name, svc.version)
            baked.append(container)

        summarize("built %s" % (", ".join(x[-1] for x in raw)))
        return baked

    @task()
    def push(self, service):
        status("checking if %s containers exist" % service)
        unpushed = list(cull(lambda (svc, name, _): self.docker.needs_push(name, svc.version), containers([service])))

        pushed = []
        if not unpushed:
            summarize("skipped, images exist")
            return []

        for svc, name, container in unpushed:
            status("pushing container %s" % container)
            pushed.append(self.docker.push(name, svc.version))

        summarize("pushed %s" % ", ".join(x[-1] for x in unpushed))
        return pushed

    def resources(self, k8s_dir):
        return sh("kubectl", "apply", "--dry-run", "-f", k8s_dir, "-o", "name").output.split()

    def template(self, svc):
        k8s_dir = os.path.join(self.workdir, "k8s", svc.name)
        try:
            svc.deployment(self.docker.registry, self.docker.namespace, k8s_dir)
        except TemplateError, e:
            raise TaskError(e)
        return k8s_dir, self.resources(k8s_dir)

    @task()
    def manifest(self, service):
        status("generating manifests for %s" % service.name)
        k8s_dir, resources = self.template(service)
        istioify = service.info().get("istio", False)
        if istioify:
            status("istioifying kube manifests")
            istio(k8s_dir)
        summarize("generated %s\nwrote %smanifests to %s" % (", ".join(str(r) for r in resources),
                                                             "istioified " if istioify else "",
                                                             k8s_dir))
        return k8s_dir

    @task()
    def build(self, service):
        baked = self.bake(service)
        pushed = self.push(service)
        result = self.manifest(service)

        lines = []
        if baked:
            lines.append("%s" % ", ".join(baked))
        if pushed:
            lines.append("%s %s" % (self.terminal.green("pushed"), (", ".join(pushed))))
        lines.append("%s %s" % (self.terminal.green("manifests"), result))

        summarize("\n".join(lines))
        return result

    @task()
    def deploy(self, k8s_dir):
        cmd = "kubectl", "apply", "-f", k8s_dir
        if self.dry_run:
            cmd += "--dry-run",
        result = sh(*cmd, expected=xrange(256))
        code = self.terminal.green("OK") if result.code == 0 else self.terminal.red("ERR[%s]" % result.code)
        summarize("%s -> %s\n%s" % (" ".join(cmd), code, result.output))

def search_parents(name, start=None):
    prev = None
    path = start or os.getcwd()
    while path != prev:
        prev = path
        candidate = os.path.join(path, name)
        if os.path.exists(candidate):
            return candidate
        path = os.path.dirname(path)
    return None

def get_config(args):
    if args["--config"] is not None:
        return args["--config"]

    if "FORGE_CONFIG" in os.environ:
        return os.environ["FORGE_CONFIG"]

    return search_parents("forge.yaml")

def get_workdir(conf, base):
    workdir = conf.get("workdir") or base
    if not workdir.startswith("/"):
        workdir = os.path.join(base, workdir)
    return workdir

def get_password(conf):
    pw = conf.get("password")
    if not pw:
        raise CLIError("docker password must be configured")
    return base64.decodestring(pw)

def get_docker(conf):
    url = conf.get("docker-repo")

    if url is None:
        raise CLIError("docker-repo must be configured")
    if "/" not in url:
        raise CLIError("docker-repo must be in the form <registry-url>/<namespace>")
    registry, namespace = url.split("/", 1)

    try:
        user = conf["user"]
    except KeyError, e:
        raise CLIError("missing config property: %s" % e)

    return Docker(registry, namespace, user, get_password(conf))

def main(argv=None):
    args = docopt(__doc__, argv or sys.argv[1:], version="Forge %s" % __version__)
    forge = Forge()

    if args["setup"]: return forge.setup()

    conf_file = get_config(args)
    if not conf_file:
        raise CLIError("unable to find forge.yaml, try running `forge setup`")

    with open(conf_file, "read") as fd:
        conf = yaml.load(fd)

    base = os.path.dirname(os.path.abspath(conf_file))
    forge.workdir = get_workdir(conf, base)
    forge.docker = get_docker(conf)

    forge.filter = args.get("--filter")
    forge.dry_run = args["--dry-run"]

    @task()
    def service(name):
        svc = forge.services[name]
        if args["bake"]: forge.bake(svc)
        if args["push"]: forge.push(svc)
        if args["manifest"]: forge.manifest(svc)
        if args["build"]: forge.build(svc)
        if args["deploy"]: forge.deploy(forge.build(svc))
        summarize(forge.terminal.white(name))

    @task("forge")
    def root():
        start = search_parents("service.yaml")
        if start:
            path = os.path.dirname(start)
        else:
            path = os.getcwd()
        services = forge.scan(path)
        if not os.path.samefile(path, base):
            forge.scan(base)
        if services:
            services.extend(forge.dependencies(services))
        for name in services:
            service.go(name)

    INCLUDED = set(["scan", "dependencies", "service", "build", "deploy"])
    if args["--verbose"]:
        INCLUDED.update(["GET", "CMD"])

    root.run(task_include=lambda x: x.task.name in INCLUDED)

def call_main():
    util.setup_yaml()
    try:
        exit(main())
    except CLIError, e:
        exit(e)
    except KeyboardInterrupt, e:
        exit(e)

if __name__ == "__main__":
    call_main()
