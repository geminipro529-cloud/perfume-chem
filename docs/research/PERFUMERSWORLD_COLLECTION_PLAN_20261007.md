# PerfumersWorld catalogue intelligence collection — 2026-10-07

Scope: enumerate the official public raw-material catalogue, including aroma chemicals, natural extracts, proprietary bases and supplied dilutions; identify non-material shop products separately. Preserve exact supplier SKU/form and source bytes. Produce searchable supplier records and a conservative live-inventory candidate crosswalk.

Implementation: use a disposable collection notebook/script under output/, reuse existing catalogue/census interfaces where appropriate, and write new source-bound artifacts under data/research/perfumersworld/20261007_01a1152f/. Do not change canonical parsers, formulation runtime, inventory, holds, historical sources or evidence ledgers. No new pipeline script.

Collection: inspect robots and official sitemap/category/catalogue pages; retain all discovered product identifiers with discovery lineage. Fetch public product and document-list pages with bounded concurrency, timeouts and response sizes. Record actual URL, timestamp, HTTP result and SHA-256. Parse exact product-local labels, supplied forms and document tabs; honor explicit unavailable flags before extracting content. Keep zero placeholders and unspecified units explicit.

Research: use the user-requested Firecrawl, Undermind, Amass, SciSpace, Consensus, Wolfram, Context7, Life Sciences Literature and Life Science Research routes. Plugin Management resolves installed capabilities. Adaptyv Bio is assessed via its index; protein experiment execution is outside chemical-catalogue research. No credentials, private stock information, or proprietary formulas are transmitted.

Verification: reconcile independent live enumeration surfaces and historical SKU sets, verify product-local identity, account for every fetch and unknown field, validate source hashes and randomly sampled extractions. Crosswalk by exact recorded SKU and conservative candidate labels only. Supplier intensity/life/use/IFRA fields remain supplier statements, never calibrated thresholds, approved doses or safety/release authority. Preserve Orris Liquid user hold.

Requested DeepSeek native workers were unavailable (Unknown model deepseek-flash). Four Codex-native read-only workers reviewed independent repository contracts under the user's explicit allowance. Parent owns collection, edits, source interpretation and final verification.
