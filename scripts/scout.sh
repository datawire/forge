#!/bin/bash
set -e

SCOUT_FILE="${HOME}/.config/forge/id"

if [ -e "$SCOUT_FILE" ]; then
    echo "Forge Scout ID is: $(cat $SCOUT_FILE)"
else
    echo "Forge Scout ID was not generated."
fi
