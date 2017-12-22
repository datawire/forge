#!/bin/bash

test -n "${KUBERNAUT_TOKEN}" && kubernaut set-token "${KUBERNAUT_TOKEN}"
git config --global user.email dev@forge.sh
git config --global user.name "Forge Dev"

exec /usr/bin/make "$@"
