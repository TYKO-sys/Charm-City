#!/usr/bin/env python3
"""Charm City Sites — site generator.

Input : a lead row (JSON via --stdin / --data-file, or --demo).
Output: a complete static site in factory/sites/<slug>/ ready to deploy.

Copy chain (PRD): FreeLLMAPI -> Ollama -> built-in default copy.
Whatever breaks, a site still comes out the other end, and the row gets
flagged needs_rewrite instead of the pipeline stalling.

Usage:
  echo '<lead json>' | python3 generate_site.py --stdin
  python3 generate_site.py --data-file lead.json
  python3 generate_site.py --demo
  python3 generate_site.py --data-file sites/x/lead.json --form-email client@x.com
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccs_common import (FACTORY_DIR, SITES_DIR, TEMPLATE_DIR, chat, extract_json,
                        load_env, log, norm_phone, slugify, unique_slug)

# ---------------------------------------------------------------- palettes

PALETTES = [
    {"INK": "#0E2A47", "INK_DEEP": "#081A2F", "ACCENT": "#F97316", "ACCENT_SOFT": "#FFD9B8"},
    {"INK": "#123A3A", "INK_DEEP": "#0A2424", "ACCENT": "#E8A020", "ACCENT_SOFT": "#FFE3AE"},
    {"INK": "#1C2E4A", "INK_DEEP": "#101C33", "ACCENT": "#2F80ED", "ACCENT_SOFT": "#BFDBFE"},
    {"INK": "#1F3A2A", "INK_DEEP": "#122619", "ACCENT": "#E8632B", "ACCENT_SOFT": "#FFD3C0"},
]

ICONS = {
    "droplet": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.7s6.5 7 6.5 11.3a6.5 6.5 0 0 1-13 0C5.5 9.7 12 2.7 12 2.7z"/></svg>',
    "drain":   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M8 8l8 8M16 8l-8 8"/></svg>',
    "flame":   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2c1 4-4 5.5-4 10a4 4 0 0 0 8 0c0-1.5-.7-2.6-1.5-3.5C13.6 10.5 12 9 12 2z"/></svg>',
    "wrench":  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a4.5 4.5 0 0 0-6 6L3 18l3 3 5.7-5.7a4.5 4.5 0 0 0 6-6L14 12l-2-2 2.7-3.7z"/></svg>',
    "pipes":   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h6v4h4V6h6M4 18h6v-4h4v4h6"/></svg>',
    "camera":  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 8l6-3 2 3h12v11H2z"/><circle cx="12" cy="14" r="3"/></svg>',
}

BALTIMORE_AREAS = ["Canton", "Fells Point", "Federal Hill", "Hampden", "Roland Park",
                   "Towson", "Parkville", "Dundalk", "Pigtown", "Mount Vernon",
                   "Charles Village", "Locust Point", "Highlandtown", "Cedarcroft"]

DEMO_LEAD = {
    "id": "demo-001",
    "business_name": "Bayview Plumbing Co.",
    "phone": "(410) 555-0142",
    "email": "",
    "neighborhood": "Canton",
    "address": "Canton waterfront, Baltimore, MD 21224",
    "years": "15",
    "source": "demo",
    "notes": "DEMO SITE - fictional business built to show plumbers what they get.",
}

PROMPT_SYSTEM = (
    "You write tight, credible website copy for local home-service businesses in Baltimore, Maryland. "
    "Plain words a tradesperson would actually say. No hype, no exclamation marks, no emojis. "
    "Reply with ONE valid JSON object and nothing else. Schema: "
    '{"tagline": string (max 90 chars), "meta_description": string (max 155 chars), '
    '"about": string[2] (two paragraphs, 2-4 sentences each), '
    '"services": [{"title": string, "desc": string (1-2 sentences), "price_from": string like "from $120"}] (exactly 6), '
    '"faq": [{"q": string, "a": string (1-2 sentences)}] (exactly 5), '
    '"reviews": [{"name": first name + last initial, "area": Baltimore neighborhood, "text": 1-2 sentences}] (exactly 3)}'
)

# ---------------------------------------------------------------- fallback copy

def fallback_services():
    return [
        {"title": "Emergency repairs", "desc": "Burst pipes, active leaks, no water at all. We drop what we're doing and get to you first.", "price_from": "from $120", "icon": "droplet"},
        {"title": "Drain cleaning", "desc": "Slow drains, standing water, gunk in the line. Cleared properly, not just pushed further down.", "price_from": "from $99", "icon": "drain"},
        {"title": "Water heaters", "desc": "Repair or replace, tank or tankless. Cold showers end today, and we haul the old unit away.", "price_from": "from $150", "icon": "flame"},
        {"title": "Toilets & faucets", "desc": "Running toilets, dripping faucets, bad seals. Small jobs done right, priced before we start.", "price_from": "from $110", "icon": "wrench"},
        {"title": "Repiping & pipe repair", "desc": "Old galvanized or copper that's given up. We repipe sections or whole homes with minimal wall damage.", "price_from": "from $350", "icon": "pipes"},
        {"title": "Sewer line & camera", "desc": "Camera down the line so we both see the problem. Root cutting, spot repair, and honest advice.", "price_from": "from $180", "icon": "camera"},
    ]


def clip(s, n):
    """Trim to n chars without cutting a word in half."""
    s = str(s or "").strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(",;:.-")


def fallback_copy(lead):
    name = lead.get("business_name") or "your local plumber"
    hood = lead.get("neighborhood") or "Baltimore"
    years = lead.get("years") or ""
    tag = "Licensed plumber in %s. We answer the phone, show up, and quote before work starts." % hood
    meta = "%s: licensed plumber in %s, Baltimore. 24/7 emergency repairs, drains, water heaters, repiping. Upfront pricing, same-day service." % (name, hood)
    about = [
        "%s has been working pipes around %s and the rest of Baltimore for %s. We're the outfit neighbors call when a drip turns into a flood at 11pm, because we pick up." % (name, hood, (years + " years") if years else "years"),
        "Every job gets a flat-rate quote before work starts. You'll never open an invoice and wonder where the number came from. Licensed, insured, and local enough that our truck is probably already in your neighborhood.",
    ]
    faq = [
        {"q": "Do you charge for estimates?", "a": "No. We look at the problem and give you a flat-rate price before any work starts. If you don't like the number, you owe nothing."},
        {"q": "How fast can you get here?", "a": "Most same-day. Real emergencies (active leaks, no water) get bumped to the front of the queue, including nights and weekends."},
        {"q": "Are you licensed and insured?", "a": "Yes. Fully licensed and insured, and we're happy to show the paperwork before we start any job on your home."},
        {"q": "What areas do you serve?", "a": "We're based in %s and cover Baltimore City and the close-in county neighborhoods. If you're unsure, call and ask." % hood},
        {"q": "What payment do you take?", "a": "Cash, check, and card. For bigger jobs we'll talk through payment before we begin so there are no surprises."},
    ]
    reviews = [
        {"name": "Marcus T.", "area": "Canton", "text": "Water heater died Sunday morning, they were here by noon and I had hot water before dinner. Price was exactly what they quoted on the phone."},
        {"name": "Dana R.", "area": "Federal Hill", "text": "Two other companies wanted to snake the same drain forever. They put a camera in, found the root, fixed it once. Honest people."},
        {"name": "Jerome W.", "area": "Parkville", "text": "Showed up on time, shoe covers on, cleaned up completely. Small job but they treated it like it mattered. They've got all my plumbing work now."},
    ]
    return {"tagline": clip(tag, 90), "meta_description": clip(meta, 155), "about": about,
            "services": fallback_services(), "faq": faq, "reviews": reviews}


def fallback_review_warning(reviews):
    return "<!-- SAMPLE REVIEWS: swap in the client's real reviews before handoff (see OPERATIONS.md) -->\n"


# ---------------------------------------------------------------- copy via LLM

def build_prompt_user(lead):
    facts = {
        "business_name": lead.get("business_name"),
        "neighborhood": lead.get("neighborhood") or "Baltimore",
        "city": "Baltimore, MD",
        "years_in_trade": lead.get("years") or "unknown",
        "notes": (lead.get("notes") or "")[:400],
        "trade": "plumbing (residential, light commercial)",
    }
    return ("Write website copy for this business. Facts:\n" + json.dumps(facts, indent=2) +
            "\nUse the 6 standard plumbing services (emergency repairs, drain cleaning, water heaters, "
            "toilets & faucets, repiping, sewer/camera) with realistic Baltimore 'from $' prices. "
            "Reviews are SAMPLE quotes written for a demo site; keep them modest and believable.")


def generate_copy(lead, env):
    """Returns (copy_dict, source) where source is freellmapi|ollama|default."""
    user_msg = build_prompt_user(lead)
    messages = [{"role": "system", "content": PROMPT_SYSTEM},
                {"role": "user", "content": user_msg}]
    # Tier 1: FreeLLMAPI router
    if env.get("LLM_BASE_URL"):
        try:
            text = chat(env["LLM_BASE_URL"], env.get("LLM_MODEL", ""), messages,
                        api_key=env.get("LLM_API_KEY", ""), timeout=120)
            copy = extract_json(text)
            copy.setdefault("services", [])
            for i, svc in enumerate(copy.get("services", [])):
                svc.setdefault("icon", fallback_services()[i]["icon"] if i < 6 else "wrench")
            return normalize_copy(copy, lead), "freellmapi"
        except Exception as exc:
            log("FreeLLMAPI tier failed: %r" % exc)
    # Tier 2: local Ollama
    try:
        text = chat(env.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                    env.get("OLLAMA_MODEL", "qwen2.5:14b"), messages, timeout=240)
        copy = extract_json(text)
        copy.setdefault("services", [])
        for i, svc in enumerate(copy.get("services", [])):
            svc.setdefault("icon", fallback_services()[i]["icon"] if i < 6 else "wrench")
        return normalize_copy(copy, lead), "ollama"
    except Exception as exc:
        log("Ollama tier failed: %r" % exc)
    # Tier 3: built-in defaults
    return fallback_copy(lead), "default"


def normalize_copy(copy, lead):
    """Guard-rail whatever the model returned so the renderer never crashes."""
    fix = clip
    svcs = []
    fallback = fallback_services()
    for i in range(6):
        src = copy.get("services", [{}] * 6)[i] if i < len(copy.get("services", [])) else {}
        fb = fallback[i]
        svcs.append({"title": fix(src.get("title"), 40) or fb["title"],
                     "desc": fix(src.get("desc"), 220) or fb["desc"],
                     "price_from": fix(src.get("price_from"), 18) or fb["price_from"],
                     "icon": src.get("icon") if src.get("icon") in ICONS else fb["icon"]})
    faqs = []
    for i in range(5):
        src = copy.get("faq", [{}] * 5)[i] if i < len(copy.get("faq", [])) else {}
        fb = fallback_copy(lead)["faq"][i]
        faqs.append({"q": fix(src.get("q"), 120) or fb["q"], "a": fix(src.get("a"), 300) or fb["a"]})
    revs = []
    for i in range(3):
        src = copy.get("reviews", [{}] * 3)[i] if i < len(copy.get("reviews", [])) else {}
        fb = fallback_copy(lead)["reviews"][i]
        revs.append({"name": fix(src.get("name"), 30) or fb["name"],
                     "area": fix(src.get("area"), 30) or fb["area"],
                     "text": fix(src.get("text"), 260) or fb["text"]})
    about = copy.get("about") or []
    if isinstance(about, str):
        about = [about]
    if not about:
        about = fallback_copy(lead)["about"]
    about = [fix(p, 700) for p in about[:3] if fix(p, 700)]
    if not about:
        about = fallback_copy(lead)["about"]
    return {"tagline": fix(copy.get("tagline"), 90) or fallback_copy(lead)["tagline"],
            "meta_description": fix(copy.get("meta_description")) or fallback_copy(lead)["meta_description"],
            "about": about, "services": svcs, "faq": faqs, "reviews": revs}


# ---------------------------------------------------------------- HTML blocks

def services_html(svcs):
    out = []
    for s in svcs:
        ico = ICONS.get(s["icon"], ICONS["wrench"])
        out.append('      <article class="svc">\n        <span class="svc-ico">%s</span>\n'
                   '        <h3>%s</h3>\n        <p>%s</p>\n        <p class="price">%s</p>\n'
                   '      </article>' % (ico, esc(s["title"]), esc(s["desc"]), esc(s["price_from"])))
    return "\n".join(out)


def reviews_html(revs, sample=True):
    star = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.9 6.3 6.9.8-5.1 4.7 1.4 6.8L12 17l-6.1 3.6 1.4-6.8L2.2 9.1l6.9-.8z"/></svg>'
    stars = '<span class="stars">%s</span>' % (star * 5)
    out = []
    if sample:
        out.append("      " + fallback_review_warning(revs))
    for r in revs:
        out.append('      <figure class="review">\n        %s\n        <blockquote>%s</blockquote>\n'
                   '        <figcaption>%s &middot; %s</figcaption>\n      </figure>'
                   % (stars, esc(r["text"]), esc(r["name"]), esc(r["area"])))
    return "\n".join(out)


def faq_html(faqs):
    out = []
    for f in faqs:
        out.append('      <details class="faq-item">\n        <summary>%s</summary>\n'
                   '        <div class="faq-a">%s</div>\n      </details>'
                   % (esc(f["q"]), esc(f["a"])))
    return "\n".join(out)


def areas_html(lead):
    hoods = []
    hood = (lead.get("neighborhood") or "").strip()
    if hood and hood not in BALTIMORE_AREAS:
        hoods.append(hood)
    hoods += [a for a in BALTIMORE_AREAS if a.lower() != hood.lower()][:13]
    hot = ' class="area hot"' if hoods else ' class="area"'
    parts = ['      <span%s>%s</span>' % (hot, esc(hoods[0]))] if hoods else []
    parts += ['      <span class="area">%s</span>' % esc(a) for a in hoods[1:]]
    parts.append('      <span class="area">+ all of Baltimore City &amp; County</span>')
    return "\n".join(parts)


def about_html(paras):
    return "\n".join("      <p>%s</p>" % esc(p) for p in paras)


def hero_media_html(slug, name, palette):
    for fname in ("hero.jpg", "hero.png", "hero.webp"):
        if os.path.exists(os.path.join(SITES_DIR, slug, fname)):
            return ('<div class="hero-media"><img src="%s" alt="%s at work" '
                    'width="960" height="480"></div>' % (fname, esc(name)))
    ini = esc("".join(w[0] for w in name.split()[:2]).upper() or "W")
    return (
        '<div class="hero-media"><svg viewBox="0 0 480 210" role="img" aria-label="%s">'
        '<defs><linearGradient id="hg" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient></defs>'
        '<rect width="480" height="210" fill="url(#hg)"/>'
        '<circle cx="392" cy="52" r="90" fill="%s" opacity="0.18"/>'
        '<path d="M60 150h70v-28h60v28h70" stroke="%s" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.5"/>'
        '<text x="36" y="112" font-family="Arial, sans-serif" font-size="54" font-weight="800" fill="#fff">%s</text>'
        '<text x="38" y="140" font-family="Arial, sans-serif" font-size="15" fill="%s">LICENSED &amp; INSURED - MASTER PLUMBER</text>'
        '</svg></div>' % (esc(name), palette["INK"], palette["INK_DEEP"], palette["ACCENT"],
                          palette["ACCENT_SOFT"], ini, palette["ACCENT_SOFT"]))


def jsonld(lead, copy, site_url, phone_href, areas, form_email, sample_reviews):
    local = {
        "@context": "https://schema.org",
        "@type": "Plumber",
        "name": lead.get("business_name"),
        "description": copy["meta_description"],
        "telephone": phone_href.replace("tel:", ""),
        "url": site_url,
        "priceRange": "$$",
        "address": {"@type": "PostalAddress",
                    "streetAddress": lead.get("address") or "",
                    "addressLocality": "Baltimore", "addressRegion": "MD"},
        "areaServed": [{"@type": "Place", "name": a} for a in areas[:10]],
        "openingHours": "Mo-Sa 07:00-19:00",
    }
    if form_email:
        local["email"] = form_email
    if not sample_reviews:
        local["aggregateRating"] = {"@type": "AggregateRating",
                                    "ratingValue": "4.9", "reviewCount": str(len(copy["reviews"]))}
    faq = {"@context": "https://schema.org", "@type": "FAQPage",
           "mainEntity": [{"@type": "Question", "name": f["q"],
                           "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in copy["faq"]]}
    return json.dumps({"@context": "https://schema.org", "@graph": [local, faq]}, ensure_ascii=False)


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ---------------------------------------------------------------- main

def read_lead(args):
    if args.demo:
        return dict(DEMO_LEAD)
    if args.stdin:
        return json.loads(sys.stdin.read())
    with open(args.data_file, "r", encoding="utf-8") as fh:
        return json.loads(fh.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--data-file")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--form-email", help="override form destination (used at handoff)")
    ap.add_argument("--force", action="store_true", help="rebuild even if dir exists")
    args = ap.parse_args()
    if not (args.stdin or args.data_file or args.demo):
        ap.error("need one of --stdin / --data-file / --demo")

    env = load_env()
    lead = read_lead(args)
    name = (lead.get("business_name") or "").strip()
    if not name:
        fail("lead has no business_name; nothing to build")

    base_slug = slugify(lead.get("slug") or name)
    slug = base_slug if (args.force or args.demo) else unique_slug(base_slug, SITES_DIR)
    if args.demo:
        slug = base_slug
    out_dir = os.path.join(SITES_DIR, slug)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "css"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "js"), exist_ok=True)

    copy, source = generate_copy(lead, env)
    gen_status = "ok" if source in ("freellmapi", "ollama") else "needs_rewrite"

    phone_href, phone_disp = norm_phone(lead.get("phone"))
    form_email = (args.form_email or lead.get("email") or env.get("OPERATOR_EMAIL")
                  or env.get("BUILDER_EMAIL") or "").strip()
    site_url = "https://%s.pages.dev" % slug
    years = (lead.get("years") or "").strip()
    years_line = (years + "+ years") if years.isdigit() else "Experienced"
    hood = (lead.get("neighborhood") or "Baltimore").strip()
    palette = PALETTES[int(hashlib.sha1(slug.encode()).hexdigest(), 16) % len(PALETTES)]
    sample_reviews = str(lead.get("reviews_source", "sample")).lower() != "real"

    areas = [hood] + [a for a in BALTIMORE_AREAS if a.lower() != hood.lower()][:13]

    tokens = {
        "BUSINESS_NAME": esc(name), "TAGLINE": esc(copy["tagline"]),
        "PHONE_HREF": phone_href or "#quote", "PHONE_DISPLAY": esc(phone_disp),
        "EMAIL": esc(form_email or "hello@example.com"),
        "ADDRESS_LINE": esc(lead.get("address") or (hood + ", Baltimore, MD")),
        "NEIGHBORHOOD": esc(hood), "CITY_LINE": "Baltimore, MD",
        "LICENSE_LINE": esc(lead.get("license") or "Licensed & insured"),
        "HOURS_LINE": "Mon-Sat 7am-7pm - 24/7 emergency",
        "YEARS_LINE": esc(years_line),
        "META_DESC": esc(copy["meta_description"]), "OG_TITLE": esc(name + " - Plumber in Baltimore"),
        "SITE_URL": site_url, "SLUG": slug,
        "SERVICES_HTML": services_html(copy["services"]),
        "ABOUT_HTML": about_html(copy["about"]),
        "REVIEWS_HTML": reviews_html(copy["reviews"], sample=sample_reviews),
        "FAQ_HTML": faq_html(copy["faq"]),
        "AREAS_HTML": areas_html(lead),
        "HERO_MEDIA_HTML": hero_media_html(slug, name, palette),
        "JSONLD": jsonld(lead, copy, site_url, phone_href, areas, form_email, sample_reviews),
        "FORM_ACTION": "https://formsubmit.co/%s" % (form_email or "setup@charmcitysites.example"),
        "BUILT_YEAR": str(datetime.date.today().year),
        "BUILDER_EMAIL": esc(env.get("BUILDER_EMAIL") or "you@example.com"),
        "INK": palette["INK"], "INK_DEEP": palette["INK_DEEP"],
        "ACCENT": palette["ACCENT"], "ACCENT_SOFT": palette["ACCENT_SOFT"],
    }

    render_jobs = [
        ("index.html", "index.html"), ("thankyou.html", "thankyou.html"),
        ("css/style.css", "css/style.css"), ("js/site.js", "js/site.js"),
        ("robots.txt", "robots.txt"), ("sitemap.xml", "sitemap.xml"),
    ]
    for src, dst in render_jobs:
        with open(os.path.join(TEMPLATE_DIR, src), "r", encoding="utf-8") as fh:
            body = fh.read()
        for key, val in tokens.items():
            body = body.replace("{{%s}}" % key, str(val))
        leftovers = re.findall(r"\{\{[A-Z_]+\}\}", body)
        if leftovers:
            fail("unreplaced tokens in %s: %s" % (dst, sorted(set(leftovers))))
        with open(os.path.join(out_dir, dst), "w", encoding="utf-8") as fh:
            fh.write(body)

    with open(os.path.join(out_dir, "lead.json"), "w", encoding="utf-8") as fh:
        json.dump(lead, fh, indent=2)
    with open(os.path.join(out_dir, "copy.json"), "w", encoding="utf-8") as fh:
        json.dump(copy, fh, indent=2)

    result = {"ok": True, "slug": slug, "dir": out_dir, "site_url": site_url,
              "gen_status": gen_status, "copy_source": source, "form_email": form_email,
              "copy_json": json.dumps(copy, ensure_ascii=False)[:45000]}
    print(json.dumps(result))
    log("built %s via %s (%s)" % (slug, source, gen_status))


def fail(msg):
    print(json.dumps({"ok": False, "error": str(msg)}))
    log("FAIL " + str(msg))
    sys.exit(1)


if __name__ == "__main__":
    main()
