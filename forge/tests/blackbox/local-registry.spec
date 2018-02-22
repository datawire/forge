FILE service.yaml
name: local-registry-TEST_ID
END

FILE k8s/DUMMY
END

FILE Dockerfile
FROM alpine:3.6
END

FILE forge.yaml
registry:
  type: docker
  url: registry.hub.docker.com
  namespace: forgeorg

profiles:
  foo:
    registry:
      type: local
END

RUN forge deploy
MATCH
║ docker build TEST_BASE/ -f TEST_BASE/Dockerfile -t registry.hub.docker.com/forgeorg/local-registry-TEST_ID:VERSION_1
║ Sending build context to Docker daemon {{NUMBER}} kB
║ Step 1/1 : FROM alpine:3.6
║  ---> {{HEX}}
║ Successfully built {{HEX}}
║ Successfully tagged registry.hub.docker.com/forgeorg/local-registry-TEST_ID:VERSION_1
║ docker push registry.hub.docker.com/forgeorg/local-registry-TEST_ID:VERSION_1
║ {{.*}}
║ VERSION_1: digest: sha256:{{HEX}} size: {{NUMBER}}
║ {{NUMBER}} tasks run, 0 errors
║ 
║    built: Dockerfile
║   pushed: local-registry-TEST_ID:VERSION_1
║ rendered: (none)
║ deployed: local-registry-TEST_ID
END

RUN forge --profile foo deploy
MATCH
║ docker build TEST_BASE/ -f TEST_BASE/Dockerfile -t local-registry-TEST_ID:VERSION_1
║ Sending build context to Docker daemon {{NUMBER}} kB
║ Step 1/1 : FROM alpine:3.6
║  ---> {{HEX}}
║ Successfully built {{HEX}}
║ Successfully tagged local-registry-TEST_ID:VERSION_1
║ {{NUMBER}} tasks run, 0 errors
║ 
║    built: Dockerfile
║ rendered: (none)
║ deployed: local-registry-TEST_ID
END
