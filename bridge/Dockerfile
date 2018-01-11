FROM alpine:3.6

ARG UNISON_VERSION=2.48.4

# Install in one run so that build tools won't remain in any docker
# layers
RUN apk add --no-cache build-base curl bash supervisor inotify-tools rsync ruby \
    && apk add --update-cache --repository http://dl-4.alpinelinux.org/alpine/edge/testing/ ocaml \
    && curl -L https://github.com/bcpierce00/unison/archive/$UNISON_VERSION.tar.gz | tar zxv -C /tmp \
    && cd /tmp/unison-${UNISON_VERSION} \
    && sed -i -e 's/GLIBC_SUPPORT_INOTIFY 0/GLIBC_SUPPORT_INOTIFY 1/' src/fsmonitor/linux/inotify_stubs.c \
    && make UISTYLE=text NATIVE=true STATIC=true \
    && cp src/unison src/unison-fsmonitor /usr/local/bin \
    && apk del curl build-base ocaml \
    && apk add --no-cache libgcc libstdc++ \
    && rm -rf /tmp/unison-${UNISON_VERSION} \
    && apk add --no-cache --repository http://dl-4.alpinelinux.org/alpine/edge/testing/ shadow \
    && apk add --no-cache tzdata

# These can be overridden later
ENV LANG="C.UTF-8" \
    HOME="/root"

VOLUME /output
WORKDIR /input

COPY entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
