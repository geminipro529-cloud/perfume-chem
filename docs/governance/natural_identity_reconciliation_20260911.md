# Natural and opaque-blend identity reconciliation (lane evidence)

Provenance: lane `D:\chatbots\.lanes2-20260910\13-natural-identities`, detached worktree of the
integration repository at `cc2693eb7b76ddac9b0c208c0507b13b7be4ba7f`. Reproduced with
`D:\chatbots\perfume-chem-integration-20260909\.venv\Scripts\python.exe` from the lane root.
Analysis only: no inventory row, formula, or `data/materials` entry was modified.
The body below is the lane deliverable verbatim; it was not re-derived during harvesting.

---
# L13 - Natural and opaque-blend identity reconciliation

Report-only deliverable for the inventory authority. No inventory row, formula, or
`data/materials` entry was modified. All commands ran read-only in this lane
(detached worktree of the integration repo at `cc2693eb`) with
`D:\chatbots\perfume-chem-integration-20260909\.venv\Scripts\python.exe`.
`git status --porcelain` after the analysis shows only `?? _lane_out/`.

## 0. What the audit is counting, and how

Source: `engine/science_audit.py:241-320` (`_build_inventory_oav_coverage_audit_cached`).
For every live owned non-solvent inventory row (`parse_inventory`, 246 rows):

- `oav is not None` -> available (204 rows)
- else `not is_known` -> `unknown_material_identities` (`engine/science_audit.py:290-291`)
- else `is_opaque_preblend` -> `opaque_preblends_without_disclosed_composition` (`:293`)
- else `oav_model == unknown:composite_decomposition_missing` -> `naturals_missing_composite_evidence` (`:296-298`)
- else -> `other_oav_unknowns` (`:300`)

Identity comes from `engine/material_resolver.py:39-65`: a row is "known" only if its
exact label resolves through `get_profile` or the data-spine registry. Registry entries
are keyed by exact casefolded canonical name and alias (`engine/data_spine/material.py:
214-232`), and later duplicates silently overwrite earlier ones ("last wins"). Natural
classification is name-token based (`engine/pipeline/formula_state.py:70-79`, `:603-605`);
opaque classification is token/profile based (`:588-602`). Unsupported natural/opaque
mixtures fail closed at `:1026-1050`.

Reproduction (identical to the counts in the brief):

```
& $py -c "import json; from engine.science_audit import build_inventory_oav_coverage_audit as b; print(json.dumps(b(), indent=1))"
```

Result at `cc2693eb`: status `FAIL_CLOSED_GAPS`, 246 materials, 204 available,
42 unknown, coverage 82.927%. Categories: 24 naturals, 4 opaque preblends,
11 unknown identities, 3 other. Raw output: `L13_live_audit_raw.json`.

## 1. Headline verdicts

1. **The suspected duplicate is real at the identity level, but both rows must stay.**
   `Peppermint EO` (inventory row 72) and `Peppermint Essential Oil` (row 71) are the
   same material identity (Mentha piperita EO; alias bridge at `engine/name_utils.py:170-171`,
   entry aliases at `data/materials/P.yaml:3409-3410`). They are two physically distinct
   stocks: neat (fraction 1.0) and a user-prepared 10% v/v ethanol working stock
   (fraction 0.1; direct confirmation binding at `engine/inventory_parser.py:1649`).
   The audit counts them twice (2 of the 24 "naturals"), so the natural list is
   23 distinct identities wearing 24 labels.
2. **7 of the 11 "unknown identities" are label-bridge gaps, not missing identity data.**
   `data/governance/inventory_user_authority_overlay_20260910_stock_clarifications.json`
   already declares canonical names for the four working stocks (Anisaldehyde,
   Ethyl Maltol, Hexyl Acetate, Helional) and the three tinctures (Vietnamese Benzoin,
   Kenyan Myrrh, Oman Frankincense Ethanol Tinctures), but the inventory rows carry
   strength/process suffixes that the resolver cannot bridge.
3. **3 of the 11 are genuine no-catalogue-entry stocks** (Guaiacwood EO, Methyl Laitone,
   Cinnamon Bark EO - Telvada USDA Organic); one (`Tuberose Base`) is an opaque base with
   no catalogue entry at all. Each has governance/thread evidence that identifies the
   product but not a material-spine identity.
