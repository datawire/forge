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
        result = sh(*cmd, expected=xrange(256))
        return result
