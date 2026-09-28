#!/bin/bash
# Charm City Sites — one-command installer (macOS).
# Double-click "Install Factory.command" in Finder, or run:  bash install.sh
#
# What it does, in order:
#   1. Homebrew + node + python3 + git (skips whatever exists)
#   2. n8n + wrangler (npm, global)
#   3. FreeLLMAPI (macOS app from the official GitHub release; falls back to git)
#   4. Ollama + the offline fallback model (downloads in the background)
#   5. Wires the workflows to this folder, imports them into n8n
#   6. Installs launchd agents: n8n always-on + daily lead hunt 07:40
#   7. Asks ONE optional question (your Google Sheet URL), prints next steps
#
# Safe to run again. Re-running refreshes workflows without duplicating them.

set -uo pipefail

KIT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$KIT_DIR/factory/logs/install.log"
mkdir -p "$KIT_DIR/factory/logs"
exec >>"$LOG" 2>&1   # everything also lands in the log; console gets the highlights too
step() { echo ""; echo "==> $*"; }
say()  { echo "    $*"; }
fail() { echo "    !! $* (install continues; check install.log)"; }

echo "=== Charm City Sites install started $(date) ==="
[ "$(uname)" = "Darwin" ] || say "Not macOS - some steps (Homebrew, launchd, dmg) will be skipped."

# ---------------------------------------------------------------- 1. base tools
step "1/6 Base tools (Homebrew, node, python3, git)"
if [ "$(uname)" = "Darwin" ] && ! command -v brew >/dev/null 2>&1; then
  say "Installing Homebrew (one time, ~2 min)..."
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" \
    || fail "Homebrew install failed"
  [ -x /opt/homebrew/bin/brew ] && eval "$(/opt/homebrew/bin/brew shellenv)"
  [ -x /usr/local/bin/brew ] && eval "$(/usr/local/bin/brew shellenv)"
fi
command -v brew >/dev/null 2>&1 && say "Homebrew: present"
if command -v brew >/dev/null 2>&1; then
  for pkg in node python@3.12 git; do
    brew list --formula "$pkg" >/dev/null 2>&1 || { say "brew install $pkg..."; brew install "$pkg" || fail "$pkg"; }
  done
fi
command -v node >/dev/null 2>&1 && say "node: $(node --version)" || fail "node missing - install manually, then re-run"
command -v python3 >/dev/null 2>&1 && say "python3: $(python3 --version)" || fail "python3 missing"

# ---------------------------------------------------------------- 2. n8n + wrangler
step "2/6 n8n + wrangler (npm global, ~3 min first time)"
command -v n8n >/dev/null 2>&1 || npm install -g n8n --no-audit --no-fund || fail "n8n install failed"
command -v wrangler >/dev/null 2>&1 || npm install -g wrangler --no-audit --no-fund || fail "wrangler install failed"
say "n8n: $(n8n --version 2>/dev/null || echo 'installed') | wrangler: present"

