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

build_bridge() {
    docker build -f $BRIDGE/Dockerfile $BRIDGE -t bridge
}

build_env() {
    docker build -f $DIR/Dockerfile $DIR -t forge
}

build() {
    build_bridge
    build_env
}

clean() {
    docker kill bridge || true
    docker rm bridge || true
    sleep 0.25
    docker volume rm forge || true
    sleep 0.25
}

bridge() {
    clean
    docker volume create forge
    docker run --name bridge -v "$DIR:/input" -v forge:/output -d bridge $(id -u)
}

run() {
    if [ -e "$DIR/env" ]; then
        ARGS="--env-file $DIR/env"
    else
        ARGS=""
    fi
    docker run --rm $ARGS -it -v /var/run/docker.sock:/var/run/docker.sock ${EXTRA_MOUNTS} -p 4000:4000 -p 35729:35729 forge "$@"
}


case $1 in

build)
    build
    ;;

clean)
    clean
    ;;

bridge)
    build
    bridge
    EXTRA_MOUNTS="-v forge:/work"
    run shell
    ;;

*)
    build_env
    run "$@"
    ;;

esac
