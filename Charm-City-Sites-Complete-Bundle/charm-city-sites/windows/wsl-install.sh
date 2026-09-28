#!/bin/bash
# Charm City Sites — WSL installer (Windows laptops).
# Runs INSIDE Ubuntu as root. Launched by 1-INSTALL-WINDOWS.bat.
# Safe to re-run: refreshes workflows and schedules, never touches the
# secrets in factory/env.sh, never deletes built sites or logs.

set -uo pipefail

KIT=/home/ccs/charm-city-sites
LOG="$KIT/factory/logs"
mkdir -p "$LOG"

step() { echo ""; echo "==> $*"; }
say()  { echo "    $*"; }
fail() { echo "    !! $* (install continues; see factory/logs/)"; }

[ -d "$KIT/n8n" ] || { echo "!! Kit not found at $KIT - run 1-INSTALL-WINDOWS.bat again."; exit 1; }
[ "$(id -u)" = "0" ] || { echo "!! Must run as root (the .bat file does this for you)."; exit 1; }

echo "=== Charm City Sites WSL install started $(date) ==="

# ---------------------------------------------------------------- 1. base tools
step "1/7 Base tools (python3, git, curl)"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y >>"$LOG/apt.log" 2>&1 || fail "apt update"
apt-get install -y curl git python3 ca-certificates >>"$LOG/apt.log" 2>&1 || fail "base tools"
command -v python3 >/dev/null 2>&1 && say "python3: $(python3 --version 2>&1)"

# ---------------------------------------------------------------- 2. node 20
step "2/7 Node.js 20 (runs the spine)"
NODE_MAJOR="$(node -v 2>/dev/null | sed 's/^v//' | cut -d. -f1)"
case "${NODE_MAJOR:-}" in ''|*[!0-9]*) NODE_MAJOR=0;; esac
if [ "$NODE_MAJOR" -lt 20 ]; then
  say "Installing Node 20 via NodeSource..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >>"$LOG/nodesource.log" 2>&1 || fail "nodesource setup"
  apt-get install -y nodejs >>"$LOG/nodesource.log" 2>&1 || fail "node install"
fi
say "node: $(node --version 2>/dev/null || echo 'installed')"

# ---------------------------------------------------------------- 3. n8n + wrangler
step "3/7 n8n + wrangler (the spine + the deployer, ~3 min first time)"
command -v n8n >/dev/null 2>&1 || npm install -g n8n --no-audit --no-fund >>"$LOG/npm.log" 2>&1 || fail "n8n install"
command -v wrangler >/dev/null 2>&1 || npm install -g wrangler --no-audit --no-fund >>"$LOG/npm.log" 2>&1 || fail "wrangler install"
say "n8n: $(n8n --version 2>/dev/null || echo 'installed') | wrangler: present"

# ---------------------------------------------------------------- 4. docker
step "4/7 Docker (carries the AI brain)"
apt-get install -y docker.io docker-compose-v2 >>"$LOG/apt.log" 2>&1 \
  || apt-get install -y docker.io >>"$LOG/apt.log" 2>&1 \
  || fail "docker install"
usermod -aG docker ccs 2>/dev/null || true
if [ -d /run/systemd/system ]; then
  systemctl enable docker >/dev/null 2>&1 || true
  systemctl start docker  >/dev/null 2>&1 || true
else
  service docker start >/dev/null 2>&1 || (nohup dockerd >>"$LOG/docker.log" 2>&1 &)
fi
for i in $(seq 1 30); do docker info >/dev/null 2>&1 && break; sleep 1; done
docker info >/dev/null 2>&1 && say "Docker: up" || fail "docker did not come up - see factory/logs/docker.log"

# ---------------------------------------------------------------- 5. FreeLLMAPI
step "5/7 FreeLLMAPI - the AI brain, port 3001"
if runuser -u ccs -- bash -lc 'curl -sf --max-time 4 http://localhost:3001/v1/models >/dev/null 2>&1'; then
  say "FreeLLMAPI already answering on port 3001."
else
  runuser -u ccs -- bash -lc 'curl -fsSL https://freellmapi.co/install.sh | bash' >>"$LOG/freellmapi.log" 2>&1 \
    && say "FreeLLMAPI installed and started - dashboard at http://localhost:3001" \
    || fail "FreeLLMAPI install - see factory/logs/freellmapi.log"
fi

# ---------------------------------------------------------------- 6. Ollama (offline fallback)
step "6/7 Ollama - the offline brain, laptop-sized model"
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh >>"$LOG/ollama.log" 2>&1 || fail "ollama install"
fi
if command -v ollama >/dev/null 2>&1; then
  if [ -d /run/systemd/system ]; then
    systemctl enable ollama >/dev/null 2>&1 || true
    systemctl start ollama  >/dev/null 2>&1 || true
  fi
  runuser -u ccs -- bash -lc 'pgrep -x ollama >/dev/null 2>&1 || nohup ollama serve > $HOME/.ollama_serve.log 2>&1 &' 2>/dev/null || true
  runuser -u ccs -- bash -lc 'nohup ollama pull qwen2.5:3b > $HOME/.ollama_pull.log 2>&1 &' 2>/dev/null || true
  say "Ollama in. Background-downloading the offline model (2 GB, only used with no internet)."
else
  say "Ollama not installed - fine, FreeLLMAPI is the primary brain."
fi

# ---------------------------------------------------------------- 7. wire + import + schedule
step "7/7 Personalize, import the 5 workflows, schedule the heartbeat"

# secrets file (create once, never overwrite)
if [ ! -f "$KIT/factory/env.sh" ]; then
  cp "$KIT/factory/env.example.sh" "$KIT/factory/env.sh"
fi
# laptop CPUs get the 3b offline model; the Mac installer uses 14b
sed -i 's/^OLLAMA_MODEL=.*/OLLAMA_MODEL=qwen2.5:3b/' "$KIT/factory/env.sh"

# n8n env for manual sessions (marker-guarded)
if ! grep -q "ccs-n8n-env" /home/ccs/.bashrc 2>/dev/null; then
  cat >> /home/ccs/.bashrc <<'RC'
# ccs-n8n-env
export TZ=America/New_York
export GENERIC_TIMEZONE=America/New_York
export N8N_SECURE_COOKIE=false
export N8N_DIAGNOSTICS_ENABLED=false
RC
fi

# optional sheet auto-wiring
echo "Optional: paste your Google Sheet URL to auto-wire every workflow."
echo "   (From the sheet's address bar, e.g. https://docs.google.com/spreadsheets/d/ABC123...)"
SHEET_URL=""
if [ -t 0 ]; then
  printf "   Paste it here, or just press Enter to skip: "
  read -r SHEET_URL
else
  say "No interactive console detected - skipping the sheet question."
fi
SHEET_ID=$(printf '%s' "$SHEET_URL" | python3 -c "
import re, sys
m = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', sys.stdin.read() or '')
print(m.group(1) if m else '')" 2>/dev/null || echo "")
[ -n "$SHEET_ID" ] && say "Sheet id captured: $SHEET_ID" || say "No sheet given - pick it manually in n8n later (see OPERATIONS.md 1.3)."

python3 - "$KIT" "$SHEET_ID" <<'PYEOF'
import glob, os, sys
kit, sheet_id = sys.argv[1], sys.argv[2]
for path in sorted(glob.glob(os.path.join(kit, "n8n", "*.json"))):
    with open(path, "r", encoding="utf-8") as fh:
        body = fh.read()
    body = body.replace("__DIR__", kit)
    if sheet_id:
        body = body.replace("__SHEET_ID__", sheet_id)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    print("    wired:", os.path.basename(path))
PYEOF

# remove older imports of the same workflows so re-runs never duplicate
rm -f /tmp/ccs_existing.json
runuser -u ccs -- bash -lc 'n8n export:workflow --all --output=/tmp/ccs_existing.json' >/dev/null 2>&1 || true
if [ -s /tmp/ccs_existing.json ]; then
  python3 - <<'PYEOF' > /tmp/ccs_old_ids.txt
import json
try:
    data = json.load(open("/tmp/ccs_existing.json"))
    for wf in (data if isinstance(data, list) else [data]):
        if str(wf.get("name", "")).strip()[:2] in ("01", "02", "03", "04", "05"):
            print(wf.get("id", ""))
except Exception:
    pass
PYEOF
  while read -r OID; do
    [ -n "$OID" ] && runuser -u ccs -- bash -lc "n8n delete:workflow --id=$OID" >/dev/null 2>&1
  done </tmp/ccs_old_ids.txt
fi
for WF in "$KIT"/n8n/*.json; do
  runuser -u ccs -- bash -lc "n8n import:workflow --input='$WF'" >/dev/null 2>&1 \
    && say "imported: $(basename "$WF")" || fail "import $(basename "$WF")"
done

# root helper scripts for the Windows scheduled tasks (fixed paths, no spaces)
cat > /root/ccs-keep.sh <<'EOF'
#!/bin/bash
exec bash /home/ccs/charm-city-sites/scripts/keep_alive_wsl.sh >> /home/ccs/charm-city-sites/factory/logs/keepalive.log 2>&1
EOF
cat > /root/ccs-hunt.sh <<'EOF'
#!/bin/bash
runuser -u ccs -- bash -lc 'cd /home/ccs/charm-city-sites && python3 scripts/scrape_leads.py' >> /home/ccs/charm-city-sites/factory/logs/scraper.log 2>&1
EOF
chmod +x /root/ccs-keep.sh /root/ccs-hunt.sh

# Windows Task Scheduler via WSL interop
SCH="/mnt/c/Windows/System32/schtasks.exe"
D="${WSL_DISTRO_NAME:-Ubuntu-24.04}"
if [ -x "$SCH" ]; then
  "$SCH" /Create /F /TN "Charm City Sites KeepAlive" /SC MINUTE /MO 5 /RU SYSTEM /RL HIGHEST \
    /TR "wsl.exe -d $D -u root bash /root/ccs-keep.sh" >/dev/null 2>&1 \
    && say "Heartbeat scheduled: self-heals the factory every 5 minutes." || fail "heartbeat scheduling"
  "$SCH" /Create /F /TN "Charm City Sites LeadHunt" /SC DAILY /ST 07:40 /RU SYSTEM /RL HIGHEST \
    /TR "wsl.exe -d $D -u root bash /root/ccs-hunt.sh" >/dev/null 2>&1 \
    && say "Lead hunt scheduled: daily at 07:40." || fail "hunt scheduling"
else
  say "Could not reach Windows Task Scheduler. Run these two commands later in an admin Command Prompt:"
  echo "    schtasks /Create /F /TN \"Charm City Sites KeepAlive\" /SC MINUTE /MO 5 /RU SYSTEM /RL HIGHEST /TR \"wsl.exe -d $D -u root bash /root/ccs-keep.sh\""
  echo "    schtasks /Create /F /TN \"Charm City Sites LeadHunt\" /SC DAILY /ST 07:40 /RU SYSTEM /RL HIGHEST /TR \"wsl.exe -d $D -u root bash /root/ccs-hunt.sh\""
fi

# ownership + wake everything up once
chown -R ccs:ccs "$KIT" 2>/dev/null
[ -d /home/ccs/freellmapi ] && chown -R ccs:ccs /home/ccs/freellmapi 2>/dev/null
bash /root/ccs-keep.sh

# ---------------------------------------------------------------- wrap up
step "INSTALL DONE - what happens next"
echo ""
echo "  1. n8n control panel: http://localhost:5678  (a browser should be opening)"
echo "     First visit: create the owner account - any email + password, stays on this laptop."
echo "  2. Grab the FreeLLMAPI key: open http://localhost:3001 in your browser,"
echo "     do its one-time dashboard login, open the Keys page, copy the unified key."
echo "  3. Paste that key into the secrets file with Windows Notepad:"
echo "     Notepad - File - Open - paste this into the file name box:"
echo "     \\\\wsl.localhost\\$D\\home\\ccs\\charm-city-sites\\factory\\env.sh"
echo "     ...and set LLM_API_KEY=yourkey  (Cloudflare token goes there too)."
echo "  4. Then open WINDOWS.md in the kit folder - the remaining one-time"
echo "     paste-ins, same as OPERATIONS.md Part 1, about 45 minutes, once."
echo ""
echo "  Keeping it alive: two invisible Windows tasks now guard the factory."
echo "  KeepAlive checks every 5 minutes; LeadHunt fires daily at 07:40."
echo "  Manual wake-up any time: double-click 'Start Factory (Windows).bat'."
echo ""
echo "=== WSL install finished $(date) ==="
