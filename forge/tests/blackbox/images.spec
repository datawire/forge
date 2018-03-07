FILE forge.yaml
registry:
  type: docker
  url: registry.hub.docker.com
  namespace: forgeorg
END

RUN docker login registry.hub.docker.com -u forgetest -p forgetest

FILE k8s/DUMMY
END

FILE service.yaml
name: images

containers:
- name: foo
  dockerfile: foo.dockerfile
- name: bar
  dockerfile: bar.dockerfile
END

RUN forge build metadata
OUT images:
OUT foo.dockerfile:
OUT foo:
OUT bar.dockerfile:
OUT bar:
