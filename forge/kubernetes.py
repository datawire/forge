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

def is_yaml_empty(dir):
    for name in glob.glob("%s/*.yaml" % dir):
        with open(name) as f:
            if f.read().strip():
                return False
    return True

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

    @task()
    def apply(self, yaml_dir):
        if is_yaml_empty(yaml_dir):
            return SHResult("", 0, "")
        cmd = "kubectl", "apply", "-f", yaml_dir
        if self.namespace:
            cmd += "--namespace", self.namespace
        if self.dry_run:
            cmd += "--dry-run",
        result = sh(*cmd)
        return result
