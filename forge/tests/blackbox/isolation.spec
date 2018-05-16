FILE forge.yaml
registry:
  type: docker
  url: registry.hub.docker.com
  namespace: forgeorg
END

RUN docker login registry.hub.docker.com -u forgetest -p forgetest

FILE bad/service.yaml
name: bad
{
END

FILE bad/k8s/DUMMY
END

FILE good/service.yaml
name: good
END

FILE good/k8s/DUMMY
END

CWD good
RUN forge --no-scan-base build manifests
