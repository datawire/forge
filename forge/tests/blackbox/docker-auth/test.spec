RUN rm forge.yaml

FILE service.yaml
name: docker-auth
END

FILE Dockerfile
FROM alpine:3.6
END

FILE forge.yaml
registry:
  type: docker
  url: registry.hub.docker.com
  namespace: forgeorg
END

FILE k8s/DUMMY
END

RUN docker logout registry.hub.docker.com/forgeorg
RUN forge build
MATCH
unable to locate docker credentials, please run `docker login registry.hub.docker.com`
END
ERR

RUN docker login registry.hub.docker.com/forgeorg -u forgetest -p forgetest

RUN forge build
