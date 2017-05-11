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

import logging, sys, traceback
from eventlet.queue import Queue

class Dispatcher(object):

    def __init__(self):
        self.queue = Queue()

    def work(self):
        while True:
            try:
                fun, args = self.queue.get()
                logging.info("dispatching %s(%s)" % (fun.__name__, ", ".join(repr(a) for a in args)))
                fun(*args)
            except:
                logging.error(traceback.format_exc())

    def schedule(self, fun, *args):
        self.queue.put((fun, args))
