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

__all__ = [
    "__title__", "__version__",
    "__summary__", "__uri__",
    "__author__", "__email__",
    "__license__", "__copyright__",
]

__title__ = 'Forge'
__version__ = os.environ.get("BUILD_VERSION", 'dev')

__summary__ = "Forge Deployment Tooling"
__uri__ = "https://www.datawire.io"

__author__ = "datawire.io"
__email__ = "hello@datawire.io"

__license__ = "Apache License, Version 2.0"
__copyright__ = "2017 %s" % __author__
