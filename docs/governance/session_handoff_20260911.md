# Session handoff — 2026-09-11 (engine-fix + intake window)

Purpose: carry this session's state into a new opencode session. If you are a
fresh session reading this, treat it as context, not authority: verify against
the repository before acting.

## Repository state

- Repo: `D:\chatbots\perfume-chem-integration-20260909`
- Branch: `codex/integration-20260909`, HEAD `89f1c0e5` (3 ahead of `origin`)
- Dirty: `.codex/config.toml` (not ours — do not touch)
- Root `D:\chatbots\perfume-chem` is the archive (26 behind integration); do
  work in the integration worktree.

## Commits made this session

| Commit | Change |
|---|---|
| `dce6e8a5` | Hedonics/architecture references (Tier A/C) + `hedonics_and_architecture` topic in `future_modules/literature_references.py` |
| `7cddb88b` | Anchored successor overlays for the frozen C0 pins (mechanism + 47 re-binds) |
| `89f1c0e5` | C0 human-read drift pass + 21 `owner_rebaseline` receipts + `C0-LH-005` frozen to C0 v2 |

## Supplier intake (uncommitted)

- `data/knowledge_graph/supplier_resolution_ledger.json` — closing ledger for the 31 non-PW materials.
- `data/knowledge_graph/bontoux_material_data.json` — Bontoux identity-only record (Geranium Flower EO; no public TDS).
- `data/knowledge_graph/generic_material_data.json` — added `Ethanol 96%`, `Cinnamon Bark EO - Telvada USDA Organic`; Geranium Flower EO now points at Bontoux.
- `data/external/perfumersworld/aliases.json` — `Clove EO (India)` → Clove Bud EO, `Basil EO (India, Ocimum Basilicum)` → Sweet Basil EO.
- `data/knowledge_graph/pw_material_data.json` — Clove Bud `7SP00122` (CAS 8000-34-8) and Sweet Basil `7PS00047` (CAS 8015-73-4) added.

## Verified state

- C0 verifier: **PASS, 0 errors** (was 49).
- `tests/test_c0_physical_model_inventory.py` + `tests/test_verification_invariants.py`: **26 passed**.
- Quick gate: **10/0 PASS**.
- Owner decisions already executed: `C0-LH-005` freeze; 21 owner re-baselines.

## Open owner decisions (not yet taken)

1. **C5** — re-bind `C5_INVENTORY_SHA256` to the current `inventory.txt` authority (a scientific claim), or leave as hold.
2. **Backend corpus** — re-baseline `synergy_matrix.json` / `theory_rules.json`, or restore the frozen corpus.

## Uncommitted work

- `.gitignore` — adds `data/external/perfumersworld/raw/`.
- `tools/pw_enrich.py` — PerfumersWorld intake tool (resumable; catalogue index, aliases, manual SKUs, product metadata, CoA/IFRA/MSDS PDFs with SHA-256 cache).
- `data/knowledge_graph/pw_material_data.json` (+ `pw_material_data_shard2/3/5.json`) — parsed records.
- `data/external/perfumersworld/` — catalogue index (1,321 products + categories), aliases, manual SKUs, raw cache.
- `data/external/pw_shards/` — 5 seeded shard caches.
- `output/pw_shard{1,4}.ps1|.log|.err` — detached shard runners (output/ is gitignored).

## PerfumersWorld intake status

- Tool: `tools/pw_enrich.py`. Resolution ladder: exact → `aliases.json` → same-material suffix → PW search (`--search`) → DDG lite (default) → containment (`--strict` disables).
- Tool bugs fixed this session (in `tools/pw_enrich.py`):
  - relative `--cache-dir` no longer crashes — `_display_path()` guards `relative_to` and falls back to cwd/absolute.
  - added `--materials-file` (one name per line) for names containing commas; reads with `utf-8-sig` so a PowerShell-written BOM does not corrupt the first name.
  - `--materials` still splits on commas; use `--materials-file` when a name contains a comma.
- Data available per material: CAS, physical state, relative odor impact, odour life (smelling strip), and `ifra/COA|IFRA|MSDS/<SKU>.pdf` (+ `/ifra/view-page.php?pro_id=<SKU>` inline IFRA certificate). PDFs verified by `%PDF-` magic and cached.
- Javanol and other out-of-stock items are **not** in the supplies catalogue; resolve via DDG lite and pin in `data/external/perfumersworld/manual_skus.json` (Javanol = `4WX10027`).
- Shards 2/3/5 completed; shards 1 and 4 were being re-run as detached processes (PIDs 1904, 7864) at handoff time. Check with:
  `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'pw_enrich' }`
