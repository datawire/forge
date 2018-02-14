FILE service.yaml
name: profile-test

profiles:
  stable:
    myval: stable-value
  canary:
    myval: canary-value
  default:
    myval: default-value
END

FILE k8s/profile.yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: dummy
data:
  {%- for k, v in build.profile.items() %}
  {{k}}: {{v}}
  {%- endfor %}
END

RUN forge --profile default build manifests
RUN cat .forge/k8s/profile-test/profile.yaml
MATCH 
apiVersion: v1
kind: ConfigMap
metadata:
  name: dummy
  labels: {forge.service: profile-test, forge.profile: default}
  annotations: {forge.repo: '', forge.descriptor: service.yaml, forge.version: VERSION_1}
data:
  myval: default-value
  name: default
END

RUN forge --profile stable build manifests
RUN cat .forge/k8s/profile-test/profile.yaml
MATCH
apiVersion: v1
kind: ConfigMap
metadata:
  name: dummy
  labels: {forge.service: profile-test, forge.profile: stable}
  annotations: {forge.repo: '', forge.descriptor: service.yaml, forge.version: VERSION_1}
data:
  myval: stable-value
  name: stable
END

RUN forge --profile canary build manifests
RUN cat .forge/k8s/profile-test/profile.yaml
MATCH
apiVersion: v1
kind: ConfigMap
metadata:
  name: dummy
  labels: {forge.service: profile-test, forge.profile: canary}
  annotations: {forge.repo: '', forge.descriptor: service.yaml, forge.version: VERSION_1}
data:
  myval: canary-value
  name: canary
END
