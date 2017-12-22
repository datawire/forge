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

export PATH=${SRC_DIR}/dist:${PATH}
forge --version
kubernaut claim
{
    $DIR/istio.sh && py.test -svv
    RESULT=$?
} || true
kubernaut discard
$DIR/scout.sh
echo RESULT=$RESULT
exit $RESULT