4. **The 24 naturals are a true evidence gap.** None of the 24 has constituent
   decomposition in the 77-profile accepted-composite DB
   (`engine/pipeline/natural_absolute_decomposition.py`) under its own name or any
   catalogue variant label. One near-match needs an authority decision:
   `Grapefruit FCF oil Sicilian` vs the accepted key `grapefruit fcf` (6 constituents).
5. **Catalogue hygiene is the common root cause.** `data/materials` contains 18 names
   with duplicate canonical blocks (37 blocks, last-wins), 10 `EO` / `Essential Oil`
   sibling pairs that were never merged (several shadow each other through the
   canonical-first lookup), one wrong cross-material alias (`tuberose eo` on
   Tuberose Absolute (India)), one dead alias (`cinnamon ... telvada`), and one block
   with fields misindented under `ifra_max_pct_edp`.
6. **Authority asymmetry on tinctures.** `Turkish Storax ... tincture` receives a
   numeric heuristic OAV (1.361) from registry physics even though its final
   dissolved-solids fraction is unknown and the overlay marks tinctures execution-held,
   while the three sibling tinctures fail closed. Pick one treatment.

## 2. Reconciliation tables

Verdict legend: DISTINCT = unique physical material; ALIAS-DUP = same identity as
another row; STRENGTH-VARIANT = same material, separate declared dilution stock;
NO-ENTRY = no material-spine identity; OPAQUE = declared opaque blend.

### 2.1 Naturals missing composite evidence (24 rows)

All 24 have accepted identity but no constituent evidence; none is an identity
duplicate except Peppermint.

| # | Label (inventory.txt row) | Stock | Verdict | Evidence (file:line) | Required action |
|---|---|---|---|---|---|
| 1 | Anise EO (293) | neat | DISTINCT | `data/materials/A.yaml:3470` (aliases anise eo / china); supplier stub `A.yaml:3511` | none (evidence gap) |
| 2 | Basil EO (306) | neat | DISTINCT | `B.yaml:271`; `engine/name_utils.py:187-189` | none |
| 3 | Cabreuva EO (177) | 0.5 mass_fraction / DPG | DISTINCT | `C.yaml:75-77` (alias) | none |
| 4 | Cade Oil Rectified (271) | 0.01 unspecified / DPG | DISTINCT | `C.yaml:112` | none |
| 5 | Caraway Seed Oil (282) | 0.1 mass_fraction / DPG | DISTINCT | `C.yaml:583-585`; `engine/name_utils.py:197` | none |
| 6 | Champaca Flower EO (121) | neat | DISTINCT | `C.yaml:2114`; stub `C.yaml:2155` | merge stub or keep as supplier row |
| 7 | Cypress EO (175) | neat | DISTINCT | `C.yaml:6140-6142`; (Cypress Absolute `C.yaml:6100` is a different product) | none |
| 8 | Elemi EO (280) | neat | DISTINCT | `E.yaml:123-125`; stub `E.yaml:157`; (Elemi Gum `E.yaml:193` distinct) | none |
| 9 | Grapefruit FCF oil Sicilian (38) | neat | DISTINCT, bridge candidate | `G.yaml:1808`; sibling `G.yaml:1760` "Grapefruit FCF"; composite key `grapefruit fcf` (6 constituents) | authority decision: bridge to `grapefruit fcf` or acquire Sicilian-specific data |
| 10 | Hay Absolute (228) | 0.1 unspecified | DISTINCT | `H.yaml:198` | none |
| 11 | Helichrysum EO (85) | neat | DISTINCT | `H.yaml:1470-1471` (aliases helichrysum eo / immortelle eo) | none; keep distinct from Immortelle Absolute (`I.yaml:1144`) |
| 12 | Himalayan Cedarwood EO (202) | neat | DISTINCT | `H.yaml:933-935`; `engine/name_utils.py:179` | none |
| 13 | Magnolia EO (122) | neat | DISTINCT | `M.yaml:426-428` | none |
| 14 | Myrrh EO (263) | 0.5 unspecified / DEP | DISTINCT | `M.yaml:2802-2804`; stub `M.yaml:2844` | none |
| 15 | Nutmeg EO (296) | neat | DISTINCT | `N.yaml:1278-1280`; stub sibling `N.yaml:1312` | merge/alias the EO vs Essential Oil pair |
| 16 | Opoponax Resinoid (262) | 0.5 unspecified / DEP | DISTINCT | duplicate blocks `O.yaml:626` (shell) and `O.yaml:1815` (enriched) | drop shell block |
| 17 | Peppermint EO (72) | 0.1 volume_fraction / ethanol | ALIAS-DUP of row 71 | `P.yaml:3406-3410`; `engine/name_utils.py:171`; receipt binding `engine/inventory_parser.py:1649` | keep both stocks; fix catalogue duplicate `P.yaml:982` vs `P.yaml:3406` |
| 18 | Peppermint Essential Oil (71) | neat | DISTINCT (same identity as 17) | `P.yaml:3406`; profile `engine/ingredient_intelligence.py:3233` | as row 17 |
| 19 | Peru Balsam Resinoid (261) | 0.5 unspecified / DPG | DISTINCT | blocks `P.yaml:1127` (shell) and `P.yaml:3456` | drop shell block |
| 20 | Pine EO (302) | neat | DISTINCT, conflicting duplicate | `P.yaml:3382-3384` (vp 250, odt_air 12, odt_eth 5) vs `P.yaml:1877-1879` "Pine Essential Oil" (vp 180, odt_air 25) | adjudicate one identity and one property set |
| 21 | Pink Pepper EO (285) | neat | DISTINCT | `P.yaml:2222-2224`; stub sibling `P.yaml:2256` | merge/alias EO pair |
| 22 | Sandalwood EO (174) | 0.1 unspecified / DPG | DISTINCT | `S.yaml:1332-1334`; stub sibling `S.yaml:1366` | merge/alias EO pair |
| 23 | Spike Lavender EO (300) | neat | DISTINCT, conflicting duplicate | `S.yaml:3288-3290` (vp 70) vs `L.yaml:906-908` "Lavender Spike Essential Oil" (vp 0.3) | adjudicate one identity and one property set |
| 24 | Tagetes EO (74) | 0.1 unspecified / DPG | DISTINCT | `T.yaml:4055-4057` (aliases include "tagetes essential oil"); stub sibling `T.yaml:76` | merge/alias EO pair |

