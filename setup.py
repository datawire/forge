# Copyright 2015 datawire. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import versioneer

ROOT_DIR = os.path.dirname(__file__)

from setuptools import setup

metadata = {}
with open(os.path.join(ROOT_DIR, "forge/_metadata.py")) as fp:
    exec(fp.read(), metadata)

with open(os.path.join(ROOT_DIR, "requirements.txt")) as fp:
    install_requirements = [i.strip() for i in list(fp)
                            if i.strip() and not i.strip().startswith("#")]

def recursive_hack(dir):
    return [os.path.join(dir, *['*']*i) for i in range(1, 10)]

setup(name=metadata["__title__"],
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      description=metadata["__summary__"],
      author=metadata["__author__"],
      author_email=metadata["__email__"],
      url=metadata["__uri__"],
      license=metadata["__license__"],
      packages=['forge'],
      package_data={'forge': recursive_hack('static')},
      install_requires=install_requirements,
      entry_points={"console_scripts": ["forge = forge.cli:call_main"]},
      keywords=['Deployment', 'Kubernetes', 'service', 'microservice'],
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: Apache Software License',
          'Operating System :: MacOS',
          'Operating System :: OS Independent',
          'Operating System :: POSIX',
          'Topic :: Software Development'
      ]
)
