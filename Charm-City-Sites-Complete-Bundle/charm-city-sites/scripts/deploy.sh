#!/bin/bash
# Charm City Sites — deploy a built site to Cloudflare Pages (free).
# Usage: deploy.sh <slug>
# Prints one JSON line at the end for n8n to parse. All wrangler noise goes to the log.
set -uo pipefail

SLUG="${1:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
FACTORY="$(dirname "$HERE")"
ENV_FILE="$FACTORY/factory/env.sh"
LOG="$FACTORY/factory/logs/deploy.log"
mkdir -p "$FACTORY/factory/logs"

[ -z "$SLUG" ] && { echo '{"ok":false,"error":"deploy.sh needs a slug"}'; exit 1; }
SITE_DIR="$FACTORY/factory/sites/$SLUG"
[ -d "$SITE_DIR" ] || { echo "{\"ok\":false,\"error\":\"no site dir for $SLUG\"}"; exit 1; }

# Load Cloudflare credentials (written by install.sh / you, in factory/env.sh)
[ -f "$ENV_FILE" ] && . "$ENV_FILE"
if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
  echo '{"ok":false,"error":"CLOUDFLARE_API_TOKEN missing in factory/env.sh"}'
  exit 1
fi
export CLOUDFLARE_API_TOKEN
[ -n "${CLOUDFLARE_ACCOUNT_ID:-}" ] && export CLOUDFLARE_ACCOUNT_ID

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

run_deploy() {
  # Create the project on first deploy; "already exists" is fine.
  wrangler pages project create "$SLUG" --production-branch main >>"$LOG" 2>&1 || true
  wrangler pages deploy "$SITE_DIR" --project-name="$SLUG" --branch=main >>"$LOG" 2>&1
}

log "deploy start: $SLUG"
if run_deploy; then
  log "deploy ok: https://$SLUG.pages.dev"
  echo "{\"ok\":true,\"slug\":\"$SLUG\",\"url\":\"https://$SLUG.pages.dev\"}"
  exit 0
fi

# PRD: one automatic retry, then surface the error.
log "deploy failed once for $SLUG - retrying in 10s"
sleep 10
if run_deploy; then
  log "deploy ok on retry: https://$SLUG.pages.dev"
  echo "{\"ok\":true,\"slug\":\"$SLUG\",\"url\":\"https://$SLUG.pages.dev\",\"retried\":true}"
  exit 0
fi

log "deploy FAILED twice for $SLUG (row will be marked deploy_error)"
echo "{\"ok\":false,\"slug\":\"$SLUG\",\"error\":\"deploy failed twice - see factory/logs/deploy.log\"}"
exit 1
