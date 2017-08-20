#!/bin/bash

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

SRC_DIR=${DIR}/..
WHL_DIR=build/wheelhouse
OUTPUT=dist/forge

aws --no-sign-request s3 sync s3://datawire-static-files/wheelhouse $WHL_DIR

cd $WHL_DIR

for whl in $(ls *-manylinux1_*.whl); do
  cp $whl $(echo $whl | sed s/manylinux1/linux/)
done

cd $SRC_DIR

pip wheel --no-index --no-deps . -w $WHL_DIR
pex --no-pypi -f $WHL_DIR -r requirements.txt Forge -e forge.cli:call_main -o dist/forge --disable-cache --platform linux_x86_64 --platform linux_i686 --platform macosx_10_11_x86_64
echo "Created ${OUTPUT}"