### 2.2 Opaque preblends without disclosed composition (4 rows)

| # | Label (row) | Stock | Verdict | Evidence | Required action |
|---|---|---|---|---|---|
| 1 | Leather FO (315) | neat | OPAQUE, DISTINCT | `L.yaml:1088` (profile `Leather FO`) | supplier disclosure request; keep fail-closed |
| 2 | Lilyreal ND (114) | neat | OPAQUE, DISTINCT | `L.yaml:2017-2020`; row receipt `engine/inventory_parser.py:1651-1652` | supplier disclosure request; keep fail-closed |
| 3 | Sandalwood Base 3X (173) | neat | OPAQUE, DISTINCT | `S.yaml:3329-3330` (canonical, aliases sandalwood base x3 / sandalwood base); supplier stub sibling `S.yaml:1296` "Sandalwood Base X3" | merge stub; supplier disclosure |
| 4 | Tuberlia Base (83) | neat | OPAQUE, DISTINCT | `T.yaml:4131` (intake batch, mw 190, odt 10/0.02) vs variant-spelling pair `T.yaml:3623` + `T.yaml:3927` "tuberalia base" (mw 220, odt 2.0/0.03) | confirm one spelling/one property set; supplier disclosure |

### 2.3 Unknown material identities (11 rows)

