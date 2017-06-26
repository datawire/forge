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

import base64, fnmatch, requests, os, urllib2, yaml
from blessed import Terminal
from docopt import docopt
from collections import OrderedDict
from jinja2 import Template, TemplateError

import util
from . import __version__
from .common import Service, Prototype, image, containers

class CLIError(Exception): pass

def next_page(response):
    if "Link" in response.headers:
        links = requests.utils.parse_header_links(response.headers["Link"])
        for link in links:
            if link['rel'] == 'next':
                return link['url']
    return None

def inject_token(url, token):
    if not token: return url
    parts = url.split("://", 1)
    if len(parts) == 2:
        return Elidable("%s://" % parts[0], Secret(token), "@%s" % parts[1])
    else:
        return Elidable(Secret(token), "@%s" % parts[0])

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

class Baker(object):

    def __init__(self):
        self.terminal = Terminal()
        self.pushed_cache = {}

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
        user = os.environ["USER"]
        password = None
        json_key = None

        test_image = "registry.hub.docker.com/datawire/forge-setup-test:1"

        @task()
        def validate():
            sh("docker", "login", "-u", user, "-p", Secret(password), registry)
            sh("docker", "pull", test_image)
            img = image(registry, repo, "forge_test", "dummy")
            sh("docker", "tag", test_image, img)
            self.do_push(img)
            assert self.pushed("forge_test", "dummy", registry=registry, repo=repo, user=user, password=password)

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
            e = validate.run()
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

    def dr(self, url, expected=(), user=None, password=None):
        user = user or self.user
        password = password or self.password

        response = get(url, auth=(user, password))
        if response.status_code == 401:
            challenge = response.headers['Www-Authenticate']
            if challenge.startswith("Bearer "):
                challenge = challenge[7:]
            opts = urllib2.parse_keqv_list(urllib2.parse_http_list(challenge))
            authresp = get("{realm}?service={service}&scope={scope}".format(**opts), auth=(user, password))
            if authresp.ok:
                token = authresp.json()['token']
                response = get(url, headers={'Authorization': 'Bearer %s' % token})
            else:
                raise TaskError("problem authenticating with docker registry: [%s] %s" % (authresp.status_code,
                                                                                          authresp.content))
        return response

    def gh(self, api, expected=None):
        headers = {'Authorization': 'token %s' % self.token} if self.token else None
        response = self.get("https://api.github.com/%s" % api, headers=headers, expected=expected)
        result = response.json()
        if response.ok:
            next_url = next_page(response)
            while next_url:
                response = self.get(next_url, headers=headers)
                result.extend(response.json())
                next_url = next_page(response)
        return result

    def git_pull(self, name, url):
        repodir = os.path.join(self.workdir, name)
        if not os.path.exists(repodir):
            os.makedirs(repodir)
            self.call("git", "init", cwd=repodir)
        self.call("git", "pull", inject_token(url, self.token), cwd=repodir)

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
    def scan(self):
        prototypes = OrderedDict()
        services = OrderedDict()

        def descend(path, parent):
            if not os.path.exists(path): return
            status("searching %s" % path)
            names = os.listdir(path)

            if "proto.yaml" in names:
                proto = Prototype(os.path.join(path, "proto.yaml"))
                if proto.name not in prototypes:
                    prototypes[proto.name] = proto
                return
            if "service.yaml" in names:
                version = self.version(path)
                svc = Service(version, os.path.join(path, "service.yaml"), [])
                if svc.name not in services:
                    services[svc.name] = svc
                parent = svc
            if "Dockerfile" in names and parent:
                parent.containers.append(os.path.relpath(os.path.join(path, "Dockerfile"), parent.root))

            for n in names:
                if n not in self.EXCLUDED and os.path.isdir(os.path.join(path, n)):
                    descend(os.path.join(path, n), parent)

        for root in (os.getcwd(), self.workdir):
            descend(root, None)

        result = list(services.values())
        summarize("%s" % ", ".join(s.name for s in result))
        return result

    @task()
    def baked(self, name, version):
        return bool(sh("docker", "images", "-q", image(self.registry, self.repo, name, version)).output)

    @task()
    def pushed(self, name, version, registry=None, repo=None, user=None, password=None):
        registry = registry or self.registry
        repo = repo or self.repo
        user = user or self.user
        password = password or self.password

        img = image(registry, repo, name, version)
        if img in self.pushed_cache:
            return self.pushed_cache[img]

        response = self.dr("https://%s/v2/%s/%s/manifests/%s" % (registry, repo, name, version), expected=(404,),
                           user=user, password=password)
        result = response.json()
        if 'signatures' in result and 'fsLayers' in result:
            self.pushed_cache[img] = True
            return True
        elif 'errors' in result and result['errors']:
            if result['errors'][0]['code'] == 'MANIFEST_UNKNOWN':
                self.pushed_cache[img] = False
                return False
        raise TaskError(response.content)

    def pull(self):
        repos = self.gh("orgs/%s/repos" % self.org)
        filtered = [r for r in repos if fnmatch.fnmatch(r["full_name"], self.filter)]

        urls = []
        for repo in async_map(lambda r: self.gh("repos/%s" % r["full_name"], expected=(404,)),
                              filtered):
            if "id" in repo:
                urls.append((repo["full_name"], repo["clone_url"]))

        for u in urls:
            self.git_pull.go(u)

    @task()
    def is_raw(self, (svc, name, _)):
        return not (self.pushed(name, svc.version) or self.baked(name, svc.version))

    @task()
    def bake(self, service):
        status("checking if images exist")
        raw = list(cull(self.is_raw, containers([service])))
        if not raw:
            summarize("skipped, images exist")
            return

        for svc, name, container in raw:
            status("building %s" % container)
            sh.go("docker", "build", ".", "-t", image(self.registry, self.repo, name, svc.version),
                  cwd=os.path.join(svc.root, os.path.dirname(container)))

        summarize("built %s" % (", ".join(x[-1] for x in raw)))

    @task()
    def is_unpushed(self, (svc, name, container)):
        return self.baked(name, svc.version) and not self.pushed(name, svc.version)

    @task()
    def do_push(self, img):
        self.pushed_cache.pop(img, None)
        sh("docker", "push", img)

    @task()
    def push(self, service):
        status("checking if %s containers exist" % service)
        unpushed = list(cull(self.is_unpushed, containers([service])))

        if not unpushed:
            summarize("skipped, images exist")
            return

        sh("docker", "login", "-u", self.user, "-p", Secret(self.password), self.registry)
        for svc, name, container in unpushed:
            status("pushing container %s" % container)
            self.do_push.go(image(self.registry, self.repo, name, svc.version))

        summarize("pushed %s" % ", ".join(x[-1] for x in unpushed))

    def resources(self, k8s_dir):
        return sh("kubectl", "apply", "--dry-run", "-f", k8s_dir, "-o", "name").output.split()

    def template(self, svc):
        k8s_dir = os.path.join(self.workdir, "k8s", svc.name)
        try:
            svc.deployment(self.registry, self.repo, k8s_dir)
        except TemplateError, e:
            raise TaskError(e)
        return k8s_dir, self.resources(k8s_dir)

    @task()
    def manifest(self, service):
        status("generating manifests for %s" % service.name)
        k8s_dir, resources = self.template(service)
        summarize("generated %s\nwrote manifests to %s" % (", ".join(str(r) for r in resources),
                                                           k8s_dir))
        return k8s_dir

    @task()
    def build(self, service):
        status("baking")
        self.bake(service)
        status("pushing")
        self.push(service)
        status("generating manifests")
        result = self.manifest(service)
        summarize("wrote manifests to %s" % result)
        return result

    @task()
    def deploy(self, k8s_dir):
        cmd = "kubectl", "apply", "-f", k8s_dir
        if self.dry_run:
            cmd += "--dry-run",
        result = sh(*cmd, expected=xrange(256))
        code = self.terminal.green("OK") if result.code == 0 else self.terminal.red("ERR[%s]" % result.code)
        summarize("%s -> %s\n%s" % (" ".join(cmd), code, result.output))

def get_config(args):
    if args["--config"] is not None:
        return args["--config"]

    if "FORGE_CONFIG" in os.environ:
        return os.environ["FORGE_CONFIG"]

    prev = None
    path = os.getcwd()
    while path != prev:
        prev = path
        candidate = os.path.join(path, "forge.yaml")
        if os.path.exists(candidate):
            return candidate
        path = os.path.dirname(path)
    return None

def get_workdir(conf, base):
    workdir = conf.get("workdir") or base
    if not workdir.startswith("/"):
        workdir = os.path.join(base, workdir)
    return workdir

def get_repo(conf):
    url = conf.get("docker-repo")
    if url is None:
        raise CLIError("docker-repo must be configured")
    if "/" not in url:
        raise CLIError("docker-repo must be in the form <registry-url>/<name>")
    registry, repo = url.split("/", 1)
    return registry, repo

def get_password(conf):
    pw = conf.get("password")
    if not pw:
        raise CLIError("docker password must be configured")
    return base64.decodestring(pw)

def main(args):
    baker = Baker()

    if args["setup"]: return baker.setup()

    conf_file = get_config(args)
    if not conf_file:
        raise CLIError("unable to find forge.yaml, try running `forge setup`")

    with open(conf_file, "read") as fd:
        conf = yaml.load(fd)

    baker.workdir = get_workdir(conf, os.path.dirname(os.path.abspath(conf_file)))
    baker.registry, baker.repo = get_repo(conf)

    try:
        baker.user = conf["user"]
    except KeyError, e:
        raise CLIError("missing config property: %s" % e)

    baker.token = conf.get("token")
    baker.password = get_password(conf)

    baker.filter = args.get("--filter")
    baker.dry_run = args["--dry-run"]

    @task()
    def service(svc):
        if args["bake"]: baker.bake(svc)
        if args["push"]: baker.push(svc)
        if args["manifest"]: baker.manifest(svc)
        if args["build"]: baker.build(svc)
        if args["deploy"]: baker.deploy(baker.build(svc))

    @task()
    def forge():
        services = baker.scan()
        for svc in services:
            service.go(svc)

    INCLUDED = set(["scan", "service", "bake", "push", "manifest", "build", "deploy"])
    if args["--verbose"]:
        INCLUDED.update(["GET", "CMD"])

    forge.run(task_include=lambda x: x.task.name in INCLUDED)

def call_main():
    util.setup_yaml()
    args = docopt(__doc__, version="Forge %s" % __version__)
    try:
        exit(main(args))
    except CLIError, e:
        exit(e)
    except KeyboardInterrupt, e:
        exit(e)

if __name__ == "__main__":
    call_main()
