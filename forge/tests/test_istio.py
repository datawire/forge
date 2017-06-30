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

import os
from forge.istio import istio
from .common import mktree

YAML = {
    "kube.yaml": """---
apiVersion: v1
kind: Service
metadata:
  name: testistio
spec:
  selector:
    app: testistio
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: LoadBalancer
---
apiVersion: extensions/v1beta1
kind: Deployment
metadata: {name: testistio}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: testistio
  strategy:
    rollingUpdate: {maxSurge: 1, maxUnavailable: 0}
    type: RollingUpdate
  revisionHistoryLimit: 1
  template:
    metadata:
      labels:
        app: testistio
      name: testistio
    spec:
      containers:
      - image: CONTAINER
        imagePullPolicy: IfNotPresent
        name: testistio
        resources:
          limits:
            memory: 1G
            cpu: 1.0
        terminationMessagePath: /dev/termination-log
      dnsPolicy: ClusterFirst
      restartPolicy: Always
      securityContext: {}
      terminationGracePeriodSeconds: 30
"""
}

def test_isto():
    directory = mktree(YAML)
    istio(directory)
    print open(os.path.join(directory, "kube.yaml")).read()
