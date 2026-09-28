#!/bin/bash
# Charm City Sites — site handoff.
# Flips the quote form to the client's email, rebuilds, redeploys.
# Usage: handoff.sh <slug> <client-email>
#
# After this: submit ONE test quote on the live site. The client clicks the
# one-time FormSubmit confirmation email. From then on every lead goes
# straight to their inbox. (See OPERATIONS.md - "Handoff".)
set -uo pipefail

SLUG="${1:-}"
EMAIL="${2:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
FACTORY="$(dirname "$HERE")"
PY="$(command -v python3)"

[ -z "$SLUG" ] || [ -z "$EMAIL" ] && { echo "Usage: handoff.sh <slug> <client-email>"; exit 1; }
LEAD_FILE="$FACTORY/factory/sites/$SLUG/lead.json"
[ -f "$LEAD_FILE" ] || { echo "No lead.json for slug '$SLUG' - was the site built?"; exit 1; }

echo "Rebuilding $SLUG with form pointed at $EMAIL..."
"$PY" "$HERE/generate_site.py" --data-file "$LEAD_FILE" --form-email "$EMAIL" --force
GEN_OK=$?
if [ $GEN_OK -ne 0 ]; then echo "Rebuild failed."; exit 1; fi

echo "Redeploying..."
bash "$HERE/deploy.sh" "$SLUG"

cat <<'TIP'

Handoff done. Two things left (2 minutes, one time only):
  1. Open https://SLUG.pages.dev and submit one test quote yourself.
  2. Tell the client to click the FormSubmit confirmation email it triggers.
After that, every real lead lands in their inbox automatically.
TIP
