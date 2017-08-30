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

import os
from tempfile import mkdtemp

def mktree(treespec, **substitutions):
    files = parse_treespec(treespec, **substitutions)
    root = mkdtemp()
    for name, content in files.items():
        path = os.path.join(root, name)
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(path, "write") as f:
            f.write(content)
    return root

def parse_treespec(treespec, **substitutions):
    result = {}

    filename = None
    filelines = []
    for lineno, line in enumerate(treespec.splitlines()):
        if filename is None:
            if line[:2] == "@@":
                filename = line[2:]
                if not filename:
                    raise ValueError("%s: found '@@', expecting filename" % lineno)
        else:
            if line == "@@":
                content = "\n".join(filelines)
                for k, v in substitutions.items():
                    content = content.replace(k, v)
                result[filename] = content
                filename = None
                filelines = []
            else:
                filelines.append(line)

    if filename:
        raise ValueError("unterminated file: %s" % filename)
    return result