# ---------------------------------------------------------------- 3. FreeLLMAPI
step "3/6 FreeLLMAPI (the AI brain, port 3001)"
if [ "$(uname)" = "Darwin" ]; then
  APP_PATH=$(ls -d /Applications/FreeLLMAPI.app /Applications/Free*.app 2>/dev/null | head -1 || true)
  if [ -z "$APP_PATH" ]; then
    say "Downloading the official macOS app from GitHub releases..."
    DMG_URL=$(curl -fsSL --max-time 30 "https://api.github.com/repos/tashfeenahmed/freellmapi/releases/latest" 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(next((a['browser_download_url'] for a in d.get('assets', []) if a['name'].lower().endswith('.dmg')), ''))
except Exception:
    print('')" 2>/dev/null || echo "")
    if [ -n "$DMG_URL" ]; then
      curl -fSL --max-time 300 "$DMG_URL" -o /tmp/freellmapi.dmg \
        && hdiutil attach -nobrowse -readonly /tmp/freellmapi.dmg -mountpoint /tmp/freellmapi_mnt >/dev/null \
        && cp -R /tmp/freellmapi_mnt/*.app /Applications/ 2>/dev/null
      hdiutil detach /tmp/freellmapi_mnt >/dev/null 2>&1 || true
      rm -f /tmp/freellmapi.dmg
    fi
    APP_PATH=$(ls -d /Applications/Free*.app 2>/dev/null | head -1 || true)
  fi
  if [ -n "$APP_PATH" ]; then
    say "App present: $APP_PATH (launching it now - it lives in your menu bar)"
    open "$APP_PATH" 2>/dev/null || true
  else
    say "App download did not land; using the git fallback."
  fi
fi
if ! ls -d /Applications/Free*.app >/dev/null 2>&1 && [ ! -d "$HOME/freellmapi" ]; then
  git clone --depth 1 https://github.com/tashfeenahmed/freellmapi.git "$HOME/freellmapi" 2>/dev/null \
    && (cd "$HOME/freellmapi" && npm install --no-audit --no-fund >/dev/null 2>&1) \
    || fail "FreeLLMAPI git fallback did not finish"
fi

# ---------------------------------------------------------------- 4. Ollama
step "4/6 Ollama (offline brain - optional but nice)"
if command -v brew >/dev/null 2>&1; then
  brew list --cask ollama >/dev/null 2>&1 || brew install --cask ollama >/dev/null 2>&1 || fail "ollama cask"
fi
if command -v ollama >/dev/null 2>&1; then
  (curl -sf --max-time 3 http://localhost:11434/api/tags >/dev/null 2>&1) || (open -a Ollama 2>/dev/null || ollama serve >/dev/null 2>&1 &)
  say "Ollama up. Background-downloading the fallback model (9 GB, only used when offline)..."
  nohup ollama pull qwen2.5:14b >>"$KIT_DIR/factory/logs/ollama_pull.log" 2>&1 &
else
  say "Ollama not installed - fine, FreeLLMAPI is the primary brain."
fi

# ---------------------------------------------------------------- 5. wire + import workflows
step "5/6 Personalize and import the 5 workflows"
echo "Optional: paste your Google Sheet URL to auto-wire every workflow."
echo "   (From the sheet's address bar, e.g. https://docs.google.com/spreadsheets/d/ABC123...)"
printf "   Paste it here, or just press Enter to skip: "
read -r SHEET_URL </dev/tty
SHEET_ID=$(printf '%s' "$SHEET_URL" | python3 -c "
import re, sys
m = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', sys.stdin.read() or '')
print(m.group(1) if m else '')" 2>/dev/null || echo "")
[ -n "$SHEET_ID" ] && say "Sheet id captured: $SHEET_ID" || say "No sheet given - pick it manually in n8n later (see OPERATIONS.md)."

python3 - "$KIT_DIR" "$SHEET_ID" <<'PYEOF'
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

# Remove older imports of the same workflows so re-runs never duplicate
n8n export:workflow --all --output=/tmp/ccs_existing.json >/dev/null 2>&1 || true
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
    [ -n "$OID" ] && n8n delete:workflow --id="$OID" >/dev/null 2>&1
  done </tmp/ccs_old_ids.txt
fi
for WF in "$KIT_DIR"/n8n/*.json; do
  n8n import:workflow --input="$WF" >/dev/null 2>&1 && say "imported: $(basename "$WF")" || fail "import $(basename "$WF")"
done

# ---------------------------------------------------------------- 6. launchd agents
step "6/6 Keep it running (launchd agents)"
if [ "$(uname)" = "Darwin" ]; then
  AGENTS="$HOME/Library/LaunchAgents"; mkdir -p "$AGENTS"
  cat > "$AGENTS/com.charmcitysites.n8n.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.charmcitysites.n8n</string>
  <key>ProgramArguments</key><array>
    <string>$(command -v n8n || echo /opt/homebrew/bin/n8n)</string>
    <string>start</string>
  </array>
  <key>EnvironmentVariables</key><dict>
    <key>N8N_SECURE_COOKIE</key><string>false</string>
    <key>N8N_DIAGNOSTICS_ENABLED</key><string>false</string>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$KIT_DIR/factory/logs/n8n.log</string>
  <key>StandardErrorPath</key><string>$KIT_DIR/factory/logs/n8n.log</string>
</dict></plist>
PLIST
  cat > "$AGENTS/com.charmcitysites.scraper.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.charmcitysites.scraper</string>
  <key>ProgramArguments</key><array>
    <string>$(command -v python3 || echo /usr/bin/python3)</string>
    <string>$KIT_DIR/scripts/scrape_leads.py</string>
  </array>
  <key>StartCalendarInterval</key><dict>
    <key>Hour</key><integer>7</integer>
    <key>Minute</key><integer>40</integer>
  </dict>
  <key>StandardOutPath</key><string>$KIT_DIR/factory/logs/scraper.log</string>
  <key>StandardErrorPath</key><string>$KIT_DIR/factory/logs/scraper.log</string>
</dict></plist>
PLIST
  UID_NUM=$(id -u)
  for LABEL in n8n scraper; do
    launchctl bootout "gui/$UID_NUM/$LABEL.com.charmcitysites.$LABEL" >/dev/null 2>&1
    launchctl bootout "gui/$UID_NUM/com.charmcitysites.$LABEL" >/dev/null 2>&1
    launchctl bootstrap "gui/$UID_NUM" "$AGENTS/com.charmcitysites.$LABEL.plist" >/dev/null 2>&1 \
      || launchctl load -w "$AGENTS/com.charmcitysites.$LABEL.plist" >/dev/null 2>&1 \
      || fail "launchd agent $LABEL"
  done
  say "n8n stays on (restarts with your Mac). Lead hunt runs daily at 07:40."
else
  say "Not macOS - start n8n manually with: n8n start"
fi

# ---------------------------------------------------------------- wrap up
chmod +x "$KIT_DIR/scripts/"*.sh "$KIT_DIR/scripts/"*.py 2>/dev/null || true
[ -f "$KIT_DIR/factory/env.sh" ] || cp "$KIT_DIR/factory/env.example.sh" "$KIT_DIR/factory/env.sh"

step "INSTALL DONE - what happens next"
echo ""
echo "  1. n8n control panel: http://localhost:5678"
echo "     First visit: make a owner account (any email + password, stays local)."
echo "  2. The 5 workflows are imported. Open each, connect the 3 credentials"
echo "     (Google, Telegram, Email) - exact clicks in OPERATIONS.md, one time."
echo "  3. Copy the FreeLLMAPI key from the menu-bar app popover into"
echo "     factory/env.sh (line LLM_API_KEY=...)."
echo "  4. Cloudflare token goes into factory/env.sh too - OPERATIONS.md has the"
echo "     3-minute path."
echo ""
echo "  Full walkthrough: OPERATIONS.md in this folder."
echo "  Health check any time: double-click 'Open Dashboard.command'."
echo ""
echo "=== install finished $(date) ==="
