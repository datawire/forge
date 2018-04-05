FILE forge.yaml
registry:
  type: local
END

FILE subdir/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: kubernetes
spec:
  type: ClusterIP
END

FILE service.yaml
name: myservice
END

FILE k8s/DUMMY
END

RUN forge build
