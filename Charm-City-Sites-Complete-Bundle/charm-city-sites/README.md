# Charm City Sites — the factory

You build nothing by hand. The factory builds the sites, finds the leads,
writes the emails, chases the money. You take calls and cash checks.

## Start (one afternoon, then it runs itself)

**On a Mac:** double-click `Install Factory.command`.
**On a Windows laptop:** double-click `1-INSTALL-WINDOWS.bat`, then read
`WINDOWS.md`. Same factory, same files, same steps after that — the Linux
side of Windows runs everything unchanged.

1. **Unzip this folder anywhere.** Downloads folder is fine.
2. **Double-click the installer for your machine** — that is the whole install.
3. **Open `OPERATIONS.md`** and do the one-time paste-ins it lists
   (about 45 minutes of clicking, spread across 4 accounts you create once).

## What runs on its own after that

| When | What happens |
|---|---|
| every 2 minutes | any new lead row becomes a built, deployed website |
| 07:40 daily | the lead hunter finds new Baltimore plumbers and queues them |
| 07:55 daily | new leads land in your sheet, deduped |
| 09:00 daily | Telegram morning report: who to email, who replied, what broke |
| 09:11 daily | up to 10 personalized emails go out on their own |
| every minute | form fills and email replies hit your Telegram instantly |
| every 30 minutes | closed deals get invoices, then the $400 upsell pitch 2 days later |

## Your only jobs

- Take the plumber's call when they phone you (they will).
- Mark outcomes from your phone, in Telegram: `/status 17 won`
- Collect the money (Zelle lands in your inbox).

## The pieces

- `site-template/` — the product. One file set, infinite plumber sites.
- `scripts/` — generator, deployer, lead hunter, brain caller. All stdlib Python, no dependencies.
- `n8n/` — the 5 workflows that run the whole business.
- `demo-site/` — a finished example site. Show it to anyone, today.
- `factory/` — working folders: leads, built sites, logs, your `env.sh` secrets file.
- `OPERATIONS.md` — the one-time setup walkthrough + troubleshooting.
- `WINDOWS.md` + the three `.bat` files — the Windows-laptop track.

Something looks wrong? Double-click `Open Dashboard.command`
(Windows: `Open Dashboard (Windows).bat`). It tells you
what is up, what is down, and what to paste where.
