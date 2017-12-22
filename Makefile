.PHONY: shell test release

## Development ##

shell:
	@/bin/bash -l

test:
	scripts/build.sh && scripts/test.sh

## Release ##

release:
	scripts/build.sh && scripts/test.sh && scripts/deploy.sh
