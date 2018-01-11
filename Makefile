.PHONY: shell test release

## Development ##

shell:
	@/bin/bash -l

test:
	scripts/build.sh && scripts/test.sh

apidocs:
	cd docs/api && make doctest
	cd docs/api && make html

## Release ##

release:
	scripts/build.sh && scripts/test.sh && scripts/deploy.sh
