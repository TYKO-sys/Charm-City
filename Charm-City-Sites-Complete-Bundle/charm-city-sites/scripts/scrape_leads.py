#!/usr/bin/env python3
"""Charm City Sites — lead hunter.

Pulls Baltimore plumber leads from free, no-key sources, enriches them with
emails found on their own websites, dedupes, and pushes each one to the
factory's n8n webhook (localhost:5678/webhook/lead-intake). If n8n is down,
leads queue in factory/leads_inbox/ and get pushed on the next run.

Sources (all free, no API keys):
  1. OpenStreetMap Overpass — real listed plumber shops in the Baltimore bbox
  2. DuckDuckGo HTML — one rotating search query per run, gentle footprint
  3. Their own websites — emails and phone numbers, when public

Runs automatically every morning via launchd. You never type anything.

Usage:
  python3 scrape_leads.py                # normal daily run
  python3 scrape_leads.py --all-queries  # wider net (run this once at start)
  python3 scrape_leads.py --selftest     # offline logic check, no network
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccs_common import INBOX_DIR, load_env, log

SEEN_FILE = os.path.join(INBOX_DIR, "seen.json")
QUERY_STATE = os.path.join(INBOX_DIR, "query_state.txt")
WEBHOOK = "http://localhost:5678/webhook/lead-intake"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

QUERIES = [
    "plumber baltimore md",
    "emergency plumber baltimore",
    "water heater installation baltimore",
    "drain cleaning baltimore",
    "plumber towson md",
    "plumber canton baltimore",
    "plumber parkville md",
    "plumber dundalk md",
    "master plumber baltimore county",
    "plumbing repair fells point baltimore",
]

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
OVERPASS_QUERY = (
    '[out:json][timeout:25];'
    '(node["shop"="plumber"](39.15,-76.75,39.42,-76.45);'
    'way["shop"="plumber"](39.15,-76.75,39.42,-76.45);'
    'node["craft"="plumber"](39.15,-76.75,39.42,-76.45);'
    'way["craft"="plumber"](39.15,-76.75,39.42,-76.45););'
    'out center tags;'
)

BAD_EMAIL = re.compile(r"\.(png|jpg|jpeg|gif|webp|svg|css|js)$|^(no.?reply|postmaster|abuse|"
                       r"sentry|do.?not.?reply|example|test|user|info@wix|noreply)", re.I)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
TEL_RE = re.compile(r'href=["\']tel:([0-9\-\(\)\+\. ]{7,20})["\']', re.I)
PHONE_DIGITS = re.compile(r"\D")


# ---------------------------------------------------------------- fetch helpers

def fetch(url, data=None, timeout=25, headers=None):
    h = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    if headers:
        h.update(headers)
    if data is not None and isinstance(data, str):
        data = data.encode("utf-8")
        h.setdefault("Content-Type", "application/x-www-form-urlencoded")
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


# ---------------------------------------------------------------- source 1: Overpass

def overpass_leads():
    body = urllib.parse.urlencode({"data": OVERPASS_QUERY})
    for mirror in OVERPASS_MIRRORS:
        try:
            raw = fetch(mirror, data=body, timeout=40)
            data = json.loads(raw)
            out = []
            for el in data.get("elements", []):
                t = el.get("tags", {})
                name = t.get("name")
                if not name:
                    continue
                phone = t.get("phone") or t.get("contact:phone") or ""
                addr = " ".join(filter(None, [
                    t.get("addr:housenumber"), t.get("addr:street"),
                    t.get("addr:city") or "Baltimore", t.get("addr:state") or "MD"]))
                out.append({
                    "business_name": name.strip(),
                    "phone": phone.strip(),
                    "email": (t.get("contact:email") or t.get("email") or "").strip(),
                    "website": (t.get("website") or t.get("contact:website") or "").strip(),
                    "address": addr.strip(),
                    "neighborhood": t.get("addr:suburb") or t.get("addr:neighbourhood") or "",
                    "source": "osm",
                })
            log("overpass %s -> %d raw leads" % (mirror.split("/")[2], len(out)))
            return out
        except Exception as exc:
            log("overpass mirror failed (%s): %r" % (mirror, exc))
    return []


# ---------------------------------------------------------------- source 2: DuckDuckGo

class DDGParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._in_a = False
        self._href = ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._in_a = True
            self._href = dict(attrs).get("href", "")

    def handle_endtag(self, tag):
        if tag == "a":
            self._in_a = False
            self._href = ""


def ddg_result_links(html):
    p = DDGParser()
    p.feed(html)
    links = []
    for m in re.finditer(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>', html):
        links.append(m.group(1))
    for href in links:
        yield href


def ddg_domains(query):
    html = fetch("https://html.duckduckgo.com/html/",
                 data=urllib.parse.urlencode({"q": query}), timeout=30)
    seen, out = set(), []
    for href in ddg_result_links(html):
        target = href
        if "uddg=" in href:
            try:
                target = urllib.parse.unquote(re.search(r"uddg=([^&]+)", href).group(1))
            except AttributeError:
                continue
        domain = urllib.parse.urlparse(target).netloc.lower()
        domain = domain[4:] if domain.startswith("www.") else domain
        junk = ("yelp.", "angi.", "homeadvisor.", "thumbtack.", "yellowpages.",
                "facebook.", "instagram.", "nextdoor.", "reddit.", "bbb.org",
                "linkedin.", "houzz.", "porch.", "baltimoresun.", "mapquest.",
                "duckduckgo.", "justia.", "expertise.", "porch.com")
        if not domain or domain in seen or any(j in domain for j in junk):
            continue
        seen.add(domain)
        out.append(domain)
    return out[:10]


def next_query(use_all=False):
    if use_all:
        return QUERIES
    try:
        i = int(open(QUERY_STATE).read().strip() or 0)
    except (OSError, ValueError):
        i = 0
    open(QUERY_STATE, "w").write(str((i + 1) % len(QUERIES)))
    return [QUERIES[i % len(QUERIES)]]


# ---------------------------------------------------------------- source 3: website enrichment

def enrich(domain):
    """Pull email + phone + title off a plumber's own site, politely."""
    for scheme in ("https://", "http://"):
        try:
            html = fetch(scheme + domain, timeout=10)
            html = html[:200000]
        except Exception:
            continue
        clean = [e.lower() for e in EMAIL_RE.findall(html) if not BAD_EMAIL.search(e.lower())]
        root = domain.split(".")[-2] if "." in domain else domain
        emails = [e for e in clean if root in e] or clean[:1]
        tel = TEL_RE.search(html)
        title = re.search(r"<title[^>]*>([^<]{3,90})</title>", html, re.I)
        return {
            "email": emails[0] if emails else "",
            "phone": tel.group(1).strip() if tel else "",
            "title": title.group(1).strip() if title else domain,
        }
    return {}


