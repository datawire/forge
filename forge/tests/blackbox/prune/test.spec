RUN forge -v deploy
RUN sed -i s/-foo/-bar/ k8s/deployment.yaml
RUN forge -v deploy --prune
OUT service "prune-default-foo" pruned
OUT deployment.extensions "prune-default-foo" pruned
