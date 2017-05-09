# Copyright 2015 datawire. All rights reserved.
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
Skunkworks CLI.

Usage:
  sw pull [--token=<token>] [--workdir=<path>]  [--filter=<pattern>] <organization>
  sw bake [--user=<user>] [--password=<password>] <docker-repo>
  sw push [--user=<user>] [--password=<password>] <docker-repo>
  sw deploy [--dry-run] <docker-repo>
  sw serve --token=<token> --user=<user> --password=<password> <docker-repo>
  sw -h | --help
  sw --version

Options:
  --filter=<pattern>    Only operate on services matching <pattern>. [default: *]
  --token=<token>       Github authentication token.
  --workdir=<path>      Work directory.
  -h --help             Show this screen.
  --version             Show version.
"""

import util

from docopt import docopt
from ._metadata import __version__

import fnmatch, requests, os, yaml
from collections import OrderedDict
from workstream import Workstream, Elidable, Secret

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

def image(registry, repo, name, version):
    return "%s/%s/%s:%s" % (registry, repo, name, version)

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

    def __repr__(self):
        return "Service(%r, %r, %r)" % (self.version, self.descriptor, self.containers)

class Prototype(object):

    def __init__(self, descriptor):
        self.descriptor = descriptor

    def __repr__(self):
        return "Prototype(%r)" % self.descriptor

class Baker(Workstream):

    def gh(self, api, token=None, expected=None):
        headers = {'Authorization': 'token %s' % token} if token else None
        response = self.get("https://api.github.com/%s" % api, headers=headers, expected=expected)
        result = response.json()
        next_url = next_page(response)
        while next_url:
            response = self.get(next_url, headers=headers)
            result.extend(response.json())
            next_url = next_page(response)
        return result

    def git_pull(self, workdir, name, url, token=None):
        repodir = os.path.join(workdir, name)
        if not os.path.exists(repodir):
            os.makedirs(repodir)
            self.call("git", "init", cwd=repodir)
        self.call("git", "pull", "-f", inject_token(url, token), cwd=repodir)

    EXCLUDED = set([".git"])

    def scan(self, root):
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

        descend(root, None)
        return prototypes, services
    
    def baked(self, registry, repo, name, version):
        result = self.call("docker", "images", "-q", image(registry, repo, name, version))
        return result.output

    def pushed(self, registry, repo, name, version, user, password):
        url = "https://%s/v2/%s/%s/manifests/%s" % (registry, repo, name, version)
        response = self.get(url, auth=(user, password), expected=(404,))
        result = response.json()
        if 'signatures' in result and 'fsLayers' in result:
            return True
        elif 'errors' in result and result['errors']:
            if result['errors'][0]['code'] == 'MANIFEST_UNKNOWN':
                return False
        raise Exception(response.content)

def get_workdir(args):
    workdir = args["--workdir"] or os.getcwd()
    if not workdir.startswith("/"):
        workdir = os.path.join(os.getcwd(), workdir)
    return workdir

def pull(args):
    baker = Baker()

    org = args["<organization>"]
    token = args["--token"]
    pattern = args["--filter"]
    workdir = get_workdir(args)

    repos = baker.gh("orgs/%s/repos" % org, token=token)
    filtered = [r for r in repos if fnmatch.fnmatch(r["full_name"], pattern)]
    urls = []
    for r in filtered:
        name = r["full_name"]
        result = baker.gh("repos/%s" % name, token=token, expected=(404,))
        if "id" in result:
            urls.append((name, r["clone_url"]))

    for n, u in urls:
        baker.git_pull(workdir, n, u, token)

def get_repo(args):
    url = args["<docker-repo>"]
    registry, repo = url.split("/", 1)
    return registry, repo

def containers(services):
    for svc in services:
        for container in svc.containers:
            yield svc, svc.image(container), container

def bake(args):
    baker = Baker()

    registry, repo = get_repo(args)
    user = args["--user"]
    password = args["--password"]

    prototypes, services = baker.scan(get_workdir(args))

    raw = [(svc, name, container) for svc, name, container in containers(services)
           if not (baker.pushed(registry, repo, name, svc.version, user, password) or
                   baker.baked(registry, repo, name, svc.version))]

    for svc, name, container in raw:
        baker.call("docker", "build", ".", "-t", image(registry, repo, name, svc.version),
                   cwd=os.path.join(svc.root, os.path.dirname(container)))

def push(args):
    baker = Baker()

    registry, repo = get_repo(args)
    user = args["--user"]
    password = args["--password"]

    prototypes, services = baker.scan(get_workdir(args))

    local = [(svc, name, container) for svc, name, container in containers(services)
             if (baker.baked(registry, repo, name, svc.version) and not
                 baker.pushed(registry, repo, name, svc.version, user, password))]

    baker.call("docker", "login", "-u", user, "-p", Secret(password), registry)
    for svc, name, container in local:
        baker.call("docker", "push", image(registry, repo, name, svc.version))

def deploy(args):
    baker = Baker()

    registry, repo = get_repo(args)
    prototypes, services = baker.scan(get_workdir(args))

    owners = OrderedDict()
    conflicts = []
    kube_files = []

    for svc in services:
        filename, metadata = svc.metadata(registry, repo)
        with open(filename, "write") as f:
            yaml.dump(metadata, f)
        result = baker.call("./deployment", "metadata.yaml", cwd=svc.root)
        kube_file = os.path.join(svc.root, "kube.yaml")
        with open(kube_file, "write") as f:
            f.write(result.output)
        resources = baker.call("kubectl", "apply", "--dry-run", "-f", kube_file, "-o", "name").output.split()
        for resource in resources:
            if resource in owners:
                conflicts.append((resource, owners[resource].name, svc.name))
            else:
                owners[resource] = svc
        kube_files.append(kube_file)

    if conflicts:
        messages = ", ".join("%s defined by %s and %s" % c for c in conflicts)
        raise Exception("conflicts: %s" % messages)
    else:
        for kube_file in kube_files:
            cmd = "kubectl", "apply", "-f", kube_file, 
            if args["--dry-run"]:
                cmd += "--dry-run",
            result = baker.call(*cmd)
            if result.output:
                print "  " + result.output.strip().replace("\n", "\n  ") + "\n",

def serve(args):
    print "not implemented yet"

def main(args):
    if args["pull"]: return pull(args)
    if args["bake"]: return bake(args)
    if args["push"]: return push(args)
    if args["deploy"]: return deploy(args)
    if args["serve"]: return serve(args)
    assert False, "unrecognized args"

def call_main():
    util.setup_yaml()
    args = docopt(__doc__, version="Skunkworks %s" % __version__)
    exit(main(args))

if __name__ == "__main__":
    call_main()
