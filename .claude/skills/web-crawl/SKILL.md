---
name: web-crawl
description: Map a website's URLs or crawl many of its pages to markdown files with Kenny's self-hosted webcrawl tool (robots.txt obeyed, resumable). Use for bulk jobs on one site, such as a supplier catalogue or a documentation section; free alternative to Firecrawl crawl and map.
---

# Web crawl and map (webcrawl)

> **Status: DRAFT (2026-10-08).** Fix this file when a step is wrong and add a line
> to the change log. Keep `.claude/skills/` and `.agents/skills/` copies identical.

The Firecrawl `map` + `crawl` equivalent. Where and how to run the tool: see
web-scrape ("Where to run it"). Crawls take minutes, so start them in the
background and poll the log.

## 1. Map first
```powershell
$W = 'D:\agent-cache\webcrawl\webcrawl.py'
python $W map 'https://www.perfumersworld.com/' --limit 400      # 400 URLs, tested 2026-10-08
python $W map 'https://site/' --include '/product/' --exclude '\?sort='
```
`map` lists URLs from sitemap.xml plus the start page's links. `--search` keeps URLs
whose **address** contains the words (not the page text), so `--search musk` on
perfumersworld.com finds nothing: use web-search with `site:` for content. If the URLs you need are all there, scrape just those
(web-scrape accepts many URLs) instead of crawling.

## 2. Crawl
```powershell
Start-Process python -ArgumentList $W,'crawl','https://site/section/','--limit','100','--depth','2',
  '--include','/section/','--out','D:\agent-cache\crawls\site-section','--progress' `
  -RedirectStandardOutput D:\agent-cache\crawls\site-section.json `
  -RedirectStandardError D:\agent-cache\crawls\site-section.log -NoNewWindow
```
- Output: `pages\*.md` (one per page, front matter with url and fetch time),
  `index.jsonl` (one row per URL: status, title, file, error), `summary.json`.
- `--include` filters the links to follow, so the start page must link to the section.
  If it doesn't (perfumersworld.com's home page has no `/service/` links), start
  inside the section, add `--sitemap`, or scrape the URLs from `map` directly.
- Always set `--limit`, `--depth` and `--include` so the crawl stays on topic;
  `--max-minutes` caps time; `--sitemap` seeds from sitemap.xml; `--no-pdf` skips PDFs.
- Rerun with the same `--out` to resume; already saved pages are not fetched again
  and their links are still followed.
- robots.txt is obeyed for crawl and map. `--ignore-robots` only for a site Kenny
  owns or has permission to crawl.
- 1 s per-host delay by default; don't lower it on supplier sites.

## 3. Use the results
Read `index.jsonl` for errors first, then grep the pages
(`Select-String -Path ...\pages\*.md -Pattern 'CAS'`). Copy only the extracted
facts (with their page URL) into `/mnt/project-files/<task>/`, not the whole crawl.

**Done when** summary.json shows the pages you needed, errors are explained, and the
facts you took carry their page URLs.

## Change log
- 2026-10-08: created from Firecrawl's crawl and map skills, mapped to webcrawl v0.2.1.
