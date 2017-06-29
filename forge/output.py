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

import eventlet, sys

re = eventlet.import_patched('re')
blessed = eventlet.import_patched('blessed')

class Terminal(blessed.Terminal):

    def __init__(self):
        blessed.Terminal.__init__(self)
        # for tokenizer, the '.lastgroup' is the primary lookup key for
        # 'self.caps', unless 'MISMATCH'; then it is an unmatched character.
        self._caps_compiled_any = re.compile('|'.join(
            cap.named_pattern for name, cap in self.caps.items()
        ) + '|(?P<MISMATCH>\w+|\W)')
        self._caps_unnamed_any = re.compile('|'.join(
            '({0})'.format(cap.pattern) for name, cap in self.caps.items()
        ) + '|(\w+|\W)')

        self._wrap_cache = {}

    def wrap(self, text):
        lines = []
        for line in text.splitlines():
            lines.extend(self.wrap_line(line))
        return lines

    def wrap_line(self, text):
        if text in self._wrap_cache:
            lines = self._wrap_cache[text]
        else:
            lines = []
            line = ''
            width = 0
            for token, cap in blessed.sequences.iter_parse(self, text):
                if cap:
                    delta = cap.horizontal_distance(token)
                    assert delta < self.width, (repr(token), cap)
                    if width + delta >= self.width:
                        lines.append(line)
                        line = ''
                        width = 0
                    else:
                        line += token
                        width += delta
                else:
                    while token:
                        fragment = token[:self.width-width]
                        token = token[len(fragment):]
                        line += fragment
                        width += len(fragment)
                        if width >= self.width:
                            lines.append(line)
                            line = ''
                            width = 0
            if line:
                lines.append(line)
            self._wrap_cache[text] = lines

        return lines

class Drawer(object):

    def __init__(self):
        self.previous = []
        self.terminal = Terminal()

    def draw(self, lines):
        screenful = lines[-self.terminal.height:]

        common_head = 0
        for old, new in zip(self.previous, screenful):
            if old == new:
                common_head += 1
            else:
                break

        sys.stdout.write(self.terminal.move_up*(len(self.previous)-common_head))

        for line in screenful[common_head:]:
            # XXX: should really wrap this properly somehow, but
            #      writing out more than the terminal width will mess up
            #      the movement logic
            delta = len(line) - self.terminal.length(line)
            sys.stdout.write(line[:self.terminal.width+delta])
            sys.stdout.write(self.terminal.clear_eol + self.terminal.move_down)

        sys.stdout.write(self.terminal.clear_eos)
        self.previous = screenful
