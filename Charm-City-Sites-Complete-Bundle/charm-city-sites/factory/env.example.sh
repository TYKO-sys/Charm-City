# Charm City Sites — secrets and endpoints. One file, plain KEY=value lines.
# Fill the empty ones after install. No quotes needed. Restart nothing;
# scripts read this file fresh every run.

# --- AI brain -----------------------------------------------------------
# FreeLLMAPI (menu-bar app on port 3001). Key comes from the tray popover.
LLM_BASE_URL=http://localhost:3001/v1
LLM_API_KEY=
# Model name; leave empty to let the router pick.
LLM_MODEL=

# Offline fallback (Ollama). Install.sh sets this up in the background.
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5:14b

# --- Cloudflare Pages (hosting) -----------------------------------------
# Create a free token: dash.cloudflare.com -> My Profile -> API Tokens
#   -> Create Token -> "Edit Cloudflare Pages" template -> copy here.
CLOUDFLARE_API_TOKEN=
CLOUDFLARE_ACCOUNT_ID=

# --- You -----------------------------------------------------------------
# Where alerts and pre-handoff form submissions go (your outreach Gmail).
OPERATOR_EMAIL=
# Footer byline on every site ("Site by Charm City Sites" -> mailto this).
BUILDER_EMAIL=
