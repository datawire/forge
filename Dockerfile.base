FROM ubuntu:xenial

# base
RUN apt-get update && apt-get -y install curl
# go
RUN curl -L https://dl.google.com/go/go1.9.3.linux-amd64.tar.gz -o /tmp/go.tgz && tar -C /usr/local --strip-components=1 -xzf /tmp/go.tgz && rm /tmp/go.tgz
# forge deps
RUN apt-get update && apt-get -y install python python-pip # gcc python-dev musl-dev
# test deps
RUN apt-get update && apt-get -y install python3 docker.io git
# doc deps
RUN apt-get update && apt-get -y install nodejs npm perl
RUN ln -s /usr/bin/nodejs /usr/bin/node

# kubectl
RUN curl -L https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl
RUN chmod +x /usr/local/bin/kubectl

# gcloud
RUN curl https://sdk.cloud.google.com | bash -s -- --disable-prompts && echo 'source /root/google-cloud-sdk/path.bash.inc' >> /root/.profile

# istio
ENV ISTIO_VERSION 0.4.0
ENV ISTIO "istio-${ISTIO_VERSION}"
RUN curl -L https://github.com/istio/istio/releases/download/${ISTIO_VERSION}/${ISTIO}-linux.tar.gz -o /tmp/istio.tar.gz && \
    tar -C /tmp -xzf /tmp/istio.tar.gz && \
    mv /tmp/${ISTIO}/bin/istioctl /usr/local/bin && \
    chmod +x /usr/local/bin/istioctl && \
    rm -rf /tmp/istio.tar.gz /tmp/${ISTIO}

# imagebuilder
RUN GOPATH=/tmp/gp go get -u github.com/openshift/imagebuilder/cmd/imagebuilder && mv /tmp/gp/bin/imagebuilder /usr/local/bin && rm -rf /tmp/gp

# sops
RUN curl -L https://github.com/mozilla/sops/releases/download/3.0.3/sops-3.0.3.linux -o /usr/local/bin/sops && chmod a+x /usr/local/bin/sops

# kubernaut
RUN curl -L https://s3.amazonaws.com/datawire-static-files/kubernaut/$(curl -s https://s3.amazonaws.com/datawire-static-files/kubernaut/stable.txt)/kubernaut -o /usr/local/bin/kubernaut
RUN chmod +x /usr/local/bin/kubernaut

RUN echo 'PS1="[forge \w]\$ "' >> /root/.profile
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
ENV KUBECONFIG /root/.kube/kubernaut
ENV SCOUT_DISABLE 1
