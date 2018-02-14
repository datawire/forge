RUN git init
RUN git add .
RUN git commit -m "initial commit"
RUN git remote add origin https://github.com/datawire/forge.git

RUN forge -v deploy
RUN forge --profile foo -v deploy
RUN forge list
OUT deployment default.tagging-default:
OUT service default.tagging-default:
OUT deployment default.tagging-foo:
OUT service default.tagging-foo:

RUN forge list tagging default
MATCH
tagging[default]: https://github.com/datawire/forge.git | service.yaml | VERSION_1
  deployment default.tagging-default:
    {{.*}}
  service default.tagging-default:
    {{.*}}
END
RUN forge list tag*
MATCH
tagging[default]: https://github.com/datawire/forge.git | service.yaml | VERSION_1
  deployment default.tagging-default:
    {{.*}}
  service default.tagging-default:
    {{.*}}

tagging[foo]: https://github.com/datawire/forge.git | service.yaml | VERSION_1
  deployment default.tagging-foo:
    {{.*}}
  service default.tagging-foo:
    {{.*}}
END
