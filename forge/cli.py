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
  sw pull [--config=<config>] [--token=<token>] [--workdir=<path>]  [--filter=<pattern>] [ <organization> ]
  sw bake [--config=<config>] [--user=<user>] [--password=<password>] [ <docker-repo> ]
  sw push [--config=<config>] [--user=<user>] [--password=<password>] [ <docker-repo> ]
  sw deploy [--config=<config>] [--dry-run] [ <docker-repo> ]
  sw create <prototype> <arguments> [-o,--output <target>]
  sw serve [--config=<config>] [--token=<token>] [--user=<user>] [--password=<password>] [--workdir=<path>] [ <organization> <docker-repo> ]
  sw -h | --help
  sw --version

Options:
  --config=<config>     Yaml config file location.
  --filter=<pattern>    Only operate on services matching <pattern>. [default: *]
  --token=<token>       Github authentication token.
  --workdir=<path>      Work directory.
  -h --help             Show this screen.
  --version             Show version.
"""

import eventlet
eventlet.sleep() # workaround for import cycle: https://github.com/eventlet/eventlet/issues/401
eventlet.monkey_patch()

import fnmatch, requests, os, urllib2, yaml
from docopt import docopt
from collections import OrderedDict

import util
from ._metadata import __version__
from .workstream import Workstream, Elidable, Secret
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

class Baker(Workstream):

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

    def scan(self):
        prototypes = []
        services = []

        def descend(path, parent):
            names = os.listdir(path)

            if "proto.yaml" in names:
                prototypes.append(Prototype(os.path.join(path, "proto.yaml")))
                return
            if "service.yaml" in names:
                version = self.call("git", "rev-parse", "HEAD", cwd=path).output.strip()
                svc = Service(version, os.path.join(path, "service.yaml"), [])
                services.append(svc)
                parent = svc
            if "Dockerfile" in names and parent:
                parent.containers.append(os.path.relpath(os.path.join(path, "Dockerfile"), parent.root))

            for n in names:
                if n not in self.EXCLUDED and os.path.isdir(os.path.join(path, n)):
                    descend(os.path.join(path, n), parent)

        descend(self.workdir, None)
        return prototypes, services
    
    def baked(self, name, version):
        result = self.call("docker", "images", "-q", image(self.registry, self.repo, name, version))
        return result.output

    def pushed(self, name, version):
        url = "https://%s/v2/%s/%s/manifests/%s" % (self.registry, self.repo, name, version)
        response = self.get(url, auth=(self.user, self.password), expected=(404, 401))
        if response.status_code == 401:
            challenge = response.headers['Www-Authenticate']
            if challenge.startswith("Bearer "):
                challenge = challenge[7:]
            opts = urllib2.parse_keqv_list(urllib2.parse_http_list(challenge))
            token = self.get("{realm}?service={service}&scope={scope}".format(**opts),
                             auth=(self.user, self.password)).json()['token']
            response = self.get(url, headers={'Authorization': 'Bearer %s' % token}, expected=(404,))
        result = response.json()
        if 'signatures' in result and 'fsLayers' in result:
            return True
        elif 'errors' in result and result['errors']:
            if result['errors'][0]['code'] == 'MANIFEST_UNKNOWN':
                return False
        raise CLIError(response.content)

    def pull(self):
        repos = self.gh("orgs/%s/repos" % self.org)
        filtered = [r for r in repos if fnmatch.fnmatch(r["full_name"], self.filter)]
        urls = []
        for r in filtered:
            name = r["full_name"]
            result = self.gh("repos/%s" % name, expected=(404,))
            if "id" in result:
                urls.append((name, r["clone_url"]))

        for n, u in urls:
            self.git_pull(n, u)

    def bake(self):
        prototypes, services = self.scan()

        raw = [(svc, name, container) for svc, name, container in containers(services)
               if not (self.pushed(name, svc.version) or self.baked(name, svc.version))]

        for svc, name, container in raw:
            self.call("docker", "build", ".", "-t", image(self.registry, self.repo, name, svc.version),
                      cwd=os.path.join(svc.root, os.path.dirname(container)))

    def push(self):
        prototypes, services = self.scan()

        local = [(svc, name, container) for svc, name, container in containers(services)
                 if (self.baked(name, svc.version) and not self.pushed(name, svc.version))]

        if local: self.call("docker", "login", "-u", self.user, "-p", Secret(self.password), self.registry)
        for svc, name, container in local:
            self.call("docker", "push", image(self.registry, self.repo, name, svc.version))

    def deploy(self):
        prototypes, services = self.scan()

        owners = OrderedDict()
        conflicts = []
        kube_files = []

        for svc in services:
            filename, metadata = svc.metadata(self.registry, self.repo)
            with open(filename, "write") as f:
                yaml.dump(metadata, f)
            result = self.call("./deployment", "metadata.yaml", cwd=svc.root)
            kube_file = os.path.join(svc.root, "kube.yaml")
            with open(kube_file, "write") as f:
                f.write(result.output)
            resources = self.call("kubectl", "apply", "--dry-run", "-f", kube_file, "-o", "name").output.split()
            for resource in resources:
                if resource in owners:
                    conflicts.append((resource, owners[resource].name, svc.name))
                else:
                    owners[resource] = svc
            kube_files.append(kube_file)

        if conflicts:
            messages = ", ".join("%s defined by %s and %s" % c for c in conflicts)
            raise CLIError("conflicts: %s" % messages)
        else:
            for kube_file in kube_files:
                cmd = "kubectl", "apply", "-f", kube_file
                if self.dry_run:
                    cmd += "--dry-run",
                result = self.call(*cmd)
                if result.output:
                    print "  " + result.output.strip().replace("\n", "\n  ") + "\n",

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

def default(args):
    conf_file = get_config(args)
    if not conf_file: return

    with open(conf_file, "read") as fd:
        conf = yaml.load(fd)

    for name in ("token", "user", "password", "workdir"):
        arg = "--%s" % name
        if arg not in args or args[arg] is None and name in conf:
            args[arg] = conf[name]

    for name in ("organization", "docker-repo"):
        arg = "<%s>" % name
        if name not in args or args[arg] is None and name in conf:
            args[arg] = conf[name]

def get_workdir(args):
    workdir = args["--workdir"] or os.getcwd()
    if not workdir.startswith("/"):
        workdir = os.path.join(os.getcwd(), workdir)
    return workdir

def get_repo(args):
    url = args["<docker-repo>"]
    if url is None:
        return None, None
    registry, repo = url.split("/", 1)
    return registry, repo

def create(baker, args):
    proto = args["<prototype>"]
    arguments_file = args["<arguments>"]
    target = args["<target>"] or os.path.splitext(os.path.basename(arguments_file))[0]
    prototypes, services = baker.scan()
    selected = [p for p in prototypes if p.name == proto]
    assert len(selected) <= 1
    if not selected:
        raise CLIError("no such prototype: %s" % proto)
    prototype = selected[0]

    try:
        with open(arguments_file, "read") as fd:
            # XXX: the Loader=blah messes up the OrderedDict stuff
            arguments = yaml.load(fd, Loader=yaml.loader.BaseLoader)
    except IOError, e:
        raise CLIError(e)

    errors = prototype.validate(arguments)
    if errors:
        raise CLIError("\n".join(errors))

    prototype.instantiate(target, arguments)

def main(args):
    default(args)

    baker = Baker()

    baker.workdir = get_workdir(args)
    baker.org = args["<organization>"]
    baker.token = args["--token"]
    baker.filter = args["--filter"]
    baker.registry, baker.repo = get_repo(args)
    baker.user = args["--user"]
    baker.password = args["--password"]
    baker.dry_run = args["--dry-run"]

    if args["pull"]: return baker.pull()
    if args["bake"]: return baker.bake()
    if args["push"]: return baker.push()
    if args["deploy"]: return baker.deploy()
    if args["create"]: return create(baker, args)
    if args["serve"]:
        from .server import serve
        return serve(baker)
    assert False, "unrecognized args"

def call_main():
    util.setup_yaml()
    args = docopt(__doc__, version="Forge %s" % __version__)
    try:
        exit(main(args))
    except CLIError, e:
        exit(e)

if __name__ == "__main__":
    call_main()
