FROM ubuntu:xenial

# base
RUN apt-get update && apt-get -y install curl
# forge deps
RUN apt-get -y install python python-pip # gcc python-dev musl-dev
# test deps
RUN apt-get -y install python3 docker.io git
# doc deps
RUN apt-get -y install nodejs perl

WORKDIR /work
COPY scripts scripts
RUN scripts/setup.sh

COPY requirements.txt dev-requirements.txt ./
RUN pip install -r dev-requirements.txt
RUN pip install -r requirements.txt

RUN echo 'PS1="[forge \w]\$ "' >> /root/.profile
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

ENV KUBECONFIG /root/.kube/kubernaut
ENV SCOUT_DISABLE 1
COPY .git .git
COPY forge forge
COPY examples examples
COPY docs docs
COPY Makefile setup.cfg setup.py versioneer.py MANIFEST.in LICENSE ./
COPY entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
