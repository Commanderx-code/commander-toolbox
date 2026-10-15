#!/bin/sh -e

# Commander Toolbox publishes one release channel, built by the source-sync
# workflow from every tested main revision; there are no separate pre-releases.
# This runs the same launcher as start.sh.
{
SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
if [ -f "$SCRIPT_DIR/start.sh" ]; then
    exec sh "$SCRIPT_DIR/start.sh" "$@"
fi
curl --fail --silent --location --proto '=https' --tlsv1.2 \
    https://raw.githubusercontent.com/Commanderx-code/commander-toolbox/main/start.sh | sh -s -- "$@"
} # End of wrapping
