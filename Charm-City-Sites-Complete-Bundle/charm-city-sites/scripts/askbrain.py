#!/usr/bin/env python3
"""Charm City Sites — one-shot LLM call for n8n.

Reads {"system": "...", "user": "...", "max_tokens": N} from stdin.
Prints {"ok": true, "text": "...", "source": "freellmapi|ollama"} or
{"ok": false, "error": "..."} on stdout. Callers fall back to their own
template text when ok is false.

Usage:  echo '{"system":"...","user":"..."}' | python3 askbrain.py --stdin
"""
import argparse
import json
import sys

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from ccs_common import chat, load_env, log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--system", default="You write tight, plain-English marketing copy. No hype, no emojis.")
    ap.add_argument("--user", required=False)
    ap.add_argument("--max-tokens", type=int, default=700)
    args = ap.parse_args()

    if args.stdin:
        data = json.loads(sys.stdin.read())
    else:
        data = {"system": args.system, "user": args.user or ""}

    messages = [
        {"role": "system", "content": str(data.get("system") or args.system)},
        {"role": "user", "content": str(data.get("user") or "")},
    ]
    env = load_env()
    max_tokens = int(data.get("max_tokens") or args.max_tokens)

    if env.get("LLM_BASE_URL"):
        try:
            text = chat(env["LLM_BASE_URL"], env.get("LLM_MODEL", ""), messages,
                        api_key=env.get("LLM_API_KEY", ""), timeout=90, max_tokens=max_tokens)
            print(json.dumps({"ok": True, "text": text, "source": "freellmapi"}))
            return
        except Exception as exc:
            log("askbrain freellmapi failed: %r" % exc)
    try:
        text = chat(env.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                    env.get("OLLAMA_MODEL", "qwen2.5:14b"), messages,
                    timeout=240, max_tokens=max_tokens)
        print(json.dumps({"ok": True, "text": text, "source": "ollama"}))
        return
    except Exception as exc:
        log("askbrain ollama failed: %r" % exc)
    print(json.dumps({"ok": False, "error": "no llm reachable"}))


if __name__ == "__main__":
    main()