| # | Label (row) | Stock | Verdict | Evidence | Required action |
|---|---|---|---|---|---|
| 1 | Anisaldehyde 10% v/v in ethanol (229) | 0.1 volume_fraction / ethanol | STRENGTH-VARIANT of neat Anisaldehyde (`inventory.txt:249`) | overlay record `INV-USER-20260910-001`, canonical "Anisaldehyde", alias "Anisaldehyde 10%"; parser assertion `engine/inventory_parser.py:1910` | add exact alias for the row label (or strip strength suffix at parse); identity then known, OAV stays modeled |
| 2 | Ethyl Maltol 1% v/v in ethanol (230) | 0.01 volume_fraction / ethanol | STRENGTH-VARIANT of 10% Ethyl Maltol (row 239) | overlay `INV-USER-20260910-002`, alias "Ethyl Maltol 1%"; `inventory_parser.py:1911` | same as row 1 |
| 3 | Hexyl Acetate 1% v/v in DPG (22) | 0.01 volume_fraction / DPG | STRENGTH-VARIANT of Hexyl Acetate (10%) (row 31) | overlay `INV-USER-20260910-003`, alias "Hexyl Acetate 1%"; `inventory_parser.py:1912` | same as row 1 |
| 4 | Helional 10% v/v in ethanol (79) | 0.1 volume_fraction / ethanol | STRENGTH-VARIANT of neat Helional (row 117) | overlay `INV-USER-20260910-004`, alias "Helional 10%"; `inventory_parser.py:1913` | same as row 1 |
| 5 | Vietnamese Benzoin resin ethanol tincture (233) | 0.4 starting-charge mass_fraction, fraction HOLD | DISTINCT declared tincture, not in material spine | overlay `INV-USER-20260910-006` (fraction None, unknown_final_dissolved_solids, execution_ready false); catalogued only as the historical 20% tincture `B.yaml:2938-2942` | keep HOLD; add alias or spine entry labeled as declared tincture (do not inherit 20% entry) |
| 6 | Kenyan Myrrh resin ethanol tincture (235) | 0.2 starting-charge mass_fraction, fraction HOLD | DISTINCT declared tincture, no entry | overlay `INV-USER-20260910-007` | keep HOLD; add spine entry / alias |
| 7 | Oman Frankincense resin ethanol tincture (236) | 0.33 starting-charge mass_fraction, fraction HOLD | DISTINCT declared tincture, no entry; Boswellia species unknown | overlay `INV-USER-20260910-008`; row note (`inventory.txt:236`) | keep HOLD; species unknown is a hard identification gap |
| 8 | Guaiacwood EO (200) | 0.333 declared 1/3 w/w ethanol + DEP | DISTINCT, no entry; receipt conflict | receipt contract `inventory_parser.py:2261-2294` asserts fraction 0.33 with basis `unspecified` and carrier `""`; row 200 declares 1/3 w/w mass basis with ethanol + DEP (2026-09-01 correction) | reconcile receipt vs row text (successor receipt); keep dosing HOLD until basis authority is single-sourced |
| 9 | Methyl Laitone (247) | 0.2 unspecified, HOLD | DISTINCT, no entry | supplier receipt `data/governance/inventory_supplier_product_resolution_20260910_liffarome_methyl_laitone.json` (PW SKU 5VD10871 is a separate 10% DPG product); row note `inventory.txt:247` | keep HOLD; add spine entry after basis/carrier resolved |
| 10 | Cinnamon Bark EO - Telvada USDA Organic (295) | neat | DISTINCT; dead alias | `engine/name_utils.py:159-160` maps to "cinnamon bark eo - telvada usda organic" but no catalogue entry exists under that name; generic siblings `C.yaml:2623` (Cinnamon Bark EO) and `C.yaml:2657`; distinct from Cassia (`inventory.txt:308`) | fix the dead alias to target `Cinnamon Bark EO` (or create a Telvada lot entry); keep no-substitution note |
| 11 | Tuberose Base (143) | neat | OPAQUE, NO-ENTRY | `is_opaque_preblend` true via name token; classification order puts it here because `is_known` is false (`engine/science_audit.py:290-293`) | create identity entry or supplier disclosure; distinct from Tuberlia Base (`T.yaml:4131`) and Tuberose EO / Absolute |

### 2.4 Other OAV unknowns (3 rows, not identity issues)

`Aldehyde C-18` (rows 253/254), `Caryophyllene Acetate` (310), `Liffarome` (75):
resolved identities (`C.yaml:1030`, `L.yaml:1455`, registry hits) with all physics
missing (density/mw/logp/vp/odt), so the monomolecular model returns no OAV. These are
physics-evidence gaps, not identity reconciliation items.

## 3. Duplicate and conflict annex

### 3.1 The Peppermint pair in full

| Fact | Evidence |
|---|---|
| Row 71 = neat `Peppermint Essential Oil (Mentha piperita, India)`, added 2026-06-15 | `inventory.txt:71` |
| Row 72 = `Peppermint EO (10% v/v in ethanol)`, user-prepared separate stock | `inventory.txt:72`; binding `engine/inventory_parser.py:1649` |
| One identity: alias table maps peppermint eo and the India-suffixed label to `peppermint essential oil` | `engine/name_utils.py:170-171` |
| Enriched catalogue entry carries aliases incl. `peppermint eo` | `data/materials/P.yaml:3406-3410` |
| Older shell block (all null, user_in_inventory false) duplicates the canonical name | `data/materials/P.yaml:982` |
| Registry keeps the later block only because of load order | `engine/data_spine/material.py:219-224` |
| Both rows resolve to the same canonical material and both fail closed for missing composite evidence | audit probe (`L13_probe_out.json`) |

