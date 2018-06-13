RUN forge -v deploy
RUN kubectl get svc,deploy --all-namespaces -oname -lforge.service=delete,forge.profile=default
OUT service/delete-default
OUT service/delete-default-namespaced
OUT deployment.extensions/delete-default
OUT deployment.extensions/delete-default-namespaced

RUN forge -v --profile foo deploy
RUN kubectl get svc,deploy --all-namespaces -oname -lforge.service=delete,forge.profile=foo
OUT service/delete-foo
OUT service/delete-foo-namespaced
OUT deployment.extensions/delete-foo
OUT deployment.extensions/delete-foo-namespaced

RUN forge delete delete foo
OUT deployment.extensions "delete-foo" deleted
OUT endpoints "delete-foo" deleted
OUT service "delete-foo" deleted

RUN kubectl get svc,deploy --all-namespaces -oname -lforge.service=delete,forge.profile=default
OUT service/delete-default
OUT deployment.extensions/delete-default

RUN forge -v --profile foo deploy
RUN kubectl get svc,deploy --all-namespaces -oname -lforge.service=delete,forge.profile=foo
OUT service/delete-foo
OUT deployment.extensions/delete-foo

RUN forge delete delete
RUN kubectl get svc,deploy --all-namespaces -lforge.service=delete
OUT No resources found.

RUN forge -v deploy
RUN kubectl get svc,deploy --all-namespaces -oname -lforge.service=delete,forge.profile=default
OUT service/delete-default
OUT service/delete-default-namespaced
OUT deployment.extensions/delete-default
OUT deployment.extensions/delete-default-namespaced

TIMEOUT 60

RUN forge delete --all
RUN kubectl get svc,deploy --all-namespaces -lforge.service=delete
OUT No resources found.
