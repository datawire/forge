.PHONY: shell test release

## Development ##

shell:
	@/bin/bash -l

test:
	scripts/build.sh && scripts/test.sh

apidocs:
	rm -rf /tmp/docs
	sphinx-apidoc -F -M --ext-autodoc --ext-doctest -o /tmp/docs forge
	cd /tmp/docs && make doctest SPHINXOPTS=-W
	cd /tmp/docs && make html

serve: apidocs
	cd /tmp/docs/_build/html && python -m SimpleHTTPServer 4000

## Release ##

release:
	scripts/build.sh && scripts/test.sh && scripts/deploy.sh