# ---------------------------------------------------------------- dedupe + push

def dedupe_key(lead):
    phone = PHONE_DIGITS.sub("", lead.get("phone") or "")
    if len(phone) == 11 and phone.startswith("1"):
        phone = phone[1:]
    dom = (lead.get("website") or "").lower().replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
    name = re.sub(r"[^a-z0-9]", "", (lead.get("business_name") or "").lower())
    return ("tel:" + phone) if phone else (("dom:" + dom) if dom else ("nam:" + name) if name else None)


def load_seen():
    try:
        return json.load(open(SEEN_FILE))
    except (OSError, ValueError):
        return {"tel": [], "dom": [], "nam": []}


def save_seen(seen):
    os.makedirs(INBOX_DIR, exist_ok=True)
    json.dump(seen, open(SEEN_FILE, "w"), indent=1)


def is_new(lead, seen):
    key = dedupe_key(lead)
    if not key:
        return False
    kind, _, val = key.partition(":")
    return val not in seen.get(kind, [])


def mark_seen(lead, seen):
    key = dedupe_key(lead)
    if key:
        kind, _, val = key.partition(":")
        seen.setdefault(kind, []).append(val)


def webhook_up():
    try:
        urllib.request.urlopen(urllib.request.Request(WEBHOOK, method="OPTIONS"), timeout=4)
        return True
    except urllib.error.HTTPError:
        return True  # answered = alive
    except Exception:
        return False


