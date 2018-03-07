# Copyright 2017 datawire. All rights reserved.
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

import collections, errno, logging, os, socket, yaml

def dict_representer(dumper, data):
    return dumper.represent_dict(data.iteritems())

def unicode_representer(dumper, uni):
    node = yaml.ScalarNode(tag=u'tag:yaml.org,2002:str', value=uni)
    return node

def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))

def setup_yaml():
    _mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG
    yaml.add_representer(collections.OrderedDict, dict_representer)
    yaml.add_representer(os._Environ, dict_representer)
    yaml.add_representer(unicode, unicode_representer)
    yaml.add_constructor(_mapping_tag, dict_constructor)

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s forge 0.0.1 %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    NOISY = ('socketio', 'engineio')
    for n in NOISY:
        logging.getLogger(n).setLevel(logging.WARNING)

def setup():
    setup_yaml()
    setup_logging()

def search_parents(name, start=None, root=False):
    rootiest = None
    prev = None
    path = start or os.getcwd()
    while path != prev:
        prev = path
        candidate = os.path.join(path, name)
        if os.path.exists(candidate):
            if root:
                rootiest = candidate
            else:
                return candidate
        path = os.path.dirname(path)
    return rootiest
