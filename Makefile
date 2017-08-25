.PHONY: default release

VERSION=$(shell git describe --tags)
SHELL:=/bin/bash

default:
	@echo "See https://github.com/datawire/forge/blob/master/DEVELOPING.md"

version:
	@echo $(VERSION)

## Setup dependencies ##

virtualenv:
	virtualenv --python=python2 virtualenv
	virtualenv/bin/pip install -Ur requirements.txt

## Development ##

## Release ##

