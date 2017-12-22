#!/bin/bash
set -e

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

SRC_DIR=${DIR}/..
BIN_DIR=/usr/local/bin

curl -L https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl -o ${BIN_DIR}/kubectl
chmod +x ${BIN_DIR}/kubectl

ISTIO_VERSION=0.4.0
ISTIO=istio-${ISTIO_VERSION}

curl -L https://github.com/istio/istio/releases/download/${ISTIO_VERSION}/${ISTIO}-linux.tar.gz -o /tmp/istio.tar.gz
tar -C /tmp -xzf /tmp/istio.tar.gz
mv /tmp/${ISTIO}/bin/istioctl ${BIN_DIR}
chmod +x ${BIN_DIR}/istioctl

curl -L https://s3.amazonaws.com/datawire-static-files/kubernaut/$(curl -s https://s3.amazonaws.com/datawire-static-files/kubernaut/stable.txt)/kubernaut -o ${BIN_DIR}/kubernaut
chmod +x ${BIN_DIR}/kubernaut
