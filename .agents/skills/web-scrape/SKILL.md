---
name: web-scrape
description: Turn one or more URLs (web pages, PDFs, PubChem, PubMed, publisher pages) into clean markdown with Kenny's self-hosted webcrawl tool. Use whenever you have a URL and need its content; free, no credits, works where Firecrawl and WebFetch are blocked.
---

# Web scrape (webcrawl)

> **Status: DRAFT (2026-10-08).** Fix this file when a step is wrong and add a line
> to the change log. Keep `.claude/skills/` and `.agents/skills/` copies identical
> (`tests/test_skill_mirrors.py`).

The Firecrawl `scrape` equivalent. The tool is `D:\agent-cache\webcrawl\webcrawl.py`
on Kenny's PC (Python stdlib, no key, v0.2.1+). Source and tests:
`/mnt/project-files/webcrawl-build/`.

## Where to run it
- **On Kenny's PC** (Codex, local Claude Code): run it directly.
- **Cloud thread**: the cloud proxy blocks most sites (even example.com), so run it on
  the PC through the desktop-commander device tool `start_process` (PowerShell, about
  60 s per call). Put URLs in single quotes. For jobs over a minute use
  `Start-Process python -ArgumentList ... -RedirectStandardOutput <log>` and poll.
- If the device link is down: WebFetch first, then the Firecrawl connector (it may be
  out of credits).

## Quick start
```powershell
$W = 'D:\agent-cache\webcrawl\webcrawl.py'
python $W scrape 'https://example.com/page' --markdown-only          # plain markdown
python $W scrape 'URL1' 'URL2' --json-out D:\agent-cache\out\pages.json
python $W scrape 'URL' --formats markdown links                       # + outgoing links
python $W scrape 'URL' --render --wait 3000                          # JavaScript pages
python $W scrape 'URL' --full-page                                    # keep nav/footer
python $W scrape 'https://x.org/sds.pdf' --save-dir D:\agent-cache\downloads   # PDF -> text + saved file
```
Save long results with `--json-out` and read them with bounded reads
(`Select-String`, `Get-Content -TotalCount`) instead of printing whole pages.

## What it does for you (check `via` and `note` in the result)
- PubChem compound page -> PUG REST properties and experimental sections
  (odor, vapour pressure, boiling point, logP, density...); if PubChem answers
  "server busy" -> NCBI E-utilities summary, ranked to the parent compound.
- PubMed page -> abstract via E-utilities.
- Publisher 401/403/thin page with a DOI, ScienceDirect PII or OUP volume/issue/page
  URL -> Crossref + OpenAlex record. That is the **abstract, not the full text**:
  label it so.
- Any other refusal -> latest Internet Archive copy (`via` says wayback; note the
  capture date). Never for API URLs.
- Framesets are stitched; PDFs become text (pypdf).
- `--render` tries installed Chrome, bundled Chromium, then an off-screen real Chrome
  window (needed for Akamai sites such as sigmaaldrich.com).
- `--no-adapters` gives only the page itself.

## Rules
- Results are cached for a day (`cache\fetch.db`); `--max-age 0` forces a fresh fetch.
  Errors, 403/429/5xx and bot-check pages are never cached.
- A single scrape ignores robots.txt like a browser; add `--respect-robots` for bulk
  jobs. Keep the 1 s per-host delay.
- Record the source URL, `fetchedAt` and `via` with every value you take from a page.
- Supplier claims, Archive copies and abstracts are weaker than the full source:
  say which one you used.

**Done when** the content is saved or printed, you inspected it with bounded reads,
and every value you report carries its URL and evidence level.

## Known blocks
Basenotes article pages (Cloudflare, no Archive copy); PubChem PUG REST answered 503
to the PC all of 2026-10-08 (the E-utilities fallback covers it). Alibaba needs the
browser: see web-interact.

## See also
web-search (no URL yet), web-crawl (many pages of one site), web-research
(question -> cited answer), web-interact (clicks, forms, captchas).

## Change log
- 2026-10-08: created from Firecrawl's scrape skill, mapped to webcrawl v0.2.1.
