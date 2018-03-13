FILE service.yaml
name: no-delete-storage
END

FILE forge.yaml
registry:
  type: docker
  url: registry.hub.docker.com
  namespace: forgeorg
END

RUN docker login registry.hub.docker.com/forgeorg -u forgetest -p forgetest

FILE k8s/manifest.yaml
---
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: no-delete-storage
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
END

RUN kubectl delete --ignore-not-found storageclass no-delete-storage
RUN forge deploy
RUN kubectl get storageclass no-delete-storage
RUN forge delete no-delete-storage
RUN kubectl get storageclass no-delete-storage
