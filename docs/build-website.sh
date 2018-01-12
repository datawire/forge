#!/bin/bash
set -eo pipefail
IFS=$'\n\t'
# http://redsymbol.net/articles/unofficial-bash-strict-mode/
# because I don't know what I'm doing in Bash

set -x

cd "$(dirname "$0")"

# First we install forge in order to generate the necessary docs
cd ..
pip install .
forge schema_docs forge_yaml > docs/docs/reference/forge-config.md
forge schema_docs service_yaml > docs/docs/reference/service-descriptor.md

# Build the documentation as usual
cd docs
npm install
npm run build

# Remove the data-path attributed of every list item linking to index.html,
# which are the ones marked with data-level="1.1". This causes the GitBook
# scripts to redirect to the index page rather fetching and replacing just
# the content area, as they do for proper GitBook-generated pages.

perl -pi \
    -e "s/{VERSION}/$VERSION/g;" \
    -e 's,<li class="chapter " data-level="1.1" data-path="[^"]*">,<li class="chapter " data-level="1.1">,g;' \
    $(find _book -name '*.html') _book/search_index.json

# Replace index.html with our hand-crafted landing page
cp index.html _book/

# Build apidocs
pip install sphinx==1.6.5
cd api
make html
cp -r _build/html ../_book/api
