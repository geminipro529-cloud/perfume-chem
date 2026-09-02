# Bounded Formula-Artifact Repair Plan

**Scope:** repair derived export artifacts only. Do not change canonical formula parts, select a formula, admit quarantined sources, deploy runtime hardening, or claim physical/sensory authority.

## R1. Exact-decimal dose export

Recompute every derived dose field from canonical `parts_per_1000 × concentrate_ul / 1000` using canonical decimal strings. Do not reuse rounded display values as calculation inputs. Issue a versioned successor artifact and regenerate the affected artifact/formula hashes while preserving the current parent hashes as ancestry.

| Perfume | Residual µL | Required state |
|---|---:|---|
| DHP25 | -0.0007 | `RECOMPUTE_DERIVED_DOSE_EXPORT` |
| AHS | -0.0012 | `RECOMPUTE_DERIVED_DOSE_EXPORT` |
| ELIXIR | -0.0001 | `RECOMPUTE_DERIVED_DOSE_EXPORT` |
| LHOMME | -0.0018 | `RECOMPUTE_DERIVED_DOSE_EXPORT` |
| LANUIT | -0.0002 | `RECOMPUTE_DERIVED_DOSE_EXPORT` |
| BDCP | 0.0001 | `RECOMPUTE_DERIVED_DOSE_EXPORT` |

DHI12, EB, and EE already reconcile exactly at the stored export precision.

## R2. Stock-lineage closure

Close the following operation-scoped hold classes before quick verification:

| Hold class | Rows |
|---|---:|
| LABEL_STRENGTH_CONFLICT | 3 |
| LOT_OR_LABEL_DETAIL_OPEN | 11 |
| PLANNED_ACQUISITION_OR_PHYSICAL_PENDING | 9 |
| PREPARE | 24 |
| PREPARE_AND_VERIFY | 1 |
| SPECIES_UNRESOLVED | 1 |
| VERIFY_FIRST | 14 |

Each row must bind to exact stock identity, declared strength/basis, lot or bottle reference, preparation receipt where required, and exact dose evidence. Product-basis materials remain opaque named products and must not receive invented composition.

## R3. Runtime acceptance

After an evidence-accepted V20 hardening implementation is deployed under `cheapluna-chat / DIRECT_PRO / NO_LUNA`, run repository-native quick verification against the successor formula artifacts. DeepLuna Fast and alternate fallbacks remain disabled.

## R4. Revalidation outputs

Rerun formula-file hash closure, exact-decimal arithmetic, stock-lineage gates, formula-signature views, anti-chassis views, ratio-bound n-ary records, and quick-verification gating. Keep all complexity dimensions separate and retain `HOLD` for every unclosed authority.