- **Intake CLOSED (2026-09-11):** the 31 inventory materials that do not resolve to a PW SKU are now each given exactly one disposition in `data/knowledge_graph/supplier_resolution_ledger.json` — 3 `pw` (Clove EO India `7SP00122`, Basil EO India `7PS00047`, Nagarmotha Oil `7WU09815` CAS 68916-60-9, all fetched), 3 `ssd`, 1 `bontoux`, 12 `generic`, 5 `prepared_stock`, 6 `dilution_of_parent`, 1 `not_owned`. Note: `Nagarmotha Oil` is out of stock and absent from the supplies-table catalogue (so site search misses it); the owner supplied the SKU. PW spells it "Nagarmotha". `eo_source_map.json` / `material_source_overrides.json` / `prepared_stocks.json` / `generic_material_data.json` / `ssd_material_data.json` / `bontoux_material_data.json` hold the detail.
- Unresolved names at PW are the `status != "OK"` records in each shard file; a second supplier (Simple Scents DIY, `simplescentsdiy.com`, sitemap has ~1,554 URLs, `/product/<id>/<slug>`, listing pages `/fragrancelist` and `/essentialoils-list`) is the fallback. SSD CoA numbers must be **processed visually** — record `coa_needs_visual_review: true`, do not OCR.

## Next recommended order

1. PW/SSD intake is closed (see `supplier_resolution_ledger.json`). Next: map `pw_impact`, `pw_odour_life_hrs`, `pw_class` into `data/knowledge_graph/material_properties.json` and the data spine.
2. Function-balance gate (chosen next job): build the Heart/Modifier/Blender/Fixative/X-Factor model in `engine/knowledge/performance_engineering.py` (currently a 27-line stub). Recon done: add `ReleaseGateConfig.function_balance_enabled: bool = False` and append `_gate_function_balance` conditionally in `engine/pipeline/gates.py` at the `gates = [...]` / `if config.deep_plane_diagnostics_enabled:` site (~line 5791). Opt-in avoids golden-output churn.
3. C5 + backend receipts (needs the two owner decisions above).
4. Module cleanup: rename `engine/optimization/`, consolidate the two intervention layers, fix KB DB distribution so fresh clones can run knowledge tests.
5. Root master's three checks that were force-pushed past (`c35289af` used `--no-verify`): `formula-artifact-validation`, `scientific-audit`, `material-data-validation`.

## Module classification (condensed)

- **KEEP:** `engine/pipeline/`, `families/`, `units/`+`quantities.py`, `optimizer/`, `optimization/`, `physics/`+`thermo/`+`calibration/`, `knowledge/`+KB, `reconstruction/`+`identity/`+`evidence/`+`target/`+`bottle/`+`versioning/`, `data_spine/`+`inventory/`+`inventory_parser.py`+`name_utils.py`+`material_*`, `safety/`+`ifra_*`, `workbench.py`, receipts/audit modules, `fuckups/`.
- **MODIFY:** data-in-code (`odor_thresholds.py`, `ingredient_intelligence.py`), `inventory_parser.py` EOL pin, `optimization` rename, intervention consolidation, KB DB distribution.
- **IMPROVE:** reconstruction stack, `sensory/` migration, `ingestion/` + supplier docs, backend holds, formulas artifacts, science coverage (Antoine/HSP/OR 0%, dHvap 0.16%, ODT-air 7.8%, hedonic 10.8%).
- **QUARANTINE:** `engine/formulation_intelligence/` (NOT_RELEASE_READY), perception research candidates, retired complexity/sensory contracts, `receptor/`, `experiments/`, `future_modules/`, zero-ref leftovers (`perspectives.py`, `pattern_miner.py`, `science_data.py`, `emotional_mapping.py`, `opus_v_workbook.py`, `build/`, `solforge/`, `biology/`, `delivery/`, `orchestration/`, `interaction_registry/`), `chat_bridge/`, `incoming_review/`.

## Key commands

```powershell
Set-Location D:\chatbots\perfume-chem-integration-20260909
.venv\Scripts\python.exe scripts\verify_c0_physical_model_inventory.py
.venv\Scripts\python.exe -m pytest tests/test_c0_physical_model_inventory.py tests/test_verification_invariants.py -q
.venv\Scripts\python.exe scripts\pipeline_audit.py project-verify --quick --json
.venv\Scripts\python.exe tools\pw_enrich.py --from-inventory --strict --no-ddg
```

## Rules that remain in force

- No commit unless explicitly asked.
- Do not unfreeze `configs/complexity/complexity_module_registry_v1.json`.
- Pins move only through anchored successor records (`docs/governance/pin_successor_ledger_20260911.md`); R1 (reproducible superseded digest) and R2 (no CRLF preference) apply.
- Supplier and literature data are evidence-classed (`SUPPLIER_TECHNICAL`, Tier A/C); never promoted to measured truth without held-out validation.
