# Prada L'Homme Intense — research and design decisions, 2 October 2026

## Outcome

A new 30 mL personal research interpretation was designed from the current inventory: 29 liquid transfers totaling 6,000 µL plus two separate solid weighings totaling 140 mg. The design targets powdery iris, warm tonka/amber, patchouli and sandalwood, with only restrained suede. No authenticated quantitative analysis of the commercial product was obtained, so this is not an exact reconstruction and no numerical similarity claim is made.

The formula and adjacent JSON are PRADA-LHOMME-INTENSE-RESEARCH-BUILD-V1-20261002. This is a ROOT_DESIGN, not a stock-strength revision or delta to an existing bottle. Historical V1/V2 Prada artifacts remain historical and are not silently updated.

## Research hierarchy

1. **Exact target evidence:** Prada's own L'Homme Intense product and Pradasphere pages identify the target architecture. Notes are marketed sensory descriptions, not recovered chemical composition. [P1](https://www.prada.com/ww/en/p/lhomme-prada-intense-edp-100-ml/2A1252_2HC1_F0Z99_P_ML100), [P2](https://www.prada.com/ww/en/pradasphere/fragrances/la-femme-et-l-homme-prada/la-femme-et-l-homme-prada-intense.html).
2. **Material-function evidence:** supplier and manufacturer pages support the possible roles of AIMI, dihydro beta ionone, Orivone, Clearwood, Sandalore and Suederal. They do not prove these materials occur in Prada.
3. **Relevant scientific literature:** Abate et al. (2007), *The enantiomers of Iralia: preparation and odour evaluation*, supports treating methyl-ionone identity and stereochemical composition seriously. It does not make AIMI, alpha ionone, gamma coeur and alpha irone interchangeable. [L1](https://doi.org/10.1016/j.tetasy.2007.04.022).
4. **Psychophysical boundary:** Wakayama et al. (2019) measured human intensity against gas concentration. This does not authorize stock volume or liquid OAV as an intensity input or pleasure objective. No measured curve is claimed applicable to this complete trial. [L2](https://doi.org/10.1021/acs.iecr.9b01225).

Public pages were reviewed on 2026-10-02. No proprietary formula was purchased, no dataset/model was admitted, no model was trained and no formula was smelled. No third-party formula claim is upgraded to authenticated GC-MS evidence.

## Inventory and units

Inventory text SHA-256: `a07a862febe2e6da3b6301a1189b2cb330a55a801f5126b89ccd57751f0591bb`.
Personal-design inventory projection SHA-256: `3ed783092c94aed53b3987583b8131b4b348995bddb82afab13716f47cad0687`.

All 31 selected rows resolve to one matching stock in the current personal design projection, using identity, nominal fraction, basis and carrier, with a physical-form check for Ambrox crystals. Basis codes mass_fraction and volume_fraction map to w/w and v/v respectively; these are not exchanged. Six rows are design-eligible at lower physical-binding authority; this is sufficient for a personal formulation hypothesis, not permission for automated mixer execution. No new stock receipt or inventory write was fabricated.

The already-owned crystals are selected separately from Ambrox Super 25% w/w solution. Heliotropal/Piperonal uses the user's neat solid, not Heliotropin Fleuressence. Current coumarin is 10% w/w DPG, not a remembered 20% DEP stock. Tonka and labdanum are 10% w/w DPG; Siam benzoin is 50% w/w DPG; Safraleine is 10% w/w DPG; neroli is the existing 10% v/v ethanol working stock. The vanillin convention remains nominal.

Volume times w/w fraction is not active volume or exact active mass. Such endpoints are null in the design manifest. Molecular exposure models would require appropriately bound mass/carrier composition and uncertainty; none is invented here.

## Why these materials

- **Iris:** AIMI is the confirmed owned PerfumersWorld 3IW00300 product, CAS 127-51-5. Its supplier description supports powdery violet/floral/woody uses. The proposed 700 µL is an iris-forward hypothesis, not a measured optimum. Its 11.67% share of liquid-stock charge is near the supplier's high typical-use example (11.9%); the supplier does not establish that its percentage basis equals this recipe's volume basis. [M1](https://www.perfumersworld.com/view.php?pro_id=3IW00300).
- **Iris-to-amber continuity:** dihydro beta ionone supplies a woody floral orris bridge, while alpha ionone gives a distinct contour. The smaller Orivone dose limits dry earthy emphasis. These are not proxies for an authenticated Prada iris accord. [M2](https://www.givaudan.com/fragrance-beauty/fragrance-ingredients-business/fragrance-molecules/dihydro-ionone-beta), [M3](https://www.perfumersworld.com/view.php?pro_id=3IA00343).
- **Orivone precaution:** supplier documentation lists a 0.15% w/w fine-fragrance limit. The 20 µL transfer is deliberately restrained; its nominal finished volume fraction is not a mass-based compliance calculation. The full formula has not received an applicable safety review. [M4](https://www.perfumersworld.com/document-list.php?pro_id=3IA00343).
- **Patchouli and sandalwood:** natural patchouli supplies earthy character, Clearwood a cleaner patchouli/creamy-amber extension, Sandalore the sandalwood body and a smaller Ebanol dose a persistent contour. Alternatives such as a Javanol-led sandalwood or Norlimbanol-led dry amber were rejected for this initial softer concept. [M5](https://www.firmenich.com/product/200092526), [M6](https://www.perfumersworld.com/view.php?pro_id=4WX00405).
- **Leather:** the small Suederal/Safraleine accent is explicitly interpretive. Suederal is a commercial mixture; its proprietary composition is unknown. It is not a single chemical with an established molecular weight. [M7](https://www.perfumersworld.com/view.php?pro_id=3UP14351).
- **Tonka/amber:** tonka absolute supplies natural complexity and coumarin a reproducible coumarinic backbone. The low-dose balsamic and powder accents support them without intending a vanilla dessert accord.
- **Air and cushion:** Hedione, the limited muguet/aromatic materials and salicylates support a cosmetic-clean floral heart. Iso E Super gives a transparent woody envelope. One musk, Ethylene Brassylate, supplies powdery cushioning rather than stacking multiple musks for a numerical score.
- **Opening:** modest bergamot and cardamom support lift/cool spice without replacing the iris/amber identity. The small neroli working-stock addition is a restrained clean-floral hypothesis.

The prior alpha-irone objection is respected: no Alpha Irone or Orris Liquid is included. That is a design choice, not a claim of proven absence from the branded perfume. Methyl Ionone Gamma Coeur remains depleted and distinct from AIMI. No Tonalide, Macrolide, Musk Ketone, unowned Kephalis or depleted Polysantol is used.

## Current-engine applicability audit

- The legacy markdown parser supports µL/mL/% formula amounts, not the independent mg table. Its recipe object therefore cannot describe the complete 31-row physical composition. The JSON design retains all rows without converting solids to volume.
- Dihydro beta ionone: Givaudan lists vapor pressure 0.0093 hPa (=0.93 Pa); the local profile/YAML use 0.02 Pa. The manufacturer's displayed value does not establish a matching measurement temperature. This is an unresolved source/context discrepancy, not justification for silently editing the data or treating either drydown as exact.
- Suederal: the local legacy profile gives MW 168.28 and VP 0.01 Pa, while the supplier identifies a mixture. These cannot establish product-level molecular exposure truth.
- Whole essential oils, absolutes and resinoids retain composition uncertainty. A legacy representative molecular weight or threshold is a proxy, not lot truth.
- Authoritative threshold lookup/verification was executed, not regex dictionary merging. Iso E Super has a runtime/verification ethanol threshold conflict; linalool has an explicitly retained source/numeric conflict; several natural/product thresholds are derived or unverified. Dihydro beta ionone's PEER_SINGLE label cites estimation from analogs and is not independently treated as measured evidence.
- Neroli's exact requested label does not return a direct legacy intelligence profile. Do not infer that its gas release or curve is known from inventory ownership.
- Raw/log OAV, heuristic valence, note count, legacy confidence/star/mass-appeal outputs and computed “skin life” are not used to select this formula.

A focused liquid-only gate and its canonical formatting artifact will be linked after execution. Any gate failure remains visible. No unsupported adjustment is made merely to force a generic or original-L'Homme-EDT archetype to pass. There is no exact Intense-specific calibrated model in this review.

## Practical evaluation

Dissolve the two solids in an ethanol precharge, add the existing liquid stocks in basket order, and top up to a measured 30.0 mL. All transfers are at least 20 µL. Inspect clarity; do not treat a cloudy or crystallized mixture as a completed homogeneous trial. Start with blotter comparisons. A short observation at opening, 30 minutes, 2 hours and 4 hours is sufficient to guide a later hypothesis; no lengthy questionnaire, photograph, lot audit or compulsory personal sensory study is imposed here.

Expected character and material jobs are hypotheses. Prada similarity, persistence, liking, physical stability, skin suitability, regulatory compliance and commercial release remain untested or unestablished. Formula/inventory/authority ledgers are not changed by a research run.

## Verification receipt

Fresh checks passed:
- 31 unique material rows: 29 liquids and 2 weighed solids.
- Exact Decimal totals: 6,000 µL liquids; 120 mg Ambrox and 20 mg piperonal, 140 mg solids in total. No mixed-dimension total exists.
- Minimum liquid transfer 20 µL; basket and descending-volume order verified.
- Markdown parser matches every liquid name, dose, fraction, basis and carrier. Literal `neat` is required by the legacy stock grammar; `neat / as supplied` is human-readable but is not recognized as a declared stock by that parser. The table therefore uses `neat`, with the as-supplied qualification explained separately.
- All 31 design stock selections matched the current personal inventory; its bytes and projection hash remain unchanged.
- Analysis did not mutate the formula; opening and closing implementation/reference snapshots matched.
- Existing focused parser regression suite: **38 passed** (pytest-reported 0.73 seconds). No full test suite was run.

Frozen diagnostic run: `output/Prada_LHomme_Intense_Research_20261002/run-36yxusek`.
The existing batch module was invoked in-process with discovery bounded to this one exact formula, one isolated worker, generic brief, 6,000 µL target and 90-second timeout. This does not add a pipeline script or execute the full corpus. The worker uses `--json --no-append-analysis --no-audit`.

Result: **FAIL**, 114 PASS / 27 WARN / 5 FAIL / 2 SKIP. Fresh gate execution: 2.652467 seconds.
The five failures are:
1. Pipeline preflight, aggregating incomplete execution evidence.
2. Exact inventory-stock contract: Ethyl Linalool, Labdanum, Suederal and Tonka lack the canonical physical metadata required for an automated build. Personal ownership/design availability is not denied.
3. Reference claim: the runtime auto-detected **original L'Homme EDT**, not Intense, then asked for geranium/black pepper. This is a target-resolution/applicability limitation, not evidence those additions are needed for this Intense interpretation.
4. Chemistry/stability: unknown because authoritative active mass is unavailable; no measured instability was demonstrated.
5. Phase compatibility: unknown because authoritative active mass is unavailable; no physical incompatibility was demonstrated.

The pre-mix guard returned PASS for this root design with `parent_comparison_available=false`; it did not test equivalence to an earlier formula. Warnings include unknown/derived thresholds, heuristic activity, missing finished matrix, ambiguous natural/product physics, cross-source vapor-pressure discrepancies and incomplete safety coverage. No raw-OAV “overdose” reduction or hedonic-score promotion was performed.

The canonical formatting module was executed against the wrapper's exact `gate_output` in memory, with no source edits. Its complete output is preserved under an explicit legacy/non-authoritative header:
[Liquid-only diagnostic analysis](../../output/Prada_LHomme_Intense_Research_20261002/run-36yxusek/liquid_only_diagnostic_analysis.md).
[Raw result and source binding](../../output/Prada_LHomme_Intense_Research_20261002/run-36yxusek/result_manifest.json).

Hashes:
- Recipe markdown: `015ba01f76004b8e8c2392f9e2be67aeffeb3170a231d6e6be9a79a0031bb211`.
- Complete 31-row JSON design: `39c537afeb7d78cd706492af8ac6928138a73b704620998b2829cdf41029bef8`.
- Opening/closing source snapshot: `f0928a41b1f78ea029c71caa4d3773d46ca00757acf5c5c24e893509b27d603f`.
- Raw gate artifact: `b10dca06c5fce2428b9a03f901915685468b801b36b4ccdb378562d2fe57d4da`.
- Formatted diagnostic: `118b9c9f5e969a3e7afb3f1c568605b074723bb1ff8f5db848b0d4d406b6a65f`.

Scope-limited whitespace checks cover the three new artifacts. A whole-dirty-worktree check encountered permission-denied files inside pre-existing C10 verification fixtures; no permission or cleanup change was made. No full verifier, merge/release readiness, safety approval or physical execution is claimed. Existing formula and inventory truth remains unchanged; only this new design and its research/output artifacts were added.
