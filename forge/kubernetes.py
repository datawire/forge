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

import os, glob
from tasks import task, TaskError, get, sh, SHResult
from forge.match import match
from forge.yamlutil import MappingNode, Node, as_node, compose, compose_all, serialize_all, view
from forge import yamlutil

@match(MappingNode, basestring, dict)
def fixup(node, key, pairs):
    node = view(node)
    if node.get("kind"):
        md = node.get("metadata")
        if md is None:
            md = view(compose("{}"))
            node["metadata"] = md

        orig = md.get(key)
        if orig is None:
            orig = view(compose("{}"))
            md[key] = orig
        for k, v in pairs.items():
            orig[k] = as_node(v)

@match(Node, basestring, dict)
def fixup(*args):
    pass

ALL = ('csr',
       'clusterrolebindings',
       'clusterroles',
       'cm',
       'controllerrevisions',
       'crd',
       'ds',
       'deploy',
       'ep',
       'ev',
       'hpa',
       'ing',
       'jobs',
       'limits',
       'ns',
       'netpol',
       'no',
       'pvc',
       'pv',
       'pdb',
       'po',
       'psp',
       'podtemplates',
       'rs',
       'rc',
       'quota',
       'rolebindings',
       'roles',
       'secrets',
       'sa',
       'svc',
       'sts',
       'sc')

@match("deployment", object)
def status_summary(kind, status):
    conds = status.get("conditions")
    if conds:
        return conds[0]["message"]
    else:
        return "(none)"

@match("service", object)
def status_summary(kind, status):
    if status is None:
        return "(none)"
    ready = []
    not_ready = []
    for subset in status:
        for key, lst in ("addresses", ready), ("notReadyAddresses", not_ready):
            for address in subset.get(key, ()):
                for port in subset["ports"]:
                    lst.append("%s:%s" % (address["ip"], port["port"]))
    result = []
    if ready:
        result.append("READY(%s)" % ", ".join(ready))
    if not_ready:
        result.append("NOT READY(%s)" % ", ".join(not_ready))
    return ", ".join(result)

@match(basestring, object)
def status_summary(kind, status):
    return str(status)

def is_yaml_empty(dir):
    for name in glob.glob("%s/*.yaml" % dir):
        with open(name) as f:
            if f.read().strip():
                return False
    return True

def selector(labels):
    return "-l%s" % (",".join("%s=%s" % (k, v) for k, v in labels.items()))

class Kubernetes(object):

    def __init__(self, namespace=None, context=None, dry_run=False):
        self.namespace = namespace or os.environ.get("K8S_NAMESPACE", None)
        self.context = context
        self.dry_run = dry_run

    @task()
    def resources(self, yaml_dir):
        if is_yaml_empty(yaml_dir):
            return []
        cmd = "kubectl", "apply", "--dry-run", "-f", yaml_dir, "-o", "name"
        if self.namespace:
            cmd += "--namespace", self.namespace
        return sh(*cmd).output.split()

    def _labeltate(self, yaml_dir, labels, annotate):
        if is_yaml_empty(yaml_dir):
            return SHResult("", 0, "")
        key = "annotations" if annotate else "labels"

        for name in os.listdir(yaml_dir):
            fixed = []
            with open(os.path.join(yaml_dir, name), 'read') as f:
                for nd in compose_all(f):
                    fixup(nd, key, labels)
                    # we filter out null nodes because istioctl sticks
                    # them in for some reason, and then we end up
                    # serializing them in a way that kubectl doesn't
                    # understand
                    if nd.tag == u'tag:yaml.org,2002:null':
                        continue
                    fixed.append(nd)
            munged = serialize_all(fixed)
            with open(os.path.join(yaml_dir, name), 'write') as f:
                f.write(munged)

    @task()
    def annotate(self, yaml_dir, labels):
        self._labeltate(yaml_dir, labels, annotate=True)

    @task()
    def label(self, yaml_dir, labels):
        self._labeltate(yaml_dir, labels, annotate=False)

    @task()
    def apply(self, yaml_dir, prune=None):
        if is_yaml_empty(yaml_dir):
            return SHResult("", 0, "")
        cmd = "kubectl", "apply", "-f", yaml_dir
        if self.namespace:
            cmd += "--namespace", self.namespace
        if self.dry_run:
            cmd += "--dry-run",
        if prune:
            cmd += "--prune", selector(prune)
        result = sh(*cmd)
        return result

    @task()
    def list(self):
        """
        Return a structured view of all forge deployed resources in a kubernetes cluster.
        """
        output = sh("kubectl", "get", "--all-namespaces", ",".join(ALL), "-oyaml", "-lforge.service").output

        repos = {}
        endpoints = {}
        for nd in yamlutil.load("kubectl-get", output):
            items = nd["items"]
            for i in items:
                kind = i["kind"].lower()
                md = i["metadata"]
                name = md["name"]
                namespace = md["namespace"]
                status = i.get("status", {})

                ann = md.get("annotations", {})

                repo = ann.get("forge.repo", "(none)")
                descriptor = ann.get("forge.descriptor", "(none)")
                version = ann.get("forge.version", "(none)")

                labels = md.get("labels", {})
                service = labels["forge.service"]
                profile = labels["forge.profile"]

                if kind == "endpoints":
                    endpoints[(namespace, name)] = i["subsets"]
                    continue

                if repo not in repos:
                    repos[repo] = {}

                if service not in repos[repo]:
                    repos[repo][service] = {}

                if profile not in repos[repo][service]:
                    repos[repo][service][profile] = []

                repos[repo][service][profile].append({
                    "kind": kind,
                    "namespace": namespace,
                    "name": name,
                    "version": version,
                    "descriptor": descriptor,
                    "status": status
                })

        for repo, services in repos.items():
            for service, profiles in services.items():
                for profile, resources in profiles.items():
                    for resource in resources:
                        kind = resource["kind"]
                        if kind == "service":
                            status = status_summary(kind, endpoints[(resource["namespace"], resource["name"])])
                        else:
                            status = status_summary(kind, resource["status"])
                        resource["status"] = status

        return repos

    @task()
    def delete(self, labels):
        lines = sh("kubectl", "get", "ns", "-oname").output.splitlines()
        namespaces = (l.strip().split("/")[-1] for l in lines)
        for ns in namespaces:
            sh("kubectl", "delete", "-n", ns, ",".join(ALL), selector(labels))
