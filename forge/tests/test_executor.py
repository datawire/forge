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

from forge.executor import executor
import time

executor.setup()

def sleeper(n):
    time.sleep(n)

def test_sync_executor():
    exe = executor("sync")
    start = time.time()
    exe.run(sleeper, 0.5)
    exe.run(sleeper, 0.5)
    exe.wait()
    elapsed = time.time() - start
    assert elapsed > 0.9, elapsed

def test_async_executor():
    exe = executor("async", async=True)
    start = time.time()
    exe.run(sleeper, 0.5)
    exe.run(sleeper, 0.5)
    exe.wait()
    elapsed = time.time() - start
    assert elapsed < 0.6, elapsed