Disposition: keep both physical stocks (they differ in dilution and carrier), remove or
merge the shell catalogue block, and record row 72 explicitly as a dilution stock of the
same material identity rather than as an independent material. Do not "fix" this by
deleting row 72: that would destroy a user-confirmed physical stock.

### 3.2 Duplicate canonical blocks in `data/materials` (18 names, 37 blocks)

Last-wins means the later block silently replaces the earlier one. Pairs where both
blocks carry chemistry need field-level adjudication; shell+enriched pairs need the
shell removed or merged.

| Canonical (casefolded) | Blocks (file:line, flags) |
|---|---|
| birch tar rectified | B.yaml:1650 (chem, inv) + B.yaml:1763 (chem, inv) |
| cassia essential oil | C.yaml:1201 (shell) + C.yaml:6202 (chem, inv) |
| immortelle absolute | I.yaml:157 (shell) + I.yaml:1144 (chem, inv) |
| isobutavan | I.yaml:686 (shell) + I.yaml:1187 (chem, inv) |
| jasmine sambac blossoms | J.yaml:470 (shell) + J.yaml:770 (chem, inv) |
| labdanum resinoid | L.yaml:141 (chem, inv) + L.yaml:293 (chem, inv) |
| mimosa absolute | M.yaml:2133 (shell) + M.yaml:2881 (chem, inv) |
| neroli eo | N.yaml:472 + N.yaml:1498 + N.yaml:1520 (three chem/inv blocks) |
| opoponax resinoid | O.yaml:626 (shell) + O.yaml:1815 (chem, inv) |
| osmanthus absolute | O.yaml:1449 (shell) + O.yaml:1705 (chem, inv) |
| peppermint essential oil | P.yaml:982 (shell) + P.yaml:3406 (chem, inv) |
| peru balsam resinoid | P.yaml:1127 (shell) + P.yaml:3456 (chem, inv) |
| phenyl ethyl acetate | P.yaml:1463 (shell) + P.yaml:3298 (chem, inv) |
| rose de mai absolute | R.yaml:806 (no chem) + R.yaml:1485 (chem, inv) |
| tonka bean absolute | T.yaml:3164 (shell) + T.yaml:4106 (chem, inv) |
| tonkarome | T.yaml:3241 (shell) + T.yaml:3885 (chem, inv) |
| tuberalia base | T.yaml:3623 (shell) + T.yaml:3927 (chem, inv) - distinct from the "Tuberlia Base" intake block at T.yaml:4131 |
| tuberose absolute | T.yaml:3659 (shell) + T.yaml:3969 (chem; fields after `ifra_max_pct_edp:` are misindented, so `user_in_inventory`, families, character, notes, provenance are swallowed) |

### 3.3 EO / Essential Oil sibling pairs never merged (10)

| Inventory label | Enriched entry | Sibling entry | Bridge status |
|---|---|---|---|
| Anise EO | A.yaml:3470 (aliases anise eo, china) | A.yaml:3511 "Anise Essential Oil China" (supplier stub) | none needed for the row; stub is orphaned |
| Champaca Flower EO | C.yaml:2114 | C.yaml:2155 stub | none needed; stub orphaned |
| Elemi EO | E.yaml:123 | E.yaml:157 stub | none needed; stub orphaned |
| Myrrh EO | M.yaml:2802 | M.yaml:2844 stub | none needed; stub orphaned |
| Nutmeg EO | N.yaml:1278 | N.yaml:1312 stub (no aliases) | no cross-alias: two live canonicals for one commerce product |
| Pine EO | P.yaml:3382 "pine eo" (alias Pine EO) | P.yaml:1877 "Pine Essential Oil" (aliases Pine EO, Pine Oil, Pine Needle EO) | alias shadowed by canonical; conflicting physics (vp 250 vs 180) |
| Pink Pepper EO | P.yaml:2222 | P.yaml:2256 stub | no cross-alias |
| Sandalwood EO | S.yaml:1332 | S.yaml:1366 stub | no cross-alias |
| Tagetes EO | T.yaml:4055 (aliases include tagetes essential oil) | T.yaml:76 stub | alias shadowed by stub canonical |
| Spike Lavender EO | S.yaml:3288 (alias Spike Lavender EO) | L.yaml:906 "Lavender Spike Essential Oil" (aliases Spike Lavender EO, Lavender Spike EO) | alias shadowed by canonical; conflicting physics (vp 70 vs 0.3) |

