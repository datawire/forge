FROM alpine:3.6
RUN apk add --no-cache rsync curl python
RUN curl https://s3.amazonaws.com/datawire-static-files/forge/0.3.23/forge -o /usr/bin/forge
RUN chmod a+x /usr/bin/forge
COPY watch /watch
VOLUME /output
WORKDIR /input
ENTRYPOINT ["forge", "invoke", "/watch"]
