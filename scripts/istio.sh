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

cat <<EOF | kubectl apply -f -
---
# Pilot service for discovery
apiVersion: v1
kind: ConfigMap
metadata:
  name: istio
data:
  mesh: |-
    # Uncomment the following line to enable mutual TLS between proxies
    # authPolicy: MUTUAL_TLS
    mixerAddress: istio-mixer:9091
    discoveryAddress: istio-pilot:8080
    ingressService: istio-ingress
    zipkinAddress: zipkin:9411
EOF
