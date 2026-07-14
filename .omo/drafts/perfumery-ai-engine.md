---
slug: perfumery-ai-engine
status: approved
intent: unclear
pending-action: implementation
approach: SQLite-backed knowledge engine that consolidates 7 scattered data sources + 8 rule locations + interaction graph + property estimator + formula memory + 10 new science domains into one system. Additive — generates existing Python dicts from DB, pipeline code unchanged. Momus review APPROVED with notes (all incorporated). 11 todos, 6 waves.
---

# Draft: perfumery-ai-engine

## Components (topology ledger)
| id | outcome | status | evidence |
|---|---|---|---|
| T1 | SQLite schema + migration from 7 sources | active | .omo/evidence/task-1 |
| T2 | Material query API (alias resolution, all fields) | active | .omo/evidence/task-2 |
| T3 | Rules DB migration (archetypes, IFRA, fatigue, shifts, skeletons) | active | .omo/evidence/task-3 |
| T4 | Rules query API (get_archetype, check_cross_family, etc.) | active | .omo/evidence/task-4 |
| T5 | Interaction graph extension (3303 existing + new discoveries) | active | .omo/evidence/task-5 |
| T6 | Fragment-based property estimator (Stein-Brown VP, Wildman-Crippen logP) | active | .omo/evidence/task-6 |
| T7 | Formula memory schema + API (store formulas, pipeline results, evaluations) | active | .omo/evidence/task-7 |
| T8 | Failure registry pattern detector (11 encoded patterns + accumulation) | active | .omo/evidence/task-8 |
| T9 | Agent query API / "perfumery brain" (recommend, compatibility, replace, evaluate) | active | .omo/evidence/task-9 |
| T10 | Sync script + pipeline parity tests (zero-regression) | active | .omo/evidence/task-10 |

## Open assumptions (announced defaults)
| assumption | adopted default | rationale | reversible? |
|---|---|---|---|
| Database choice | SQLite | Zero-dependency, built-in, portable, fast for 255 materials | Yes — schema can be migrated to PostgreSQL |
| Sync model | Additive (DB generates Python dicts) | Pipeline code doesn't need to change | Yes — can switch to direct DB reads later |
| Property estimation | Fragment-based (Stein-Brown, Wildman-Crippen) | No ML model needed, deterministic, transparent | Yes — can add ML layer on top |
| Formula memory | SQLite (not vector store) | Simple, co-located with material data | Yes — can extract to separate store |
| Interaction graph coverage | Run pairing agents ONLY for uncovered pairs | Don't waste tokens re-running existing discoveries | Yes — can re-run all pairs |

## Findings (cited)
- 7 scattered data sources mapped: ODT_DATA 316, _PROFILES 271, YAML 255 in-inventory, material_properties.json 232, natural decomposition 38, knowledge_graph 9 files — explore agent task result
- 8+ rule locations mapped: registry.py 30 archetypes, perfume_knowledge.py 85 tokens, pyramid_targets.py 40 families, gates.py 40+ gates with 4 embedded dicts (fatigue 30, Jellinek 75, adaptation 3, skeletons 20+), ifra_safety.py 119 limits, dose_response.py 25 shifts — explore agent task result
- 3 data paths NOT auto-synced — AGENTS.md "Known Data Quality Issues"
- Name normalization inconsistency between inventory_parser and name_utils — AGENTS.md section 4
- 11 failure patterns documented in AGENTS.md — F1 through F11

## Decisions (with rationale)
1. SQLite over PostgreSQL — zero dependency, built-in, sufficient for 255 materials
2. Additive sync (DB generates dicts) over direct DB reads — zero pipeline rewrite risk
3. Fragment-based estimation over ML — deterministic, transparent, no training data
4. 6 waves with parallel execution — T2/T3/T4 parallel after T1, T5/T6 parallel in Wave 3
5. One commit per todo — atomic, independently revertible

## Scope IN
- SQLite database with ~25 tables
- 10 new Python files (knowledge_base, property_estimator, formula_memory, failure_registry, perfumery_brain, kb_schema, kb_migrate, kb_sync, perfumery_brain, rebuild_kb script)
- 10 test files
- Extension of interaction graph via 5 pairing agents for uncovered pairs
- Full test coverage

## Scope OUT (Must NOT have)
- No pipeline rewrite
- No backend/ changes
- No existing file modification (additive only)
- No external dependencies
- No internet requirement after build
- No auto-formulation engine (query/recommendation only)

## Open questions
None — all resolved through exploration.

## Approval gate
status: awaiting-approval
Plan written to .omo/plans/perfumery-ai-engine.md. Awaiting user's explicit okay to proceed with implementation.
