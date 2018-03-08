RUN forge -v deploy
RUN kubectl get svc,deploy --all-namespaces -oname -lforge.service=delete,forge.profile=default
OUT services/delete-default
OUT services/delete-default-namespaced
OUT deployments/delete-default
OUT deployments/delete-default-namespaced

RUN forge -v --profile foo deploy
RUN kubectl get svc,deploy --all-namespaces -oname -lforge.service=delete,forge.profile=foo
OUT services/delete-foo
OUT services/delete-foo-namespaced
OUT deployments/delete-foo
OUT deployments/delete-foo-namespaced

RUN forge delete delete foo
OUT deployment "delete-foo" deleted
OUT endpoints "delete-foo" deleted
OUT service "delete-foo" deleted

RUN kubectl get svc,deploy --all-namespaces -oname -lforge.service=delete,forge.profile=default
OUT services/delete-default
OUT deployments/delete-default

RUN forge -v --profile foo deploy
RUN kubectl get svc,deploy --all-namespaces -oname -lforge.service=delete,forge.profile=foo
OUT services/delete-foo
OUT deployments/delete-foo

RUN forge delete delete
RUN kubectl get svc,deploy --all-namespaces -lforge.service=delete
OUT No resources found.

RUN forge -v deploy
RUN kubectl get svc,deploy --all-namespaces -oname -lforge.service=delete,forge.profile=default
OUT services/delete-default
OUT services/delete-default-namespaced
OUT deployments/delete-default
OUT deployments/delete-default-namespaced

TIMEOUT 60

RUN forge delete --all
RUN kubectl get svc,deploy --all-namespaces -lforge.service=delete
OUT No resources found.
