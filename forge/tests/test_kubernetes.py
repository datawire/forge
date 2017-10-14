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

import os, time
from forge.tasks import TaskError, sh
from forge.kubernetes import Kubernetes
from .common import mktree

START_TIME = time.time()
MANGLE = str(START_TIME).replace('.', '-')

def mangle(st):
    return st.replace("MANGLE", MANGLE)

K8S_TREE = """
@@k8s/deployment.yaml
---
apiVersion: v1
kind: Service
metadata:
  name: kube-test-service-MANGLE
spec:
  selector:
    app: kube-test-deployment-MANGLE
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: LoadBalancer
---
apiVersion: extensions/v1beta1
kind: Deployment
metadata: {name: kube-test-deployment-MANGLE}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kube-test-deployment-MANGLE
  strategy:
    rollingUpdate: {maxSurge: 1, maxUnavailable: 0}
    type: RollingUpdate
  revisionHistoryLimit: 1
  template:
    metadata:
      labels:
        app: kube-test-deployment-MANGLE
      name: kube-test-deployment-MANGLE
    spec:
      containers:
      - name: alpine
        image: alpine:3.5
@@
"""

def test_resources():
    directory = mktree(K8S_TREE, MANGLE=MANGLE)
    kube = Kubernetes()
    resources = kube.resources(os.path.join(directory, "k8s"))
    assert mangle('service/kube-test-service-MANGLE') in resources
    assert mangle('deployment/kube-test-deployment-MANGLE') in resources

def kget(namespace, type, name):
    cmd = "kubectl", "get", "-o", "name", type, name
    if namespace:
        cmd += "--namespace", namespace
    return sh(*cmd)

def kcheck(namespace, type, name):
    assert mangle("%s/%s" % (type, name)) == kget(namespace, type, mangle(name)).output.strip()

def test_apply(namespace=None):
    directory = mktree(K8S_TREE, MANGLE=MANGLE)
    kube = Kubernetes(namespace=namespace)
    kube.apply(os.path.join(directory, "k8s"))
    kcheck(namespace, "services", "kube-test-service-MANGLE")
    kcheck(namespace, "deployments", "kube-test-deployment-MANGLE")

def test_apply_namespace():
    sh("kubectl", "create", "namespace", mangle("dev-MANGLE"))
    test_apply(namespace=mangle("dev-MANGLE"))

K8S_BAD_TREE = """
@@k8s/deployment.yaml
---
apiVersion: v1
kind: xxx
metadata:
  name: bad
@@
"""

def test_apply_bad():
    directory = mktree(K8S_BAD_TREE)
    kube = Kubernetes()
    try:
        kube.apply(os.path.join(directory, "k8s"))
    except TaskError, e:
        assert "error" in str(e)
        assert "xxx" in str(e)
