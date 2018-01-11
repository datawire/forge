#!/bin/sh

UNISON_USER="$1"

unison -socket 1234 &

CMD="/usr/local/bin/unison -owner=false -group=false -repeat watch -batch -times -force newer /input socket://localhost:1234//output"

if [ -n "$UNISON_USER" ]; then
    adduser unison -Du $UNISON_USER
    chown unison /output
    su unison -c "$CMD"
else
    $CMD
fi
