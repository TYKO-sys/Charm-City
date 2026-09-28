#!/bin/bash
# Charm City Sites — copy/refresh the kit from the Windows folder into the
# Linux side. Called by 1-INSTALL-WINDOWS.bat with the Windows kit path.
# Merge semantics: adds and overwrites kit files, NEVER deletes anything —
# your secrets (factory/env.sh), built sites, and logs always survive.

set -uo pipefail

[ $# -ge 1 ] || { echo "usage: sync_kit.sh <windows-kit-folder>"; exit 1; }
SRC="$(wslpath "$1" 2>/dev/null)"
if [ -z "$SRC" ] || [ ! -d "$SRC" ]; then
  echo "!! Cannot see the Windows folder: $1"
  echo "   Extract charm-city-sites-kit.zip fully, then run the .bat again."
  exit 1
fi

KIT=/home/ccs/charm-city-sites
mkdir -p "$KIT"
cp -a "$SRC/." "$KIT/"
chown -R ccs:ccs "$KIT"
echo "    kit synced: $SRC -> $KIT (secrets and built sites preserved)"
