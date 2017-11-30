RUN git init
RUN git add .
RUN git commit -m "inital commit"
RUN git remote add origin https://github.com/datawire/forge.git
RUN forge pull
OUT cloning; OUT forge-dep-test-foo
OUT cloning; OUT forge-dep-test-bar
NOT cloning
CWD child
RUN forge pull
NOT cloning
