#!/bin/bash
# Charm City Sites — self-healing heartbeat for WSL (Windows laptops).
# Windows Task Scheduler runs this every 5 minutes as root; you can also
# run it any time via "Start Factory (Windows).bat".
# It only STARTS things that are down. It never stops anything, and it
# always exits 0 so the scheduler never complains.

KIT=/home/ccs/charm-city-sites
U=ccs
mkdir -p "$KIT/factory/logs"

# --- 1. Docker (carries FreeLLMAPI) ---
if ! docker info >/dev/null 2>&1; then
  if [ -d /run/systemd/system ]; then
    systemctl start docker >/dev/null 2>&1 || true
  else
    service docker start >/dev/null 2>&1 || true
  fi
fi
for _ in $(seq 1 20); do
  docker info >/dev/null 2>&1 && break
  sleep 1
done

# --- 2. FreeLLMAPI container (any name containing "freellm") ---
if docker info >/dev/null 2>&1; then
  CN="$(docker ps -a --format '{{.Names}}' 2>/dev/null | grep -i freellm | head -1)"
  if [ -n "$CN" ]; then
    if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$CN"; then
      docker start "$CN" >/dev/null 2>&1 || true
    fi
  fi
fi

# --- 3. Ollama (offline fallback brain) ---
runuser -u "$U" -- bash -lc 'pgrep -x ollama >/dev/null 2>&1 || nohup ollama serve > $HOME/.ollama_serve.log 2>&1 &' 2>/dev/null || true

# --- 4. n8n (the spine) with the right timezone + cookie settings ---
runuser -u "$U" -- bash -lc 'pgrep -f "[n]8n start" >/dev/null 2>&1 || (cd $HOME/charm-city-sites && nohup env TZ=America/New_York GENERIC_TIMEZONE=America/New_York N8N_SECURE_COOKIE=false N8N_DIAGNOSTICS_ENABLED=false n8n start >> factory/logs/n8n.log 2>&1 &)' 2>/dev/null || true

exit 0
