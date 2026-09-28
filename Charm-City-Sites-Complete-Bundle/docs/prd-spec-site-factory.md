# PRD — Spec-Site Factory v1 ("Baltimore Trade Sites")

**Feature:** Sheet-driven, AI-automated spec-site factory for Baltimore home-service trades
**Users:** (1) Solo operator — 4–8 h/day, ADHD, $0 budget, new M5 24GB MBP; (2) Client — trade business owner with no/bad website; (3) Client's customers — homeowners on phones
**Stack:** FreeLLMAPI (brain router) · Ollama (offline fallback) · n8n self-hosted (spine) · Google Sheets (memory) · Cloudflare Pages (hosting) · plain HTML/Astro template + Python generator · Telegram (alerts) · Meta Muse (hero images)

---

## Problem statement

Operator needs $2,350 collected within 45 days (3 spec sites at $500/$650/$800 + one $400 automation upsell). Manual site building takes 2–3 days per site and scattered tools cap output below the 3-close target. The system must compress lead-to-live-site time below 10 minutes, keep fixed overhead at $0, and remove every tool-switching decision the operator has to make (ADHD tax).

## Success metrics

- Lead row → deployed live site: **≤ 10 minutes**, unattended
- Tools the operator touches per site: **1** (one row added to the Leads sheet)
- Outbound touches/day: **≥ 10** with ≤ 30 min of human time
- ≥ 1 closed client by day 28; **$2,350 collected by day 45**
- Fixed monthly overhead: **$0** (client-paid costs only, e.g. their own Twilio number for the upsell)

## User stories & acceptance criteria

1. **As the operator, I add a lead row so a site builds itself.** Given a row with business name, phone, neighborhood — when saved — then copy is generated via the local AI endpoint, the site is built from the template, deployed to `<slug>.<brand>.pages.dev`, the sheet row is updated with the URL and timestamp, and a Telegram alert arrives. Within 10 minutes.
2. **As the operator, I get a morning action list.** Given live leads, when the daily cron fires (9:00 AM local), then a Telegram message lists today's 10 new touches, all due follow-ups (day 3 / day 7), and any replies received. No lead is ever touched after a "no".
3. **As a client, my site works on a homeowner's phone.** Given a mobile visitor, when the site loads, then the click-to-call button is visible without scrolling, the quote form submits and triggers an alert to the client within 60 seconds, and Lighthouse mobile score ≥ 90.
4. **As the operator, the factory survives failures.** Given the AI endpoint is down, when generation runs, then the system falls back to Ollama, then to template default copy, and marks the row `needs_rewrite` instead of blocking the pipeline.

## Scope — v1 ships

- Plumber niche only; one template (mobile-first, click-to-call, services, reviews, quote form, LocalBusiness SEO schema)
- Google Sheet "Leads" as the single input surface
- 3 importable n8n workflows: (a) generate+deploy, (b) outreach digest + follow-up nudges, (c) form-webhook → client alert
- FreeLLMAPI as the single OpenAI-compatible endpoint for every AI consumer; Ollama offline fallback
- Outreach message drafts generated per lead, sent/approved manually by operator
- Telegram bot alerts; setup script + runbook; a deployed demo site

## Scope — v1 does NOT ship

Multi-niche templates · CRM (Sheets only; Comp AI CRM at v2) · automated SMS/email sending (drafts + manual approval only) · payments integration (Stripe Payment Links / Venmo manually) · voice agents (pipecat later) · client dashboard · social content pipeline (MoneyPrinterTurbo later)

## Data model — Google Sheet "Leads"

`id · business_name · phone · email · neighborhood · source · gmaps_url · website_status · slug · site_url · deployed_at · gen_status · copy_json · outreach_status (new/sent/replied/won/dead) · last_touch · next_touch · price_quoted · notes`

## Edge cases & failure states

- AI endpoint unreachable → Ollama fallback → template default copy → row flagged `needs_rewrite`; pipeline never blocks
- Free-tier rate limit mid-request → FreeLLMAPI fallback chain switches provider automatically (transparent)
- Deploy failure → row marked `deploy_error`, one automatic retry, then surfaced in the morning digest
- Duplicate lead → slug collision check, append `-2`; same phone number = same record
- Client replies "no" → `outreach_status = dead`, all future touches auto-suppressed
- Laptop asleep at cron time → n8n catch-up on wake; digest delayed, never skipped
- Form spam → honeypot field + rate limit on the webhook

## Open questions (checkpoint — answer before build starts)

1. Outreach email: existing Gmail or a fresh one?
2. Telegram for alerts — yes, or email-only?
3. Brand subdomain name (e.g. `charmcitysites.pages.dev`)?
4. Cloudflare account under your own email — confirmed OK (free)?
5. Plumbers locked as niche #1?

---

## Appendix A — The verified free stack

| Layer | Tool | Role | Cost | Source |
|---|---|---|---|---|
| Brain router | **FreeLLMAPI** (tashfeenahmed/freellmapi) | 34 free providers behind one local OpenAI-compatible endpoint (`localhost:3001/v1`); macOS menu-bar app; auto provider failover; MIT | $0 | your catalog, verified |
| Offline fallback | **Ollama** + Qwen-class 14B | Works with no internet; private | $0 | your catalog + FMHY |
| Chat frontend | **Open WebUI** or **Jan** | Manual copy edits, prompt testing | $0 | your catalog + FMHY |
| Spine | **n8n** self-hosted | All automation: generate→deploy→alert→follow-up | $0 | your catalog (4 saves) |
| Memory | **Google Sheets** → Comp AI CRM at v2 | Lead + client state | $0 | evergreen → catalog |
| Hosting | **Cloudflare Pages** (wrangler CLI) | Free unlimited static hosting + free subdomains | $0 | evergreen |
| Images | **Meta Muse Image** (FMHY) | Free unlimited hero images w/ Meta login; Perchance/Bing Create as alternates | $0 | FMHY |
| Forms | **FormSubmit** or **Web3Forms** free tier | Quote form → n8n webhook → client alert | $0 | evergreen |
| Alerts | **Telegram Bot API** | "Site live" pings, morning digest | $0 | evergreen |
| Lead enrichment | **browser-use** / scrapling / firecrawl self-host | Scrape + enrich leads | $0 | your catalog |
| Lead watching | **changedetection.io** (34.6k★) | Monitor license lists / directories for new names | $0 | your catalog |
| Components | **shadcn/ui** patterns | Template component quality | $0 | your catalog |
| Reference | **ripienaar/free-for-dev** | The free-tier bible for any future need | $0 | your catalog |

**Staged for later (wrong month, right tools):** pipecat (voice receptionist — upsell 2.0) · MoneyPrinterTurbo/auto-editor/yt-dlp (content engine) · Comp AI CRM (10.9k★, agentic CRM) · Postiz (social scheduling) · Plausible/Openpanel (client analytics as a $50/mo add-on) · Cal.com (booking) · Colibri (GLM 5.2 in 24GB RAM, per FMHY) · BetterDisplay (MBP utility)

**Skipped on purpose:** FMHY jailbreak/leaked-prompt/proxy sections (ban risk; no business runs on stolen keys) · Dify/Langflow/crewAI (great tools, wrong month — one spine beats three) · vLLM/KoboldCpp/LocalAI (redundant with FreeLLMAPI + Ollama) · Polar Browser (could not verify it exists) · Grokbot (Grok's bot; fine as a chat lane, not core)
