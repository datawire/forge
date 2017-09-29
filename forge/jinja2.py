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

from __future__ import absolute_import

from .tasks import task, TaskError
from jinja2 import Environment, FileSystemLoader, Template, TemplateError, TemplateNotFound
import os, shutil

def _do_render(env, root, name, variables):
    try:
        return env.get_template(name).render(**variables)
    except TemplateNotFound, e:
        raise TaskError("%s/%s: %s" % (root, name, "template not found"))
    except TemplateError, e:
        raise TaskError("%s/%s: %s" % (root, name, e))

@task()
def render(source, target, **variables):
    """Renders a file or directory as a jinja template using the supplied
    variables.

    The source is a path pointing to either an individual file or a
    directory. The target is a path pointing to the desired location
    of the output.

    If the source points to a file, then the target is
    created/overwritten as a file.

    If the source points to a directory, the target is created as a
    directory. If the target already exists, it is removed and
    recreated prior to rendering the template.
    """
    root = source if os.path.isdir(source) else os.path.dirname(source)
    env = Environment(loader=FileSystemLoader(root))
    if os.path.isdir(source):
        if os.path.exists(target):
            shutil.rmtree(target)
        os.makedirs(target)

        for path, dirs, files in os.walk(source):
            for name in files:
                relpath = os.path.join(os.path.relpath(path, start=source), name)
                rendered = _do_render(env, root, relpath, variables)
                outfile = os.path.join(target, relpath)
                outdir = os.path.dirname(outfile)
                if not os.path.exists(outdir):
                    os.makedirs(outdir)
                with open(outfile, "write") as f:
                    f.write(rendered)
    else:
        rendered = _do_render(env, root, os.path.basename(source), variables)
        with open(target, "write") as f:
            f.write(rendered)

@task()
def renders(name, source, **variables):
    """
    Renders a string as a jinja template. The name is used where
    filename would normally appear in error messages.
    """
    try:
        return Template(source).render(**variables)
    except TemplateError, e:
        raise TaskError("%s: %s" % (name, e))
