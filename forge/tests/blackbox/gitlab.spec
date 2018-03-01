FILE forge.yaml
# Global forge configuration
registry:
  type: docker
  url: registry.gitlab.com
  namespace: forgetest/forgetest
END

FILE Dockerfile
FROM nginx:1.7.9
RUN echo TEST-ID
END

FILE k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{build.name}}
spec:
  replicas: 3
  selector:
    matchLabels:
      deployment: {{build.name}}
  template:
    metadata:
      labels:
        deployment: {{build.name}}
    spec:
      containers:
      - name: nginx
        image: {{build.images["Dockerfile"]}}
        ports:
        - containerPort: 80
END

FILE service.yaml
name: gitlab
END

RUN docker logout registry.gitlab.com
RUN forge deploy
MATCH
unable to locate docker credentials, please run `docker login registry.gitlab.com`
END
ERR

TIMEOUT 60

RUN docker login registry.gitlab.com -u forgetest -p forgetest
RUN forge -v deploy

RUN docker login registry.gitlab.com -u gitlab-ci-token -p kBjszMXMdvqW-L_sZzTk
RUN forge -v deploy
