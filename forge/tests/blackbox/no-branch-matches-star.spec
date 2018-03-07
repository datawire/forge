FILE forge.yaml
registry:
  type: docker
  url: registry.hub.docker.com
  namespace: forgeorg
END

RUN docker login registry.hub.docker.com -u forgetest -p forgetest

FILE k8s/out.yaml
---
apiVersion: v1
kind: Service
metadata:
  name: {{build.profile.name}}
END

FILE service.yaml
name: no-branch-matches-star

branches:
  master: prod
  '*': dev
END

RUN forge build manifests
RUN cat .forge/k8s/no-branch-matches-star/out.yaml
MATCH
apiVersion: v1
kind: Service
metadata:
  name: dev
  labels: {forge.service: no-branch-matches-star, forge.profile: dev}
  annotations: {forge.repo: '', forge.descriptor: service.yaml, forge.version: VERSION_1}
END

RUN forge --branch master build manifests
RUN cat .forge/k8s/no-branch-matches-star/out.yaml
MATCH
apiVersion: v1
kind: Service
metadata:
  name: prod
  labels: {forge.service: no-branch-matches-star, forge.profile: prod}
  annotations: {forge.repo: '', forge.descriptor: service.yaml, forge.version: VERSION_1}
END
