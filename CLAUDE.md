# CLAUDE.md — repo map for Claude sessions

Short on purpose: this file is loaded into every session. Full rules are in `AGENTS.md`; read only the
section your task needs (`grep -n "^## \|RULE" AGENTS.md` lists them).

## Rules that apply to every task (detail in AGENTS.md)
- RULE 0: check stock before building any formula (`inventory.txt` + `engine/inventory_parser.py::parse_current_inventory()`).
- RULE 1: keep stock dose, concentration, ODT, OAV, intensity and liking separate; OAV is never perceived strength.
- RULE 2: no new pipeline entry scripts; extend `scripts/formula_release_gate.py` or `engine/`.
- RULE 3: optimise toward the formula's name and brief, never toward an engine index.
- Editing `engine/ifra_safety.py` means rebinding its hash in `data/governance/ifra_policy_status_20260927.json`.
- Every bench formula carries the BHT 5% w/v in ethanol pre-charge row (120 uL per 30 mL); format in AGENTS.md "Running formulas through the gate".

## Where things are (8.5k tracked files; most are history, not code)
| Path | What |
|---|---|
| `engine/` | formula science (namespace package, pip `requirements.txt`, run from repo root) |
| `backend/app/` | FastAPI Lab app (separate Poetry project; does not import `engine/`) |
| `tests/` | engine and root tests (`pytest tests/...` from repo root) |
| `backend/tests/` | backend tests |
| `scripts/` | gate and pipeline entry points (`formula_release_gate.py`, `pipeline_audit.py`) |
| `data/materials/<LETTER>.yaml`, `data/governance/` | material data, stock snapshots and overlays, policy hashes |
| `formulas/` | formula files |
| `docs/agents/` | agent rules, failure registry |
| `docs/`, `incoming_review/`, `verification_runs/`, `releases/`, `output*/` | history and reports: search, don't browse |

## Commands
- One engine test: `pytest tests/test_x.py -k name` (repo root).
- Backend, in order: `cd backend && poetry run ruff check app && poetry run mypy app --ignore-missing-imports && OPENAI_API_KEY=test-key poetry run pytest`.
- Pre-push gate: `python scripts/pipeline_audit.py project-verify --quick --json`.
- GitHub Actions never start on this repo (billing lock): run checks locally.

## Reading cheaply
- Prefer the digests in `/mnt/project-files/perfume-chem-parse/` (cloud) or `D:\agent-cache` (Kenny's PC) over opening big folders.
- Search with `rg` limited to `engine/ backend/app/ tests/ scripts/` before widening.