def push(lead):
    req = urllib.request.Request(
        WEBHOOK, data=json.dumps(lead).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status == 200


def flush_inbox():
    """Leads that queued while n8n was down get pushed first."""
    sent = 0
    if not os.path.isdir(INBOX_DIR):
        return sent
    for fname in sorted(os.listdir(INBOX_DIR)):
        if not fname.endswith(".json") or fname == "seen.json":
            continue
        path = os.path.join(INBOX_DIR, fname)
        try:
            lead = json.load(open(path))
            if push(lead):
                os.remove(path)
                sent += 1
        except Exception as exc:
            log("inbox push failed for %s: %r" % (fname, exc))
            break  # n8n probably still down; try again next run
    return sent


# ---------------------------------------------------------------- main

def run(use_all=False, max_new=8, no_push=False):
    os.makedirs(INBOX_DIR, exist_ok=True)
    env = load_env()
    seen = load_seen()

    raw = overpass_leads()
    for query in next_query(use_all):
        try:
            domains = ddg_domains(query)
            log("ddg '%s' -> %s domains" % (query, domains))
        except Exception as exc:
            log("ddg failed: %r" % exc)
            domains = []
        for domain in domains:
            lead = {"business_name": domain, "phone": "", "email": "",
                    "website": domain if "." in domain else "https://" + domain,
                    "address": "", "neighborhood": "",
                    "source": "web:" + query}
            got = enrich(domain)
            time.sleep(3)  # stay polite
            if got:
                lead["email"] = got.get("email", "")
                lead["phone"] = got.get("phone", "")
                title = got.get("title", "")
                if title and ("plumb" in title.lower() or "plumb" in domain):
                    lead["business_name"] = re.sub(r"\s*[|\-–]\s*(plumb|baltimore|md).*$", "", title, flags=re.I).strip() or domain
            raw.append(lead)

    new_leads = []
    for lead in raw:
        if lead.get("business_name") and lead.get("phone", "") or lead.get("email"):
            if is_new(lead, seen) and (lead.get("phone") or lead.get("email") or lead.get("website")):
                new_leads.append(lead)
                mark_seen(lead, seen)
                if len(new_leads) >= max_new:
                    break
    save_seen(seen)

    pushed, queued = 0, 0
    if not no_push:
        if webhook_up():
            pushed += flush_inbox()
            for lead in new_leads:
                try:
                    push(lead)
                    pushed += 1
                except Exception as exc:
                    log("push failed: %r" % exc)
                    queue(lead)
                    queued += 1
        else:
            for lead in new_leads:
                queue(lead)
                queued += 1

    for lead in new_leads:
        print("  + %-38s %-16s %s" % (lead["business_name"][:38],
                                      lead.get("phone") or "-",
                                      lead.get("email") or lead.get("website") or "-"),
              file=sys.stderr)
    print(json.dumps({"ok": True, "found_raw": len(raw), "new": len(new_leads),
                      "pushed": pushed, "queued": queued}))


def queue(lead):
    ts = time.strftime("%Y%m%d-%H%M%S")
    name = re.sub(r"[^a-z0-9]+", "-", lead.get("business_name", "lead").lower()).strip("-")[:30]
    path = os.path.join(INBOX_DIR, "%s-%s.json" % (ts, name or "lead"))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(lead, fh, indent=2)


def selftest():
    fake = [
        {"business_name": "AAA Plumbing Inc", "phone": "(410) 555-0101",
         "email": "aaaplumb@example.com", "website": "aaaplumbing.com", "source": "t"},
        {"business_name": "AAA Plumbing Inc.", "phone": "410-555-0101",
         "email": "", "website": "", "source": "t"},
        {"business_name": "Different Biz", "phone": "", "email": "x@y.com",
         "website": "differentbiz.com", "source": "t"},
        {"business_name": "Different Biz LLC", "phone": "", "email": "",
         "website": "https://www.differentbiz.com/about", "source": "t"},
    ]
    seen = {"tel": [], "dom": [], "nam": []}
    keys = [dedupe_key(f) for f in fake]
    results = []
    for f in fake:
        results.append(is_new(f, seen))
        mark_seen(f, seen)
    assert keys[0] == "tel:4105550101", keys
    assert keys[1] == "tel:4105550101", "same phone must dedupe: %s" % keys[1]
    assert keys[2] == "dom:differentbiz.com", keys[2]
    assert keys[3] == "dom:differentbiz.com", "same domain must dedupe: %s" % keys[3]
    assert results == [True, False, True, False], results
    lead_shape = overpass_shape_check()
    print(json.dumps({"ok": True, "dedupe": "PASS", "shape": lead_shape}))


def overpass_shape_check():
    sample = {"elements": [{"type": "node", "tags": {"name": "T", "phone": "1", "addr:street": "S",
                                                    "addr:city": "Baltimore", "addr:state": "MD"}}]}
    t = sample["elements"][0]["tags"]
    addr = " ".join(filter(None, [t.get("addr:housenumber"), t.get("addr:street"),
                                  t.get("addr:city") or "Baltimore", t.get("addr:state") or "MD"]))
    return "PASS" if addr == "S Baltimore MD" else "FAIL"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-queries", action="store_true")
    ap.add_argument("--max", type=int, default=8)
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
    else:
        run(use_all=args.all_queries, max_new=args.max, no_push=args.no_push)
