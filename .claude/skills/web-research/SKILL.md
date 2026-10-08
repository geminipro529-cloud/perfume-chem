---
name: web-research
description: Answer a research question (material data, safety limits, papers, supplier facts) by searching, scraping and citing sources with Kenny's webcrawl tool, in parallel when there are several topics. Use for "find out", "look up", "what does the literature say"; free alternative to the Firecrawl agent and research index.
---

# Web research (webcrawl)

> **Status: DRAFT (2026-10-08).** Fix this file when a step is wrong and add a line
> to the change log. Keep `.claude/skills/` and `.agents/skills/` copies identical.

The Firecrawl `agent` / research equivalent, built from web-search and web-scrape.
Where and how to run the tool: see web-scrape ("Where to run it").

## 1. Plan
Split the question into topics a worker can finish alone (one material, one claim,
one regulation). Write the evidence table header first:
`claim | number or quote | source URL | evidence level | fetched`.
Evidence levels: **read** (full text), **abstract**, **supplier claim**,
**database** (PubChem, NIST, TGSC), **archive copy**, **snippet only** (not citable).

## 2. Search and read
- Per topic: 2 to 4 narrow queries (web-search), then scrape the 3 to 5 best hits
  (web-scrape). Prefer primary sources: RIFM/IFRA documents, NIST WebBook, PubChem
  experimental sections, papers, then supplier sheets.
- Papers: scrape the DOI or PubMed URL; the adapters return the abstract. Say
  "abstract" unless you read the full text.
- Material properties: also run `D:\agent-cache\tools\chemprops.py <CAS>` for MW,
  formula and measured vapour pressure (it withholds values it can't tie to the CAS).
- Several topics: give each to its own worker in parallel (Kenny wants speed but
  watch cost; cap workers per the project instructions). Each worker returns the
  evidence table plus NOT FOUND and "known, not retrieved" lists.

## 3. Check before you conclude
- Re-open the source for any number that changes a conclusion; workers have
  mislabelled authors and misread ranges.
- Watch units: some producer pages print mm Hg estimates labelled as Pa; usage
  recommendations are not IFRA limits.
- Keep conflicts visible (two sources, two values) instead of averaging.

## 4. Deliver
Answer first, then the evidence table and the not-found list. Long write-ups go in
a Claude Doc or a file under `/mnt/project-files/<task>/`. Never write sourced values
into `data/materials` or the engine from this skill: hand them to material-data-fill.

**Done when** every claim in the answer has a URL and an evidence level, and what
could not be found is listed.

## Change log
- 2026-10-08: created from Firecrawl's agent/research skills and the project's
  literature-review workflow, mapped to webcrawl v0.2.1 and chemprops.
