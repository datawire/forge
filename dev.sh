#!/bin/bash
set -exo pipefail

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

BRIDGE=$DIR/bridge

cleanup() {
    docker kill bridge || true
    sleep 0.25
    docker volume rm forge || true
    sleep 0.25
}

build () {
    docker build -f $BRIDGE/Dockerfile $BRIDGE -t bridge
    docker build -f $DIR/Dockerfile $DIR -t forge
}

watch() {
    cleanup
    docker volume create forge
    docker run --rm --name bridge -v $DIR:/input -v forge:/output -d bridge
}

run() {
    docker run --rm --env-file $DIR/env -it -v /var/run/docker.sock:/var/run/docker.sock -v forge:/work -p 4000:4000 -p 35729:35729 forge "$@"
}

build
run "$@"
