---
name: web-interact
description: Drive a real Chrome on Kenny's PC to click, type, upload images, page through results or get past slider captchas (Alibaba, logged-in or JavaScript-heavy sites) when web-scrape can't read the page. Free alternative to Firecrawl interact.
---

# Web interact (real Chrome on Kenny's PC)

> **Status: DRAFT (2026-10-08).** Fix this file when a step is wrong and add a line
> to the change log. Keep `.claude/skills/` and `.agents/skills/` copies identical.

The Firecrawl `interact` equivalent. Try web-scrape with `--render` first; use this
only when the page needs clicks, form input, uploads, or a human-looking browser.

## Setup (already done on Kenny's PC, 2026-10-08)
- A separate Chrome runs with `--remote-debugging-port=9333
  --user-data-dir=D:\agent-cache\chrome-bu` (not his everyday profile).
- `C:\Users\ASUS\AppData\Local\Chromium\User Data\DevToolsActivePort` holds
  `9333` and `/devtools/browser/<id>` so the remote-devices browser-use plugin finds it.
- If Chrome restarted, the id changed: read it from `http://127.0.0.1:9333/json/version`
  and rewrite that file.

## Use
- Cloud thread: the remote-devices browser-use tool (`browser_exec`) runs Python
  with helpers (`new_tab`, `page_info`, `cdp`, screenshots). Codex on the PC can use
  Playwright against the same port.
- Open with `new_tab(url)` once, then reuse that tab; close tabs you opened.
- Keep each call under about 6 page loads; the device call times out at 60 s.
- Uploads: CDP `DOM.setFileInputFiles` on the file input (Alibaba image search:
  click `.image-search-icon`, then set `input.upload-file`).
- Read results from the DOM and save them as a table under
  `/mnt/project-files/<task>/`; download images on the PC (the cloud proxy blocks
  most CDNs).

## Limits
- Never sign in, buy, post, or submit forms that send anything outside without
  Kenny's explicit go.
- If a captcha still blocks after a real-browser load, stop and tell Kenny; don't
  try to solve captchas automatically.

**Done when** the data you needed is saved with its page URLs, and the tabs you
opened are closed.

## Change log
- 2026-10-08: created from Firecrawl's interact skill and the Alibaba image-search
  procedure.
