RUN tee .gitignore
TYPE services
EOF
RUN git init
RUN git add .
RUN git commit -m "initial commit"
RUN git remote add origin https://github.com/datawire/forge.git
RUN forge pull
OUT cloning https://github.com/datawire/forge-dep-test-foo.git->.forge/forge-dep-test-foo
NOT cloning
RUN forge deploy
