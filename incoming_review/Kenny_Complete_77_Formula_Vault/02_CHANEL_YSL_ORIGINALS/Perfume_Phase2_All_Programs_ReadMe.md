# Perfume Phase 2 · All Programs Master

**Created:** 2026-08-03  
**Master workbook:** `Perfume_Phase2_All_Programs_Master_GPT56_EngineV2.xlsx`  
**Canonical state:** `phase2_perfume_program_state.json`  
**Verification engine:** `verification_engine_v2.py`

## Completed workstreams

| Workstream | Result |
|---|---:|
| Existing Prada complete masculine atlas | 28 formulas retained as the canonical external asset |
| CHANEL Allure lineage | 6 new formulas |
| YSL L’Homme and La Nuit lineage | 14 new formulas |
| Kenny Originals Volume 1 | 6 new formulas |
| Verification Engine V2 profiles | 26 |
| Engine V2 terminal passes | 26 / 26 |
| Iris Grandmasters comparison targets | 18 |
| New formula rows | 1248 |

## Verification Engine V2

The engine now includes:

- Monte Carlo propagation of threshold, release, stock-strength, and phase uncertainty;
- phase-summed computational odor-activity screening;
- material ablation classification;
- ±10%, ±20%, and ±30% dose perturbation;
- cross-formula family, material, and phase collision detection;
- a terminal GPT-5.6 Sol Pro computational gate.

```text
Profiles:                         26
Monte Carlo draws per profile: 1,800
Terminal passes:                  26 / 26
Minimum final score:              90.16
Minimum MC pass probability:      83.8%
High-collision pairs:             1
```

The first engine run did not pass everything. Allure Homme Sport Cologne, L’Homme Eau de Parfum, La Nuit L’Intense, Eau Électrique, and Storax Black Iris required model or architecture revisions. The accepted state is the post-revision state, not a courtesy pass.

## Formula library

Open:

```text
Perfume_Phase2_Formula_Library/index.html
```

Every formula is also supplied as a CSV and Markdown recipe with:

- exact as-supplied 30 mL and 5 mL doses in µL;
- stock strength and label-verification flags;
- bench mixing stage;
- trace-premix flags;
- signature phase;
- Engine V2 score and Monte Carlo probability;
- formula hash.

## Iris and preference model

The workbook includes an 18-target Iris Grandmasters atlas and an interpretable Kenny-fit model. The model uses visible ideal values and weights rather than claiming opaque machine learning from an insufficient personal dataset.

## Prada integration

The existing file-library asset remains authoritative:

```text
Prada_All_Targets_Final_Formula_Book_GPT56_Sol_Pro.xlsx
28 targets
1,399 formula rows
28 computational passes
0 empirical final passes
```

It is intentionally not copied into a second fork.

## Scientific boundary

The package is computationally complete. It does not claim:

- authenticated manufacturer formulas;
- measured commercial-perfume headspace;
- strict empirical OAV;
- blind physical equivalence;
- IFRA or local regulatory clearance;
- skin-use safety.

Those require reference bottles, supplier records, physical compounding, analytical measurement, and sensory testing.
