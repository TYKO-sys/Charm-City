"""Shared helpers for Charm City Sites scripts. No third-party deps, ever."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FACTORY_DIR = os.path.normpath(os.path.join(HERE, ".."))
SITES_DIR = os.path.join(FACTORY_DIR, "factory", "sites")
INBOX_DIR = os.path.join(FACTORY_DIR, "factory", "leads_inbox")
LOGS_DIR = os.path.join(FACTORY_DIR, "factory", "logs")
TEMPLATE_DIR = os.path.join(FACTORY_DIR, "site-template")


def load_env():
    """Parse factory/env.sh (KEY=value lines) without executing shell."""
    env = {
        "LLM_BASE_URL": "http://localhost:3001/v1",
        "LLM_API_KEY": "",
        "LLM_MODEL": "",
        "OLLAMA_BASE_URL": "http://localhost:11434/v1",
        "OLLAMA_MODEL": "qwen2.5:14b",
        "BUILDER_EMAIL": "",
        "CLOUDFLARE_API_TOKEN": "",
        "CLOUDFLARE_ACCOUNT_ID": "",
        "OPERATOR_EMAIL": "",
    }
    path = os.path.join(FACTORY_DIR, "factory", "env.sh")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.replace("export ", "").strip()
                val = val.strip().strip('"').strip("'")
                if key:
                    env[key] = val
    except FileNotFoundError:
        pass
    return env


def log(msg):
    sys.stderr.write("[ccs] %s\n" % msg)
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        with open(os.path.join(LOGS_DIR, "generate.log"), "a", encoding="utf-8") as fh:
            fh.write(msg + "\n")
    except OSError:
        pass


def norm_phone(raw):
    """Return (href, display). href like tel:+14105550199, display like (410) 555-0199."""
    digits = re.sub(r"\D", "", str(raw or ""))
    if len(digits) == 10:
        digits = "1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        href = "tel:+" + digits
        disp = "(%s) %s-%s" % (digits[1:4], digits[4:7], digits[7:11])
        return href, disp
    if digits:
        return "tel:+" + digits, str(raw)
    return "", str(raw or "")


def slugify(name, max_len=28):
    s = str(name or "").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    while len(s) > max_len and "-" in s[: max_len + 1]:
        s = s[: s.rfind("-", 0, max_len + 1)]
    s = s[:max_len].strip("-")
    return s or "site"


def unique_slug(base, sites_dir):
    """PRD edge case: slug collision -> append -2, -3, ..."""
    slug, n = base, 1
    while os.path.exists(os.path.join(sites_dir, slug)):
        n += 1
        slug = "%s-%d" % (base, n)
    return slug


def http_post_json(url, payload, timeout=90, bearer=""):
    """Minimal JSON POST using only the standard library."""
    import urllib.request
    import urllib.error

    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def chat(base_url, model, messages, api_key="", timeout=90, max_tokens=1600):
    """One OpenAI-compatible chat call. Returns assistant text or raises."""
    payload = {
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }
    if model:
        payload["model"] = model
    out = http_post_json(base_url.rstrip("/") + "/chat/completions", payload,
                         timeout=timeout, bearer=api_key)
    return out["choices"][0]["message"]["content"]


def extract_json(text):
    """Pull the first JSON object out of an LLM answer (handles code fences)."""
    text = re.sub(r"```(?:json)?", "", str(text or ""))
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start : end + 1])
