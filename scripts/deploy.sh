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

cd ${SRC_DIR}

TAG="$(git describe --exact-match --tags HEAD || true)"

if [ -z "$TAG" ]; then
    echo "Skipping deploy for untagged revision."
    exit
fi

FORGE_VERSION=$(dist/forge --version | cut -d" " -f2)
FORGE_VERSION_URL=$(python -c "import sys, urllib; print urllib.quote(\"${FORGE_VERSION}\")")
echo $FORGE_VERSION > dist/latest.txt
echo $FORGE_VERSION_URL > dist/latest.url

export AWS_ACCESS_KEY_ID=$DEPLOY_KEY_ID
export AWS_SECRET_ACCESS_KEY=$DEPLOY_KEY

aws s3 cp --acl public-read dist/forge s3://datawire-static-files/forge/$FORGE_VERSION/forge
aws s3 cp --acl public-read dist/latest.txt s3://datawire-static-files/forge/latest.txt
aws s3 cp --acl public-read dist/latest.url s3://datawire-static-files/forge/latest.url
echo "Uploaded dist/forge to $(cat dist/latest.txt)/forge"
