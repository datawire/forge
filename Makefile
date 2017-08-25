.PHONY: default forge release

VERSION=$(shell python -c "import versioneer; print versioneer.get_versions()['version']")
SHELL:=/bin/bash
SOURCE=$(shell find forge -name "*.py")

default:
	@echo "See https://github.com/datawire/forge/blob/master/DEVELOPING.md"

version:
	@echo $(VERSION)

## Setup dependencies ##

virtualenv:
	virtualenv --python=python2 virtualenv
	virtualenv/bin/pip install -Ur requirements.txt

## Development ##

forge: dist/forge

dist/forge: ${SOURCE}
	scripts/build.sh

clean:
	rm -rf build dist

## Release ##

