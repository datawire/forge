#!/bin/bash


WARN=""

if [ -n "${FORGE_ECR_KEY_ID}" ]; then
    export AWS_ACCESS_KEY_ID=${FORGE_ECR_KEY_ID}
else
    WARN="${WARN}Warning: FORGE_ECR_KEY_ID is not set.\n"
fi

if [ -n "${FORGE_ECR_SECRET_KEY}" ]; then
    export AWS_SECRET_ACCESS_KEY=${FORGE_ECR_SECRET_KEY}
else
    WARN="${WARN}Warning: FORGE_ECR_SECRET_KEY is not set.\n"
fi

if [ -n "${KUBERNAUT_TOKEN}" ]; then
    kubernaut set-token "${KUBERNAUT_TOKEN}"
else
    WARN="${WARN}Warning: KUBERNAUT_TOKEN is not set.\n"
fi

if [ -n "${WARN}" ]; then
    RED='\033[1;31m'
    NC='\033[0m' # No Color
    echo -e ${RED}
    echo -e ${WARN}
    echo "You will not be able to run the full test suite, but you can"
    echo "use 'py.test -svv -k <foo>' to run a subset of the test suite."
    echo
    echo "If you wish to rectify this, save env.in as env and follow the"
    echo "directions in the file. (Do this outside the dev container.)"
    echo -e ${NC}
fi

git config --global user.email dev@forge.sh
git config --global user.name "Forge Dev"

exec /usr/bin/make "$@"
