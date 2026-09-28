#!/bin/bash
# Charm City Sites — one-glance health check.
# Usage: status.sh   (or double-click "Open Dashboard.command")
clear 2>/dev/null || true
HERE="$(cd "$(dirname "$0")" && pwd)"
FACTORY="$(dirname "$HERE")"

G='\033[32m'; R='\033[31m'; Y='\033[33m'; B='\033[1m'; N='\033[0m'
ok()   { echo -e "  ${G}[UP]${N} $1"; }
down() { echo -e "  ${R}[DOWN]${N} $1"; }

echo -e "${B}Charm City Sites - Factory Status${N}   ($(date '+%a %b %d %H:%M'))"
echo

echo "Brain (FreeLLMAPI, port 3001)"
curl -sf --max-time 4 http://localhost:3001/v1/models >/dev/null 2>&1 && ok "router answering" || down "router not answering (sites still build with default copy)"

echo "Offline brain (Ollama, port 11434)"
curl -sf --max-time 4 http://localhost:11434/api/tags >/dev/null 2>&1 && ok "ollama answering" || down "ollama not running (optional - only needed offline)"

echo "Spine (n8n, port 5678)"
curl -sf --max-time 4 http://localhost:5678/healthz >/dev/null 2>&1 && ok "n8n answering" || down "n8n not answering - run: open http://localhost:5678"

echo "Cloudflare token"
if [ -f "$FACTORY/factory/env.sh" ] && grep -q '^CLOUDFLARE_API_TOKEN=..*' "$FACTORY/factory/env.sh"; then
  ok "token present in factory/env.sh"
else
  echo -e "  ${Y}[TODO]${N} paste your Cloudflare API token into factory/env.sh"
fi

echo
SITES=$(find "$FACTORY/factory/sites" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
INBOX=$(find "$FACTORY/factory/leads_inbox" -name '*.json' 2>/dev/null | wc -l | tr -d ' ')
echo -e "${B}Sites built:${N} $SITES    ${B}Leads waiting in inbox:${N} $INBOX"
echo
echo -e "${B}Last factory activity:${N}"
tail -n 5 "$FACTORY/factory/logs/generate.log" 2>/dev/null | sed 's/^/  /' || echo "  (nothing yet)"
echo
echo -e "Open the control panel: ${B}http://localhost:5678${N}"
