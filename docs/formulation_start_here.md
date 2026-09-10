# Formulation — start here

The operator's entry document for the Perfume-Chem working tree. Every command below was executed or
`--help`-verified in a detached worktree of the integration repository at `6a3d77e6`, with the interpreter
named in §1 and the lane as the working directory. Observed results are quoted, not predicted; where a
value was not established it is written `UNKNOWN`. Draft target: `docs/formulation_start_here.md`.

## 1. The working tree

| | |
|---|---|
| Repository | `D:\chatbots\perfume-chem-integration-20260909` |
| Branch | `codex/integration-20260909` (HEAD `0d9434e4cae5eaae3af5f0dae35fc42984f5d38a` when this was written) |
| Interpreter | `D:\chatbots\perfume-chem-integration-20260909\.venv\Scripts\python.exe` — CPython 3.11.15, pytest 9.1.1 |
| Canonical checkout | `D:\chatbots\perfume-chem` — never write here from a lane; it is the user's live checkout |

Run every command below from the repository root (or `backend\` where noted) with that interpreter.
Do not create a virtualenv and do not install packages.

## 2. Entry commands

### 2.1 See the stock you actually own

```powershell
& $py scripts\scan_inventory.py            # full scan: category, note, role, ODT, MW/VP
& $py scripts\scan_inventory.py --quick    # names only
& $py scripts\scan_inventory.py --blind formulas\<Formula>.md   # is every row in the inventory?
```

Verified: the full scan printed `INVENTORY — 264 materials` and `DONE — 264 materials`, exit 0; `--quick`
printed the name-only list, exit 0; `--blind` printed one `✅` / `❌ NOT IN INVENTORY` line per row and
exited 0. Note there is no argparse in this script — `--help` is not intercepted and a plain scan runs,
so use `--quick` when you want a cheap listing.

### 2.2 Draft the formula file

The release gate parses markdown tables, not prose. Two shapes are accepted:

- a single-formula file with an `# Title` line, or
- a numbered multi-formula file split on `## <n>. <Name>`.

Rows are recognised from the dose table. The canonical header is
`| # | Ingredient | Dilution | µL | mL |`; `| Ingredient | Dilution | µL |`, `| Ingredient | % |` and
`| Ingredient | % | Dilution |` also parse. Quote the **dilution in the cell** (`neat`, `10% in DPG`,
`50% w/w in DEP`); a blank or `—` cell is read as neat, so never leave it empty by accident. Give every
material in µL of the stock you will actually pipette, and keep the concentrate total equal to
`--expected-concentrate-ul`. Rows struck through with `~~` are treated as audit history and skipped.

Use the seven-layer skeleton in `docs/perfume_formula_architecture_template.txt` for structure. Header the
file the way the live formulas do, e.g. `formulas\DPP_01_Mandarin_Ember_Sandalwood_30mL_EDP_R2.md`:

```
# <Name> — <Form> — 30 mL EDP
**Date:** <YYYY-MM-DD>
**Claim mode:** <unclaimed|claimed>
**Immediate parent:** `formulas/<parent>.md`      # revisions only
**Parent formula-definition SHA-256:** `<64 hex>`   # revisions only
**Concentration:** 6,000 µL concentrate + ethanol 96% q.s. to 30.00 mL; nominal 20% v/v EDP
**Presentation order:** <physical basket order, then descending µL>
**Status**: <lifecycle marker and reason>
```

The `**Status**` line is the lifecycle marker. A formula that is not current carries the fail-closed text
`**Status**: QUARANTINED — do not mix or release.` plus the reason; see §4.

### 2.3 Gate the formula

```powershell
# first pass / new formula
& $py scripts\formula_release_gate.py `
    --formula-file formulas\<Formula>.md `
    --expected-concentrate-ul 6000 `
    --brief generic `
    --json > $out

# revision of an existing line: declare the parent and any intentional active-dose jump
& $py scripts\formula_release_gate.py `
    --formula-file formulas\<Revision>.md `
    --expected-concentrate-ul 6000 `
    --brief generic `
    --parent-formula-file formulas\<Parent>.md `
    --authorize-active-dose-change "<Material>=<authority text>" `
    --json > $out
```

Verified: `--help` exits 0 and lists all flags above. `--parent-formula-file` is the immediate parent
revision and triggers the mandatory G15 stock-rebase + temporal OAV screening; repeat
`--authorize-active-dose-change MATERIAL=AUTHORITY` once per material whose active dose intentionally moves
by ≥3×, and put the authority text you are relying on in it (it is preserved in the G15 audit evidence).
`--brief` accepts `auto`, `generic`, `layton_dna`, `aromatic_fougere`, `vetiver_woody`,
`floral_aldehydic_amber`, `dhi_2011`, `dhp_2014`, `woody_floral_musk`, `gourmand_floral`,
`prada_lhomme`; use `--family-archetype <key>` if the brief is not listed. Add `--commercial-ready`
only when you mean the stricter commercial bar (80% IFRA headroom, no LOW confidence, no opaque preblends).

Smoke run, for shape: `formulas\WM_Optimized_30mL_EDP.md` with `--expected-concentrate-ul 6000
--brief generic --json` returned exit 1 in 3.8 s with a 650,677-byte report — `overall: FAIL`, gates
100 PASS / 41 WARN / 6 FAIL / 1 SKIP, `dose_receipt.status: ABSTAINED`, `oav_authority.status: FAIL`.
That is a normal first result; see §5.

**The gate writes two things even when you redirect stdout.** A run appends the freshly bound analysis
block to the formula file itself (`## Pipeline Analysis`, ~270 lines for the smoke formula) and appends
two events to `data/pipeline_audit/events.jsonl`. Add `--no-append-analysis` when you want a diagnostic
run that leaves the formula file alone. If you run the gate inside a scratch worktree, restore the two
files afterwards (`git restore --source=HEAD --worktree -- formulas/<File>.md data/pipeline_audit/events.jsonl`).

### 2.4 Standalone workflow harness

```powershell
& $py scripts\verify_formula_workflow.py --formula-file formulas\<Formula>.md
# narrow to one section of a multi-formula file:
& $py scripts\verify_formula_workflow.py --formula-file formulas\<File>.md --formula 2
& $py scripts\verify_formula_workflow.py --formula-file formulas\<File>.md --name "<partial name>"
```

Verified: `--help` exits 0 and shows `--formula-file` (required), `--formula`, `--name`.

### 2.5 After any code change — quick project verifier

```powershell
& $py scripts\pipeline_audit.py project-verify --quick --json
# before merging or publishing, run the full set (no --quick) and, where relevant,
# --include-docker (Docker is not installed here — see §4)
```

Verified: `project-verify --help` exits 0 and shows `--only`, `--quick`, `--include-docker`, `--output`,
`--json`. The `--quick` run takes about 0.9 minutes and selects 9 checks: engine-compile, engine-lint,
engine-typecheck, formula-artifact-validation, scientific-audit, material-data-validation,
knowledge-rule-validation, golden-formula-regression, golden-api-regression.

In a *fresh* worktree the quick gate is expected to be red for environmental reasons and those are not
code findings. Measured here: `material-data-validation` and `knowledge-rule-validation` failed with
`sqlite3` errors because `data/perfumery_kb.db` is gitignored and absent, and `golden-api-regression`
failed under `poetry run` because that created an empty lane venv (`No module named 'pytest_asyncio'`).
After seeding the KB, `material-data-validation` returned PASS and the API golden passed with the main
Poetry environment (`1 passed, 8 deselected in 3.23 s`). The main checkout's own quick gate is recorded
as `10 passed / 0 failed` in `docs/governance/verification_20260911_full_gate_classification.md`.

## 3. One-time checklist

| Item | State / action |
|---|---|
| `inventory.txt` read | Present, 24,619 bytes, 323 lines at this revision. Read it before dosing; it carries the stock authority. |
| `.venv` Python 3.11 | Present at the path in §1 — CPython 3.11.15. |
| `data/perfumery_kb.db` present | Gitignored (`*.db`). **2,084,864 bytes** in the main integration checkout. Absent in a fresh gate worktree, which instead carried only `perfumery_kb.db-shm` (32,768 B) and `perfumery_kb.db-wal` (0 B). Report the size you actually see rather than assuming. |
| Registry overlay | Present: `configs/complexity/complexity_module_registry_integration_20260910.json` (schema `complexity_module_registry_overlay_v1` — additive unvalidated candidates only; the base registry stays frozen). |
| Regenerate the KB if missing | `& $py -c "from engine.kb_migrate import migrate; print(migrate())"` → verified 11.8 s, produced a 2,101,248-byte database at the default path. Caveat: a regenerated KB is a runtime artifact, **not** a drop-in equivalent of the incubated one — `data/materials/H.yaml` now carries Hedione `vp_25c_pa: 0.09466` while `tests/test_kb_query.py` pins `0.21`, so a freshly migrated database fails two KB-query assertions. |

## 4. Standing rules

- **Quarantined formulas are do-not-mix.** The fail-closed marker is
  `**Status**: QUARANTINED — do not mix or release.` The 2026-09-11 disposition retired 14 quarantine rows
  and added 7 more, and classified 49 `UNBOUND_LEGACY` artifacts as historical/inactive: 21 QUARANTINED,
  zero blocking STALE or TAMPERED. Source: `docs/governance/formula_artifact_dispositions_20260911.md`.
- **STALE artifacts are never cited as current.** A formula whose embedded `## Pipeline Analysis` block
  no longer binds to the current inventory is history, not evidence; regenerate before quoting it.
- **Docker is `NOT TESTED`, never "passed".** Verified in this lane: `docker` is not on PATH and
  `docker --version` fails. Do not install it to make a check go green.
- **Never commit key material.** Credential files must never enter the repository or a push. Correction to
  the task brief: at revision `6a3d77e6` `.gitignore` contains **no** `/incoming_review/openai-api-key*.txt`
  pattern (searched — no match) and `incoming_review\` holds only `worktree_candidates\` and
  `Meaningful_Complexity_Audit_v2.md`. Treat that ignore rule as `NOT PRESENT` and add it before the next
  push rather than relying on it.
- **The OAV-coverage hold is real and unchanged.** Live measurement in this lane:
  `status FAIL_CLOSED_GAPS`, `204` supported / `42` unknown of `246` materials, `oav_coverage_pct 82.927`,
  against the unchanged `>85%` criterion (`docs/governance/repository_verification_comparison_20260909.md`).
  Do not fill the gap with invented physical data and do not lower the threshold.

## 5. How to read a first report

A first report is expected to be red, and the point is a truthful report, not a green one. Read it in this
order:

1. **The dose receipt** — `formulas[0].dose_receipt`, schema `formula-dose-receipt-v1`. `status: BOUND`
   means the formula's doses are bound to the inventory stock contract; `ABSTAINED` or
   `REQUIRED_UNBOUND` means they are not, and `quantity_authority: PLANNED_VOLUME_SCREEN_ONLY`,
   `physical_metrology_authority: false`, `release_authority: false` say what the receipt does not claim.
2. **The OAV-coverage hold** — an explicit fail-closed gap (§4), not a silent pass.
3. **Stock-contract failures** — visible rows, so you can act on them at the bench instead of discovering
   them while pouring.

Everything above is subordinate to a bench result. The pipeline models headspace; it does not measure your
skin, your stock bottle, or your nose.
