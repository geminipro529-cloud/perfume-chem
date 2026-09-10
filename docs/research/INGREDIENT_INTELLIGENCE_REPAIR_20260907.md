# Ingredient intelligence repair — 2026-09-07

Scope: local ingredient profiles, their public lookup contract, and eight matching
registry molecular weights. This is not an inventory successor, complete material
database reconciliation, formula revision, sensory validation, or release.

## Implementation plan and ownership

1. Parent is sole editor of `engine/ingredient_intelligence.py`, the eight named
   records in `data/materials/{A,B,E,F,M}.yaml`, this note, and focused tests.
2. Preserve the pre-edit dirty module in a reversible snapshot; retain unrelated
   Pink Pepper, AIMI alias and stock-basis edits. Reproduce failures first.
3. Use primary-source identity evidence and the same-day chemical audit. Correct
   supported entity masses in both profile and registry (pipeline registry wins).
4. Correct muguet roles, restore missing Geranium profile, and expose uncertainty.
5. Repair public lookup of malformed late-intake character/note records. Run
   focused regressions, lint and type checks, then preserve a verification receipt.

## Accepted repairs

- Hydroxycitronellal: heart / character / muguet, with `muguet_character` and
  `floral_heart_body` roles. CAS 107-75-5 and 7-Hydroxycitronellal resolve to that
  chemical. Hydroxycitronellol remains separate, CAS 107-74-4, rose modifier.
  The character-role assignment interprets [BASF's description](https://aroma-ingredients.basf.com/global/en/our-portfolio/muguet/hydroxycitronellal),
  not a measured global usage ranking or requirement for every floral formula.
- Florol: muguet family instead of generic floral, while retaining modifier role.
  The [manufacturer](https://studio.dsm-firmenich.com/product/florolr-pe-966458)
  identifies muguet character and the chemical CAS.
- Geranium EO: previously returned no ingredient profile. It now has an explicit
  natural-mixture rosy/green design profile. Entity MW, VP and logP are absent,
  preserving existing constituent-composite modeling and data-coverage exemptions.
  No Geranium Flower EO alias was added. Character weights are design heuristics,
  not panel scores. Bontoux supplier confirmation remains in the user receipt;
  no Bontoux lot composition is inferred.
- Lilyreal ND: explicitly an opaque preblend; retained numeric surrogates are
  labeled proxies, not a verified chemical entity. [Exact supplier product](https://www.perfumersworld.com/view.php?pro_id=6MG22777).
- Public profiles expose field evidence: source-backed entity mass, legacy
  unverified values, unmeasured ideal gamma, heuristic gamma/hedonics, missing data
  and composite/opaque-product limitations. These labels are not new release gates.
- Fifteen late-intake records had prose in the numeric `character` field and note
  tiers stored in `role`. Public lookup retains prose in `odor_description`,
  returns an empty numeric map when dimensions are unknown, and recovers the
  explicit top/heart/base tier. It does not invent numeric radar scores. Original
  raw intake entries remain intact. Existing carrier classifications are preserved.
- Fixed local typing errors (character maximum, fractional transparency values,
  non-optional profile enumeration). Kept the late PEA threshold import local to
  preserve initialization order and eliminate the E402 lint issue without bypass.

## Molecular weights synchronized in profile and registry

Values are g/mol, conventional entity/formula mass. No product purity, supplier
lot identity, dilution, density, or stock execution authority follows from MW.

| Material | Previous profile | Corrected | Evidence |
|---|---:|---:|---|
| Florol | 154.25 | 172.26 | CAS 63500-71-0, C10H20O2; [PubChem](https://pubchem.ncbi.nlm.nih.gov/compound/3017432) plus manufacturer identity. Manufacturer webpage displays 173, separately retained as a source discrepancy rather than copied. |
| Bourgeonal | 176.25 | 190.28 | C13H18O, CAS 18127-01-0; [PubChem](https://pubchem.ncbi.nlm.nih.gov/compound/64832). |
| Mayol | 166.3 | 156.26 | C10H20O, CAS 13828-37-0; [PubChem](https://pubchem.ncbi.nlm.nih.gov/compound/83763), [manufacturer](https://studio.dsm-firmenich.com/product/mayolr-pe-957230). Preserve cis/product distinctions. |
| Floralozone | 192.26 | 190.28 | [IFF](https://www.iff.com/scent/ingredients-compendium/floralozone/) gives C13H18O and two isomer CAS values. Its displayed 190.1 is not silently substituted for conventional formula mass. |
| Apritone | 178.27 | 220.35 | C15H24O; [Bedoukian](https://bedoukian.com/wp-content/uploads/FR-410-spec-sheet.pdf), same-day CAS lookup 68133-79-9. Isomer/additive composition remains distinct. |
| Allyl Amyl Glycolate | 158.19 | 186.25 | C10H18O3; [PubChem](https://pubchem.ncbi.nlm.nih.gov/compound/106729), [IFF-authored SDS](https://www.johndwalsh.com/wp-content/uploads/2017/12/ALLYL-AMYL-GLYCOLATE-GHS-SDS.pdf). Multiple isomers and additive are not a single pure CID. |
| Ebanol | 220.35 | 208.34 | C14H24O; [Givaudan](https://www.givaudan.com/fragrance-beauty/fragrance-ingredients-business/fragrance-molecules/ebanoltm), same-day CAS lookup 67801-20-1. |
| Ethyl Safranate | 168.23 | 194.27 | C12H18O2; [Givaudan](https://www.givaudan.com/fragrance-beauty/fragrance-ingredients-business/fragrance-molecules/ethyl-safranate). |

The same-day raw PubChem response cache is preserved in
`docs/verification/INVENTORY_CHEMICAL_AUDIT_20260907_pubchem_cas.json` and
`..._pubchem_cids.json`. Some manufacturer re-fetches timed out; the previously
adjudicated audit and current cached entity/formula responses were reused.
Correct existing profile MWs for Peonile, Aurantiol and DPG were retained.

## Unresolved boundaries

Hydroxycitronellal's [BASF technical information](https://download.basf.com/p1/EN_StaticDocuments_5941/en/Technical_Information_Hydroxycitronellal)
reports 0.005472 hPa = 0.5472 Pa **at 20 C**. The legacy model has 0.005 Pa in
a nominal 25 C field. The source value, unit conversion and temperature are now
exposed with `HOLD_REFERENCE_TEMPERATURE_MISMATCH`; the old numeric parameter is
retained, not endorsed. No invented enthalpy or silent temperature conversion.

The generated `data/knowledge_graph/material_properties.json` was not regenerated
or accepted as corrected. Its wrong Florol/Floralozone identity bindings and other
audit findings still need reconciliation. No new formula should rely on those
stale cache records. Other VP/logP/ODT disagreements remain unresolved.

Current stock synchronization remains pending for the confirmed Hydroxycitronellal
bottle identity, Coumarin 10% w/w DPG and Bontoux supplier correction. The profile's
legacy `dilution` default is explicitly **not current stock authority**. No stock
fractions or inventory pins were changed. Historical formulas and bottle events
were not relabeled, recalculated, or authorized for addition.

## Verification and provenance

Initial new regressions: 18 failures, 1 pass before the implementation. Subsequent
integration checks caught the need to preserve Geranium composite exemptions;
this was fixed by leaving unknown single-material physics absent.

Final commands and exact results are in
`docs/verification/INGREDIENT_INTELLIGENCE_REPAIR_20260907.json`.
No full release verifier, physical experiment, merge, commit or push was performed.

Pre-edit module raw SHA-256:
`866fc83b4b77542ed9be26e0038f66e08390ddec218513fc3641debd76bf4930`.
Complete bytes are recoverable from
`docs/verification/INGREDIENT_INTELLIGENCE_20260907_before.py.gz.b64`.
All release, similarity, safety, stability and sensory claims remain NOT TESTED/HOLD.