### 3.4 Aliases, spelling variants, and block defects

- Wrong cross-material alias: `Tuberose Absolute (India)` claims alias `tuberose eo`
  (`data/materials/T.yaml:4015`), while the intended EO entry `Tuberose EO (volume
  level grade)` also claims it (`T.yaml:4167`). Registry alias assignment is last-wins,
  so this is order-dependent. Remove the alias from the absolute.
- Dead alias: `engine/name_utils.py:159-160` maps Telvada labels to a canonical string
  that has no entry; the parsed row label additionally loses the `(neat)` suffix, so
  even the existing mapping cannot fire.
- Spelling pair: `Sandalwood Base 3X` (`S.yaml:3329`, inventory row) vs
  `Sandalwood Base X3` (`S.yaml:1296`, supplier stub); `engine/name_utils.py:193`
  already normalizes the two spellings - the catalogue does not.
- `Tuberlia Base` (`T.yaml:4131`) vs `Tuberalia Base` (`T.yaml:3623`, `T.yaml:3927`):
  same trade product name with different spelling and different physics (mw 190 vs 220;
  odt_air 10/0.02 vs 2.0/0.03). Both declare `user_in_inventory: true`.
- Additional variant candidates found by normalized-name clustering (not adjudicated
  here): `D-Limonene` (D.yaml:118) vs `Limonene` (L.yaml:2230);
  `Lime Distilled EO` (L.yaml:2627) vs alias at L.yaml:2065;
  `Cyclamen Aldehyde` (C.yaml:5901) vs `Cyclimal Aldehyde` alias (C.yaml:6031);
  `Ylang Comoros Complete EO` (Y.yaml:75) vs `...F3255` (Y.yaml:110);
  `Damascone Beta` (D.yaml:267) vs `Beta Damascone` (B.yaml:1467);
  `Heliotropin` vs `Heliotropal` (H.yaml:419, H.yaml:1444);
  `Labdanum` / `labdanum resinoid` / `labdanum resinoid (10% in dpg)` / `Labdanum
  Resinoid` (L.yaml:111, 141, 152, 293).

### 3.5 Composite-evidence bridge test for the 24 naturals

`L13_composite_bridge.py` tested every catalogue variant label (canonical names and
aliases) for each of the 24 against `get_constituents`. Result: zero hits. The only
near-match in the accepted DB is `grapefruit fcf` (6 constituents) for
`Grapefruit FCF oil Sicilian`. `cedarwood eo` exists but is a different species from
Himalayan cedarwood, so it is not a bridge.

## 4. Prioritized fix list (report-only, for the inventory/material-data authority)

P0 - correctness blockers:

1. Resolve the 18 duplicate canonical blocks (section 3.2). Start with the three names
   where both blocks carry chemistry (`birch tar rectified`, `labdanum resinoid`,
   `neroli eo`), plus the `tuberose absolute` misindented block (T.yaml:3969), because
   last-wins currently discards one property set silently in those cases.
2. Adjudicate the two competing-identity pairs with conflicting physics: Pine
   (`P.yaml:3382` vs `P.yaml:1877`) and Spike Lavender (`S.yaml:3288` vs `L.yaml:906`).
3. Reconcile the Guaiacwood receipt conflict: receipt (`inventory_parser.py:2261-2294`)
   asserts basis `unspecified` / carrier empty, while row 200 declares 1/3 w/w mass
   basis with ethanol + DEP. Ship a successor receipt rather than editing either in place.
4. Remove the wrong alias `tuberose eo` from `T.yaml:4015`.

P1 - fixes that shrink the audit honestly:

