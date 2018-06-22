FILE forge.yaml
registry:
  type: docker
  url: registry.hub.docker.com
  namespace: forgeorg
END

RUN docker login registry.hub.docker.com -u forgetest -p forgetest

FILE service.yaml
name: sops
END

FILE svc.yaml
---
apiVersion: v1
kind: Service
metadata:
  name: {{build.name}}
spec:
  type: LoadBalancer
END

ENV ARN arn:aws:kms:us-east-1:020846367509:key/90d48ea4-ce83-46b7-9fec-a0d169b3f42f

RUN EDITOR="cp svc.yaml" forge edit -c k8s/svc-enc.yaml
MATCH
You must obtain the master key and export it in the 'SOPS_KMS_ARN' environment variable
END
ERR

RUN SOPS_KMS_ARN=${ARN} forge edit -c k8s/svc-enc.yaml
MATCH
[Errno 2] No such file or directory: 'k8s/svc-enc.yaml'
END
ERR

FILE k8s/DUMMY
END

FILE edit.sh
#!/bin/sh
echo EDITED >> $1
END
RUN chmod a+x edit.sh


RUN SOPS_KMS_ARN=${ARN} EDITOR="cp svc.yaml" forge edit -c k8s/svc-enc.yaml
RUN SOPS_KMS_ARN=${ARN} EDITOR="./edit.sh" forge edit k8s/svc-enc.yaml
RUN SOPS_KMS_ARN=${ARN} forge view k8s/svc-enc.yaml
MATCH
---
apiVersion: v1
kind: Service
metadata:
  name: {{.*}}
spec:
  type: LoadBalancer
EDITED
END

RUN SOPS_KMS_ARN=${ARN} EDITOR="cp svc.yaml" forge edit -c k8s/svc-enc.yaml

RUN forge build manifests
MATCH
║ 9 tasks run, 1 errors
║   sops: You must obtain the master key and export it in the 'SOPS_KMS_ARN' environment variable
END
ERR

ENV SOPS_KMS_ARN ${ARN}

RUN forge build manifests
MATCH
║ 15 tasks run, 0 errors
║ 
║ rendered: service/sops-default
END

RUN cat .forge/k8s/sops/svc-enc.yaml
MATCH
apiVersion: v1
kind: Service
metadata:
  name: sops-default
  labels: {forge.service: sops, forge.profile: default}
  annotations: {forge.repo: '', forge.descriptor: service.yaml, forge.version: VERSION_1}
spec:
  type: LoadBalancer
END
