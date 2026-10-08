---
name: web-search
description: Search the web from Kenny's PC with the self-hosted webcrawl tool (DuckDuckGo, Bing fallback) and optionally scrape every result to markdown. Use when you need sources and have no URL yet; free alternative to Firecrawl search.
---

# Web search (webcrawl)

> **Status: DRAFT (2026-10-08).** Fix this file when a step is wrong and add a line
> to the change log. Keep `.claude/skills/` and `.agents/skills/` copies identical.

The Firecrawl `search` equivalent. Where and how to run the tool: see web-scrape
("Where to run it").

## Quick start
```powershell
$W = 'D:\agent-cache\webcrawl\webcrawl.py'
python $W search 'linalool odor threshold air ppb' --limit 10
python $W search 'Habanolide vapor pressure site:dsm-firmenich.com' --limit 5
python $W search 'oakmoss atranol IFRA 51' --limit 8 --scrape --json-out D:\agent-cache\out\oakmoss.json
```
Each result has `title`, `url`, `description` and `engine` (`duckduckgo` or `bing`).
`--scrape` also fetches each result as markdown, with the same fallbacks as
web-scrape.

## How to search well
- Several narrow queries beat one broad one; run them in one PowerShell call.
- Use `site:` for known good sources: pubchem.ncbi.nlm.nih.gov, thegoodscentscompany.com,
  perfumersworld.com, ifrafragrance.org, fragrancematerialsafetyresource.elsevier.com
  (RIFM), webbook.nist.gov, echa.europa.eu, supplier sites (dsm-firmenich, givaudan,
  iff, symrise).
- Add the CAS number to chemical queries; trade names collide.
- For papers, prefer DOI pages and PubMed; the scrape adapters turn those into
  abstracts.
- Search snippets are leads, not evidence: open the page (web-scrape) before
  quoting a number.

## When it fails
- DuckDuckGo throttles with HTTP 202; the tool then asks Bing (`engine: bing`).
  If both return nothing, wait a minute or use WebSearch from the cloud thread.
- The Firecrawl connector's search needs credits.

**Done when** you have a short list of candidate URLs (or scraped pages) with the
query that found each, and you opened the ones you will cite.

## Change log
- 2026-10-08: created from Firecrawl's search skill, mapped to webcrawl v0.2.1.
