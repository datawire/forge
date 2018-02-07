RUN forge -v deploy
RUN kubectl get svc,deploy -oname -lforge.service=delete
OUT services/delete-default
OUT deployments/delete-default
RUN forge delete
OUT deployment "delete-default" deleted
OUT endpoints "delete-default" deleted
OUT service "delete-default" deleted
