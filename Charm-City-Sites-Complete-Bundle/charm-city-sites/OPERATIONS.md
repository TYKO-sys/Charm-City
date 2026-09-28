# OPERATIONS — the one-time setup, then the daily fifteen minutes

The installer already did the heavy lifting: tools are in, workflows are
imported, everything auto-starts with your Mac. What is left is connecting
four free accounts, once. Roughly 45 minutes total. After that, the factory
runs and your only manual jobs are talking to plumbers and taking money.

If a step goes sideways, check **Troubleshooting** at the bottom.

> **On a Windows laptop?** Install with `1-INSTALL-WINDOWS.bat` and read
> `WINDOWS.md` first. Everything below is identical except three small
> swaps listed there (FreeLLMAPI key from the browser, Notepad for
> `env.sh`, smaller offline model).

---

## Part 1 — One-time setup (about 45 minutes, done once, never again)

### 1.1 Your spreadsheet (5 min)

1. Create a **new Google spreadsheet**: <https://sheets.new>.
   Name it `Charm City Sites`.
2. In it: **File → Import → Upload** → choose `sheet-templates/Leads.csv`
   → *Insert new sheet* → Import data. You get a tab named **Leads**.
3. Repeat for `sheet-templates/Settings.csv` → rename that new tab to
   **Settings**.
4. Copy the spreadsheet URL from the address bar. You will paste it during
   install (or into the workflows in step 1.3).

The tabs must be named exactly `Leads` and `Settings` (case-insensitive is
fine). Every workflow reads these two tabs and nothing else.

### 1.2 The fresh Gmail (7 min)

Use a clean Gmail for outreach, not your personal one.

1. Create the account (something like `charmcitysites@gmail.com`).
2. Turn on **2-Step Verification**: Google Account → Security.
3. Create an **App Password**: Google Account → Security → 2-Step
   Verification → App passwords → name it `n8n` → copy the 16 characters.
   You will paste it twice in a minute.

### 1.3 n8n control panel (20 min — the biggest chunk, one time)

Open <http://localhost:5678>. First visit asks you to create the owner
account. Any email and password — it stays on your machine.

Then create **four credentials** (Credentials → Add). Name them exactly as
written; the workflows look for these names:

| # | Credential type in n8n | Name it | Fields |
|---|---|---|---|
| 1 | **Google Sheets OAuth2 API** | `Charm City Google` | see below |
| 2 | **Telegram API** | `Charm City Telegram` | bot token from @BotFather |
| 3 | **Email (SMTP)** | `Charm City Email` | see below |
| 4 | **IMAP** | `Charm City IMAP` | see below |

**Google (the fiddly one, ~10 min):**

1. Go to <https://console.cloud.google.com> → create project `charm-city`.
2. APIs & Services → Library → enable **Google Sheets API** and
   **Google Drive API**.
3. APIs & Services → OAuth consent screen → External → app name
   `Charm City Sites` → your Gmail as support email → add your Gmail under
   **Test users** → save.
4. Credentials → Create credentials → **OAuth client ID** → Web application.
5. In the n8n credential screen, copy the **Redirect URL** it shows you
   (looks like `http://localhost:5678/rest/oauth2-credential/callback`) into
   the Google client's Authorized redirect URIs.
6. Copy the Google **Client ID** and **Client Secret** into the n8n
   credential → click **Connect Google Account** → approve the popup.