5. Add exact alias bridges (or strip declared strength/process suffixes at parse) for
   `Anisaldehyde 10% v/v in ethanol`, `Ethyl Maltol 1% v/v in ethanol`,
   `Hexyl Acetate 1% v/v in DPG`, `Helional 10% v/v in ethanol`. Expected effect: those
   four working stocks move out of `unknown_material_identities`. The three tinctures
   need a spine entry (or an alias onto a new declared-tincture entry) before any bridge
   can work; until then they should remain visibly fail-closed quantitative HOLDs.
6. Fix the dead Telvada alias (`engine/name_utils.py:159-160`) to target
   `Cinnamon Bark EO` (C.yaml:2623) or a new lot-specific entry, preserving the
   no-substitution note.
7. Merge or alias the EO / Essential Oil sibling pairs (section 3.3) and the
   Sandalwood Base 3X / X3 and Tuberlia / Tuberalia spelling variants.
8. Decide the Turkish Storax treatment: either fail close the bulk-proxy OAV like its
   three siblings until the final dissolved-solids fraction is known, or record why
   Storax alone is exempt. Current state computes OAV 1.361 from registry physics.

P2 - evidence acquisition and policy:

9. Composite evidence: 23 natural identities (24 rows) have no constituent
   decomposition. Acquire literature profiles (follow the existing accepted-profile
   format) or keep them fail-closed; do not restore bulk-proxy OAVs for them.
10. Decide the `Grapefruit FCF oil Sicilian` -> `grapefruit fcf` bridge (accepted DB
    already carries 6 constituents) or commission Sicilian-specific data.
11. Supplier disclosure requests for the five opaque bases: Leather FO, Lilyreal ND,
    Sandalwood Base 3X, Tuberlia Base, Tuberose Base.
12. Keep the three physics-only unknowns (Aldehyde C-18, Caryophyllene Acetate,
    Liffarome) in a physics-gap queue, not an identity queue.

## 5. Evidence index (files in this lane)

| File | Content |
|---|---|
| `L13_naturals.md` | this report |
| `L13_live_audit_raw.json` | reproduced audit at cc2693eb (24/4/11/3) |
| `L13_probe.py` / `L13_probe_out.json` | per-row resolution: canonical, known, opaque, dilution, model source |
| `L13_evidence_locator.py` / `L13_evidence_out.json` | inventory row numbers, YAML canonical/alias lines, duplicate blocks, composite counts |
| `L13_dupcheck.py` / `L13_dupcheck.json` | rigorous duplicate-canonical table (18 names, 37 blocks) |
| `L13_pair_dump.py` / `L13_pair_dump.json` | field-level dumps of the EO/EOil pairs and reported entries |
| `L13_variant_clusters.py` / `L13_variant_clusters.json` | normalized-name clusters across all 246 inventory rows |
| `L13_composite_bridge.py` / `L13_composite_bridge.json` | composite-evidence bridge test for the 24 naturals |
| `L13_evidence_hits.txt`, `L13_patterns.txt` | raw pattern search output |

Lane integrity note: after the analysis runs, `git status` in this lane lists 13
`data/governance/*.json` files as modified with mtimes 2026-09-11 00:29:21, but every
one of their raw blobs is byte-identical to the committed index blob (verified per file
with `git ls-files -s` vs `git hash-object`, and `git diff --quiet` exits 0 for each).
The delta is line-ending representation only under `core.autocrlf=true`; there is no
content drift. The analysis itself is read-only (verified by re-running the module
imports and observing no further mtime changes). `inventory.txt`, `data/materials`,
and the main integration and canonical repos show no writes from this lane.

## What this means for the approach

Identity reconciliation is a prerequisite for every coverage number that comes next.
The audit's 24/4/11 split currently mixes three different problems: true evidence gaps
(the 23 natural identities, the opaque bases), pure label-bridge gaps (four working
stocks and three tinctures that the user already confirmed), and catalogue hygiene
defects (18 names with duplicate canonical blocks, 10 unmerged EO siblings, one wrong alias) that make the
resolver's answers order-dependent. Until the catalogue and alias layer is
single-sourced, any downstream work that reads "unknown material" or "missing
composite evidence" - the coverage-aware radar lane included - will inherit both
false unknowns and false distinctness. The cheapest high-value move is the P0/P1
cleanup plus a re-run of this same audit: the four working stocks should leave the
unknown list immediately, the tinctures should become honestly labeled
quantitative-HOLD stocks, and the remaining naturals should stand as genuine
evidence gaps that no renormalized radar or bulk proxy may paper over.
