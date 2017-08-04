.PHONY: default release

VERSION=$(shell git describe --tags)
SHELL:=/bin/bash

default:
	@echo "See http://forge.sh/additional-information/developing.html"

version:
	@echo $(VERSION)

## Setup dependencies ##

virtualenv:
	virtualenv --python=python2 virtualenv
	virtualenv/bin/pip install -Ur requirements.txt

## Development ##

## Release ##

