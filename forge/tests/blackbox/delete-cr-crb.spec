FILE service.yaml
name: delete-cr-crb
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
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{service.name}}-account
---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRole
metadata:
  name: {{service.name}}-role
rules:
- apiGroups: [""]
  resources:
  - services
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources:
  - configmaps
  verbs: ["create", "update", "patch", "get", "list", "watch"]
- apiGroups: [""]
  resources:
  - secrets
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1beta1
kind: ClusterRoleBinding
metadata:
  name: {{service.name}}-role-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: {{service.name}}-role
subjects:
- kind: ServiceAccount
  name: {{service.name}}-account
  namespace: default
END

RUN forge deploy
RUN forge delete delete-cr-crb
RUN kubectl get --ignore-not-found serviceaccount delete-cr-crb-account
MATCH
END
RUN kubectl get --ignore-not-found clusterrole delete-cr-crb-role
MATCH
END
RUN kubectl get --ignore-not-found clusterrolebinding delete-cr-crb-binding
MATCH
END
