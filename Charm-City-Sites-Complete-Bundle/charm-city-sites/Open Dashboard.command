#!/bin/bash
# Double-click me. Shows factory health and opens the control panel.
cd "$(dirname "$0")"
bash scripts/status.sh
echo ""
read -n 1 -s -r -p "Opening the n8n control panel - press any key to close..." _
echo ""
open "http://localhost:5678" 2>/dev/null || xdg-open "http://localhost:5678" 2>/dev/null || true
