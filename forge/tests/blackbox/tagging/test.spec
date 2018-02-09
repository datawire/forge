RUN git init
RUN git add .
RUN git commit -m "initial commit"
RUN git remote add origin https://github.com/datawire/forge.git

RUN forge -v deploy
RUN kubectl get svc,deploy -l forge.service=tagging -l forge.profile=default -o name
OUT services/tagging-default
OUT deployments/tagging-default
RUN kubectl get svc/tagging-default -o 'go-template={{range $k, $v := .metadata.annotations}}{{$k}}: {{$v}}{{"\n"}}{{end}}'
OUT forge.descriptor: service.yaml
OUT forge.repo: https://github.com/datawire/forge.git
OUT forge.version:

RUN kubectl get ns -lforge.service
OUT No resources found.

RUN forge --profile foo -v deploy

RUN kubectl get svc,deploy -l forge.service=tagging -l forge.profile=default -o name
OUT services/tagging-default
OUT deployments/tagging-default

RUN kubectl get svc,deploy -l forge.service=tagging -l forge.profile=foo -o name
OUT services/tagging-foo
OUT deployments/tagging-foo

RUN kubectl get svc,deploy -l forge.service=tagging -o name
OUT services/tagging-default
OUT services/tagging-foo
OUT deployments/tagging-default
OUT deployments/tagging-foo

RUN kubectl get ns -lforge.service
OUT No resources found.
