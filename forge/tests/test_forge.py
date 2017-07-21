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

import os, pexpect, sys, time
from .common import mktree

START_TIME = time.time()
MANGLE = str(START_TIME).replace('.', '-')

APP = {
    ################################################################################
    "forgetest/Dockerfile": r"""# Run server
FROM alpine:3.5
RUN apk add --no-cache python py2-pip py2-gevent
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /app
WORKDIR /app
EXPOSE 8080
ENTRYPOINT ["python"]
CMD ["app.py"]
""",

    ################################################################################
    "forgetest/service.yaml": r"""name: forgetest-MANGLE  # name of the service

# The service 'track' can be used to easily implement the pattern described here:
#
#   https://kubernetes.io/docs/concepts/cluster-administration/manage-deployment/#canary-deployments
#
# The default track is named 'stable'. Each track is concurrently
# deployed in order ot enable multiple long lived canaries:
#
# track: my-canary

targetPort: 8080   # port the container exposes

memory: 0.25G      # minimum available memory necessary to schedule the service
cpu: 0.25          # minimum available cpu necessary to schedule the service
""".replace("MANGLE", MANGLE),

    ################################################################################
    "forgetest/requirements.txt": r"""flask
""",

    ################################################################################
    "forgetest/k8s/deployment.yaml": r"""
{#

This template encodes the canary deployment practices described here:

  https://kubernetes.io/docs/concepts/cluster-administration/manage-deployment/#canary-deployments

Each 'track' is a parallel deployment of the application. Each track
has it's own service named {{service.name}}-{{service.track}} that
routes directly to the specific track deployment, and {{service.name}}
is set up to route to all deployments regardless of track.

#}

{% set track = service.track or 'stable' %}
{% set canary = track != 'stable' %}
{% set name = '%s-%s' % (service.name, service.track) if canary else service.name %}

---
apiVersion: v1
kind: Service
metadata:
  name: {{name}}
spec:
  selector:
    app: {{service.name}}
{% if canary %}
    track: {{track}}
{% endif %}
  ports:
    - protocol: {{service.protocol or 'TCP'}}
      port: {{service.port or '80'}}
      targetPort: {{service.targetPort or '8080'}}
  type: LoadBalancer

---
# FORGE_PROFILE is {{env.FORGE_PROFILE}}
apiVersion: extensions/v1beta1
kind: Deployment
metadata: {name: {{name}}}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {{service.name}}
      track: {{track}}
  strategy:
    rollingUpdate: {maxSurge: 1, maxUnavailable: 0}
    type: RollingUpdate
  revisionHistoryLimit: 1
  template:
    metadata:
      labels:
        app: {{service.name}}
        track: {{track}}
      name: {{name}}
    spec:
      containers:
      - image: {{build.images["Dockerfile"]}}
        imagePullPolicy: IfNotPresent
        name: {{name}}
        resources:
          limits:
            memory: {{service.memory}}
            cpu: {{service.cpu}}
        terminationMessagePath: /dev/termination-log
      dnsPolicy: ClusterFirst
      restartPolicy: Always
      securityContext: {}
      terminationGracePeriodSeconds: 30
""",

    ################################################################################
    "forgetest/app.py": r"""#!/usr/bin/python

import time
from flask import Flask
app = Flask(__name__)

START = time.time()

def elapsed():
    running = time.time() - START
    minutes, seconds = divmod(running, 60)
    hours, minutes = divmod(minutes, 60)
    return "%d:%02d:%02d" % (hours, minutes, seconds)

@app.route('/')
def root():
    return "forgetest-MANGLE (up %s)\n" % elapsed()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
""".replace("MANGLE", MANGLE),
    ################################################################################
    "forgetest/subdir/EMPTY": ""
}

user = 'forgetest'
password = 'forgetest'
org = 'forgeorg'

def launch(directory, cmd):
    return pexpect.spawn(cmd, cwd=directory, logfile=sys.stdout, timeout=60)

def setup():
    directory = mktree(APP)
    forge = launch(directory, "forge setup")
    forge.expect_exact('Docker registry[registry.hub.docker.com]: ')
    forge.sendline('')
    forge.expect_exact('Docker user[%s]: ' % os.environ["USER"])
    forge.sendline(user)
    forge.expect_exact('Docker organization[%s]: ' % user)
    forge.sendline(org)
    forge.expect_exact('Docker password: ')
    forge.sendline('forgetest')
    forge.expect_exact("== Writing config to forge.yaml ==")
    forge.expect_exact("== Done ==")
    forge.expect(pexpect.EOF)
    forge.wait()
    return directory

def test_e2e():
    directory = setup()
    os.environ["FORGE_PROFILE"] = "dev"
    forge = launch(directory, "forge deploy")
    forge.expect('service "forgetest-.*" created')
    forge.expect('deployment "forgetest-.*" created')
    forge.wait()

    for sub in ("forgetest", "forgetest/subdir"):
        forge = launch(os.path.join(directory, "forgetest/subdir"), "forge deploy")
        forge.expect('service "forgetest-.*" configured')
        forge.expect('deployment "forgetest-.*" configured')
        forge.wait()
