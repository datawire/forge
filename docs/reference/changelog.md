---
layout: doc
weight: 6
title: "Changelog"
categories: reference
---

#### 0.2.13 (Agust 23, 2017)

* Add command line arg: -n,--namespace=<name> for deploy.

#### 0.2.12 (Agust 22, 2017)

* Pass the K8S_NAMESPACE environment variable through to kubectl

#### 0.2.11 (August 21, 2017)

* noop release for travis

#### 0.2.10 (August 16, 2017)

* Change to standalone pex binary for easier distribution/installation.
* Compute version based on service subdirectory rather than entire repo.

#### 0.2.9 (July 24, 2017)

* Environment based customization of service configuration: [#23](https://github.com/datawire/forge/issues/23)
* Make the forge setup validation image configurable:  [#24](https://github.com/datawire/forge/issues/24)

#### 0.2.8 (July 13, 2017)

* Service level dependencies: [#8](https://github.com/datawire/forge/issues/8), [#16](https://github.com/datawire/forge/issues/16)
* Search for service.yaml in parent directories: [#20](https://github.com/datawire/forge/issues/20)

#### 0.2.7 (July 12, 2017)

* Don't blow up when there is no USER variable set: [#18](https://github.com/datawire/forge/issues/18)

#### 0.2.6 (July 7, 2017)

* Reduce some noise when reporting errors.

#### 0.2.5 (June 30, 2017)

* Added istio support: [#13](https://github.com/datawire/forge/issues/13)

#### 0.2.4 (June 30, 2017)

* Less noise on setup.

#### 0.2.3 (June 26, 2017)

* Clearer reporting of docker authentication errors.

#### 0.2.2 (June 26, 2017)

* Omit stack trace for expected errors.

#### 0.2.1 (June 26, 2017)

* Pin eventlet version dependency.

#### 0.2 (June 26, 2017)

* Better output and improved error reporting for background tasks.
* Improved docs around global config and docker password: [#11](https://github.com/datawire/forge/issues/11)
* Clarified setup output and provide better defaults: [#10](https://github.com/datawire/forge/issues/10), [#6](https://github.com/datawire/forge/issues/6)

#### 0.1 (May 24, 2017)

* Initial release
