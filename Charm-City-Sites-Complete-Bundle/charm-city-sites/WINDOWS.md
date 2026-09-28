# WINDOWS — the factory on your Windows laptop

Two-minute version: Windows has a real Linux layer built in (WSL). The
entire factory lives inside it, **unchanged** — the `.bat` files in this
folder are just the doors. The Mac installer and the Windows one share
everything: same 5 workflows, same Google Sheet, same Telegram bot, same
secrets file, same demo sites. Nothing about the business changes.

---

## What you click, in order

**0.** If Windows shows *"Windows protected your PC"* (SmartScreen) when
you run a `.bat`: click **More info → Run anyway**. (Or right-click the
file → Properties → check **Unblock** → OK.) Windows just distrusts any
new `.bat` file; it says that about all of them.

**1.** Double-click **`1-INSTALL-WINDOWS.bat`**.
- One Administrator approval. Windows may want to **restart once** to
  turn on its Linux layer — once, ever.
- A purple "Ubuntu" window may open asking you to create a Linux
  username: **just close it with the X.** The installer creates its own
  hidden user (`ccs`). You will never type a Linux password.
- The install itself is 10–15 minutes of downloads. One question may
  appear — your Google Sheet URL. Press **Enter** to skip if unsure.

**2.** A browser opens `http://localhost:5678`. Create the n8n owner
login — any email + password, it stays on this laptop. (First load can
take a minute; refresh once.)

**3.** Open **`OPERATIONS.md` → Part 1** and do the one-time paste-ins
(about 45 minutes: the Google Sheet, fresh Gmail, Telegram bot,
Cloudflare token). It is identical to the Mac steps — except the three
swaps in the table below.

## The only three differences from the Mac instructions

| OPERATIONS.md says (Mac) | On Windows you instead |
|---|---|
| FreeLLMAPI key "from the menu-bar app popover" | open **http://localhost:3001** in your browser, do its one-time dashboard login, open the **Keys** page, copy the unified key |
| edit `factory/env.sh` in TextEdit | open **Notepad** → File → Open → paste this into the file-name box: `\\wsl.localhost\Ubuntu-24.04\home\ccs\charm-city-sites\factory\env.sh` (if your distro has a different name, use that) |
| offline fallback model `qwen2.5:14b` | laptops get `qwen2.5:3b` — 2 GB, fast enough on CPU; the Mac installer bumps it back to the big one automatically |

## Keeping it alive — already done for you

The installer created two invisible Windows scheduled tasks:

- **Charm City Sites KeepAlive** — every 5 minutes, if anything is down
  (Docker, the AI brain, n8n), it starts it again. Survives reboots:
  the factory wakes within 5 minutes of you logging in.
- **Charm City Sites LeadHunt** — daily at 07:40, the lead hunt runs.
  (The n8n workflows also hunt on their own schedule — belt and
  suspenders.)

To see them: Start menu → type **Task Scheduler** → look for the two
names. Manual wake-up or health check any time: double-click
**`Start Factory (Windows).bat`**.

## Two power settings worth 20 seconds

The factory runs while the laptop is on. While plugged in:

- **Settings → System → Power → Screen and sleep** → *When plugged in,
  put my device to sleep after:* **Never**
- **Control Panel → Power Options → Choose what closing the lid does** →
  When plugged in: **Do nothing**

Turning it off overnight is fine — the heartbeat catches everything up
when you open the laptop again. Keep the extracted kit folder somewhere
permanent (Downloads is fine); the three `.bat` doors live there.

## When the MacBook arrives

1. Copy this kit folder — or just the zip — to the Mac.
2. Double-click **`Install Factory.command`** (the Mac installer).
3. Paste the same secrets into `factory/env.sh` — the exact values you
   already put in the Windows copy. The sheet, Telegram bot, Cloudflare
   account, and Gmail all live in the cloud; nothing actually moves.

That is the entire migration. About 15 minutes.
Optional cleanup on the Windows side: Task Scheduler → right-click the
two "Charm City Sites" tasks → Delete, and `wsl --unregister
Ubuntu-24.04` in Command Prompt if you want the disk space back.

## Troubleshooting

- **"wsl" not recognized, or install fails with a virtualization
  error** — enable VT-x (Intel) or SVM (AMD) in your BIOS/UEFI, then
  re-run `1-INSTALL-WINDOWS.bat`.
- **localhost:5678 not loading** — double-click
  `Start Factory (Windows).bat`, wait a minute, refresh the page. Still
  nothing: open Command Prompt → run `wsl --shutdown` → run
  `Start Factory (Windows).bat` again.
- **Docker refused to start** — Command Prompt (admin) →
  `wsl --shutdown` → `Start Factory (Windows).bat`.
- **Colors look garbled in the status window** — harmless cosmetic
  stuff in the console; the real dashboard is the browser page.
- **Anything inside the factory misbehaves** — same as the Mac:
  check **Troubleshooting** at the bottom of `OPERATIONS.md`. Logs live
  in `factory/logs/` inside the Linux side, reachable through the
  Notepad path in the table above (`...\charm-city-sites\factory\logs`).