**Telegram (3 min):** message [@BotFather](https://t.me/BotFather) on your
phone → `/newbot` → name it `Charm City Sites Bot` → copy the token into
the n8n credential. Then send your new bot any message (say `hi`). It
replies with your **chat id** — a number like `123456789`. Keep it handy
for 1.5.

**Email (4 min):** create the two email credentials with the same Gmail
details — App Password from 1.2 as the password:

- `Charm City Email` (SMTP): host `smtp.gmail.com`, port `465`, SSL on.
- `Charm City IMAP`: host `imap.gmail.com`, port `993`, SSL on.

**Wire the workflows (5 min):** open each of the five imported workflows.
Two things to check per workflow:

1. Every **red node** (missing credential) → click it → Credential dropdown
   → pick the matching `Charm City ...` credential.
2. The green **Google Sheets nodes** → click one → if the spreadsheet field
   is empty or says `__SHEET_ID__` → click the field → *From list* → pick
   `Charm City Sites`. (Skip this if you pasted the sheet URL during
   install.)
3. **Save & Activate** (top right toggle).

Do this for all five: `01 Site Factory`, `02 Lead Machine`,
`03 Outreach`, `04 Deal Closer`, `05 Form Alerts`.

### 1.4 Cloudflare token (5 min)

1. Create a free Cloudflare account: <https://dash.cloudflare.com/sign-up>.
2. My Profile (top right) → **API Tokens** → Create Token → use the
   **Edit Cloudflare Pages** template → Continue → Create Token.
3. Copy the token. Also grab your **Account ID** (Cloudflare home page,
   right side).
4. Open `factory/env.sh` in any text editor, paste both:
   `CLOUDFLARE_API_TOKEN=` and `CLOUDFLARE_ACCOUNT_ID=`.

Every site then deploys to a free `yoursitename.pages.dev` address with one
command, no dashboard needed.

### 1.5 The AI brain + Settings tab (8 min)

1. FreeLLMAPI lives in your **menu bar** (the installer put it there).
   Click its icon → open the dashboard/popover → copy the **API key**.
2. Paste it into `factory/env.sh` at `LLM_API_KEY=`.
3. Open the **Settings tab** of your spreadsheet and fill:

| key | value |
|---|---|
| `telegram_chat_id` | the number the bot replied with in 1.3 |
| `operator_email` | your fresh Gmail address |
| `operator_name` | what emails are signed with (e.g. `Marcus`) |
| `operator_phone` | your phone number, in emails and on invoices |
| `daily_cap` | `10` (start with `6` for the first week) |
| `autosend` | `on` — or `off` to get drafts in Telegram instead |
| `price_default` | `$500` |
| `operator_address` | where clients mail checks |
| `paypal_note` | optional, e.g. `Card via PayPal: paypal.me/yourname` |

### 1.6 Test drive (5 min)

Send your Telegram bot:

```
/add Fells Point Test Plumbing | 410-555-0134 | Fells Point
```

Within two minutes you should get `SITE LIVE: ...` with a real
`*.pages.dev` URL. Open it on your phone. That URL — that is the product.
Delete the test row from the sheet (or mark it `dead` with
`/status <id> dead`) when done admiring it.

Setup is over. Everything below is now your actual "job."

---

## Part 2 — Daily life (about 15 minutes, from your phone)

**09:00** — Telegram brings the morning report. Read it. It tells you:
who gets emailed today (already handled), who replied, what needs a call.

**When a plumber replies** — Telegram pings you instantly with the message.
Call them back that day. Talking is the close; the site already sold itself.

**When someone fills a demo site form** — Telegram shows you the hot lead.
Forward it to the plumber: *"Your site caught this while you were working.
Imagine a year of these."* That is the pitch, and it is their own customer
doing the selling.

**When a deal lands** — one message: `/status 17 won` (plus
`/status 17 dead` for the no's — dead rows are never emailed again).
Workflow 04 sends the invoice within 30 minutes and the $400 missed-call
upsell two days later. Watch Zelle.

That is the whole day. The sheet is the database; Telegram is the remote
control; the morning report is your boss voice.

### The pricing ladder (from the business plan — no negotiating, no discounts)

- Site #1: **$500** — "the site you just saw, in your name by tomorrow."
- Site #2: **$650** — "same as his, and he already paid more."
- Site #3: **$800** — "last one at this price; demand is real."
- Upsell anytime: **$400** — missed-call text-back, pitched for you
  automatically, two days after each invoice.

3 sites + 1 upsell = **$2,350** = goal.

---

## Part 3 — Handing a site to a client (2 minutes, once per sale)

1. `bash scripts/handoff.sh <slug> <client-email>` — re-aims the contact
   form at their inbox and redeploys.
2. Submit **one test quote** on their live site yourself.
3. Tell them to click the one-time FormSubmit confirmation email that
   just landed.
4. Swap the sample reviews for their real Google reviews (their favorite
   3 — they email them over, paste into the sheet `notes` or just tell
   you; rerun the same handoff command after editing
   `factory/sites/<slug>/lead.json` and setting `reviews_source` to
   `real`).

The `slug` is in the sheet, and the bot's SITE LIVE message. Domain
hookup (their own `.com`) is a nice $50 add-on later, not today's problem.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| No SITE LIVE after adding a lead | `Open Dashboard.command` → is n8n up? Cloudflare token in `factory/env.sh`? Then check `factory/logs/`. |
| `needs_rewrite` in the sheet | The AI brain was unreachable, default copy shipped. Paste the FreeLLMAPI key in `factory/env.sh`, then blank the row's `website_status` and it rebuilds itself. |
| `deploy_error` in the sheet | Cloudflare token/account id wrong, or no internet. Fix, blank `website_status`, it retries. |
| Telegram silent | Chat id missing in Settings tab. Message the bot — its help reply shows your chat id. |
| Morning report never came | The Mac was asleep at 09:00. Nothing is lost — open the lid, the 2-minute poller catches up instantly. Keep the Mac awake during your work window (plugged in, or run `caffeinate -dimsu` in Terminal). |
| Emails landing in spam | Normal for week one of any new Gmail. Keep cap at 6, plain text (already is), personalize (the brain does). It clears as you send and get replies. |
| Site built but phone number wrong | Fix the phone cell in the sheet, blank `website_status`, done — rebuild + redeploy in ~3 minutes. |
| Want a do-over on any site | Blank its `website_status` cell. That is the rebuild button. |

## Sheet cheat-sheet (columns the bots read)

`id` (row's name — bot uses it in /status) · `business_name` · `phone` ·
`email` (outreach target) · `neighborhood` (copy flavor + SEO) · `website_status`
(`built` / `deploy_error` / empty = build me) · `slug` · `site_url` ·
`gen_status` (`ok` / `needs_rewrite`) · `outreach_status`
(`new` / `sent` / `replied` / `won` / `dead`) · `last_touch` · `next_touch`
(auto-schedules follow-ups) · `sent_count` (caps touches at 3) ·
`price_quoted` · `invoice_sent` · `upsell_sent` · `notes` · `years` ·
`address` · `source` · `gmaps_url` · `website` · `deploy_attempts` ·
`copy_json` (the AI copy, for reference).
