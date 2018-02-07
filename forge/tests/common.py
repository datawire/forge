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
from forge.match import match

@match(basestring)
def mktree(treespec, **substitutions):
    files = parse_treespec(treespec)
    return mktree(files, **substitutions)

@match(dict)
def mktree(files, **substitutions):
    root = mkdtemp()
    for name, content in files.items():
        for k, v in substitutions.items():
            content = content.replace(k, v)
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
                result[filename] = content
                filename = None
                filelines = []
            else:
                filelines.append(line)

    if filename:
        raise ValueError("unterminated file: %s" % filename)
    return result

import re

TOKENS = (
    ("VERSION", r'\b[0-9a-fA-F]{40}\.(sha|git)'),
    ("TEST_ID", r'test_id_[0-9]+(_[0-9]+)?')
)

def tokenize(s):
    while s:
        matches = [re.search(t, s) for n, t in TOKENS]
        nearest = None
        for m in matches:
            if not m: continue
            if nearest:
                if m.start() < nearest.start():
                    nearest = m
            else:
                 nearest = m
        if nearest:
            yield "LITERAL", s[:nearest.start()]
            yield TOKENS[matches.index(nearest)][0], nearest.group()
            s = s[nearest.end():]
        else:
            yield "LITERAL", s
            break

def defuzz(s):
    result = ""
    counters = {}
    names = {}
    for ttype, value in tokenize(s):
        if ttype == "LITERAL":
            result += value
        else:
            if value not in names:
                idx = counters.get(ttype, 0) + 1
                names[value] = "%s_%s" % (ttype, idx)
                counters[ttype] = idx
            result += str(names[value])
    return result
