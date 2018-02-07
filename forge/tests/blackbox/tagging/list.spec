RUN git init
RUN git add .
RUN git commit -m "initial commit"
RUN git remote add origin https://github.com/datawire/forge.git

RUN forge -v deploy
RUN forge list
OUT deployment default.tagging-default:
OUT service default.tagging-default:
OUT deployment default.tagging-foo:
OUT service default.tagging-foo:
