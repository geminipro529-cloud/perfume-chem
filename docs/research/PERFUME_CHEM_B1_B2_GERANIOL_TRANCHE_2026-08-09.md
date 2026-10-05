# Perfume-Chem B1/B2 Geraniol Staging Tranche — 2026-08-09

## Outcome

The first inventory-prioritized psychophysics tranche is implemented as
append-only staging candidates. It creates no canonical database rows, changes
no property authority, and cannot promote itself.

The deterministic path is:

```text
pinned DREAM TrainSet bytes
  -> B1 source-document candidate
  -> two B1 extraction-record candidates
  -> two condition-specific B2 property-observation candidates
  -> explicit no-conflict / no-selection review
  -> WITHHELD_UNKNOWN authority
```

Geraniol was selected because it is present as neat owned stock, has an exact
source compound identifier, and has 49 subject ratings at each of two declared
liquid dilutions in the pinned training data. The source observation is scoped
to the chemical entity and is not bound to the user's supplier product, lot, or
physical stock bottle.

## Primary evidence and interpretation boundary

The underlying study presented 1 mL of each diluted molecule in paraffin oil in
vials. Participants sniffed the vial and used a computerized slider translated
to a 0–100 scale. The study retained 55 participants for its published analysis;
the pinned DREAM training table exposes 49 ratings for each selected Geraniol
condition. These are human psychophysical ratings, not measured airborne
concentrations or detection thresholds.

- Keller and Vosshall, *Olfactory perception of chemically diverse molecules*
  (2016): <https://pmc.ncbi.nlm.nih.gov/articles/PMC4977894/>
- Keller et al., *Predicting human olfactory perception from chemical features
  of odor molecules* (2017):
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC5455768/>
- Pinned DREAM repository revision:
  <https://github.com/dream-olfaction/olfaction-prediction/tree/fb47cb343cdfd5cd8b06b33161dfa8b82c0319c6>
- PubChem Geraniol identity, CID 637566 / CAS 106-24-1 / InChIKey
  GLZPCOQZEFWAFX-JXMROGBWSA-N:
  <https://pubchem.ncbi.nlm.nih.gov/compound/637566>
- EPA CompTox/ChemExpo Geraniol crosswalk, DTXSID8026727 / CAS 106-24-1:
  <https://comptox.epa.gov/chemexpo/chemical/DTXSID8026727/>

The primary-method and identity crosswalk URLs are citation metadata in this
slice, not pinned source bytes. That limitation is carried into every B2
candidate as a quality flag and canonicalization blocker.

## Pinned source identity

| Item | Value |
|---|---|
| Repository commit | `fb47cb343cdfd5cd8b06b33161dfa8b82c0319c6` |
| `TrainSet.txt` bytes | `3,592,988` |
| `TrainSet.txt` SHA-256 | `ae43841013a9c5ecb3975953b85e5965663d416d2445178e86ad577d907575a0` |
| License SHA-256 | `3715526fcaac1997011166204c67e662104ee10242988c1c627de58ac9cb8d49` |
| Normalized manifest SHA-256 | `3ba22a99b2159a8f641efcdc9ec6a179161fcd45b39150b15aae2a8fad1de1d4` |
| Staging bundle SHA-256 | `5e55a7dcf441cd1af45afd55a7f66a69e152ececda86033d742fa04d123f96f1` |

The manifest rights statement applies only to the repository `LICENSE` and
`TrainSet.txt`. It does not clear third-party descriptor files.

## Staged observations

| Source dilution | Nominal liquid fraction | n | Mean | Sample SD | SEM | State |
|---|---:|---:|---:|---:|---:|---|
| 1/1,000 | 0.001 | 49 | 70.897959183673 | 25.220068809349 | 3.602866972764 | `STAGED / CANDIDATE_ONLY` |
| 1/100,000 | 0.00001 | 49 | 32.448979591837 | 31.789713499082 | 4.541387642726 | `STAGED / CANDIDATE_ONLY` |

Each extraction retains the exact physical TSV row numbers, selected columns,
full heading context, subject pseudonym, original rating text, parsed rating,
condition, sample statistics, parser version, ambiguity flags, reserved B2
observation ID, and input/output/record SHA-256 digests.

The two distributions are not a conflict because their declared liquid
dilutions differ. They are not averaged. The selection record is explicit:

- `selection_kind = NONE`;
- `authority_state = WITHHELD_UNKNOWN`;
- every candidate is excluded from authority pending canonical B1 linkage and
  scoped human review;
- permitted wording is limited to source-linked human odor-intensity ratings.

## Hard authority holds

The staged data must not be interpreted as:

- ODT or OAV;
- airborne or headspace concentration;
- a complete concentration-response curve;
- perfume similarity or sensory validation;
- supplier-grade or user-lot evidence;
- IFRA/safety evidence;
- formula or release authority.

No row was written to `data/perfumery_kb.db`, the backend canonical B1/B2
tables, inventory, formulas, safety data, material YAML, or generated runtime
properties.

## Verification

- DeepLuna Chat read-only contract audit:
  `DS-ebc342c674e4e8f296e5b7bbf7866c9a`; its verified finding was that B1
  extraction fields and B2/conflict/selection staging were missing before this
  change.
- Focused tests: `14 passed` in
  `tests/test_scientific_source_ingestion.py`.
- Ruff: passed for the changed Python surfaces.
- Compile check: passed.
- Real-bundle replay: all 10 reports were byte-identical.
- Candidate self-hashes: two B1 extraction records, two B2 observations, and
  one conflict/selection review independently recomputed successfully.
- Protected hashes remained unchanged:
  - `data/perfumery_kb.db`:
    `5A779F9D6850345D72DE3C8265D4330C50DAC529968B38BC9B08720B5DA63FE1`;
  - `inventory.txt`:
    `DC3C7FFC6E27711AA38D26BD3AEF09B7046F1834353E7171EB78729FBD2CC4EC`.

## Next high-value gate

Pin the method paper and official identity crosswalk bytes as distinct B1 source
versions, then add supplier product/lot evidence for the user's Geraniol stock.
Only after those records are reviewed and accepted for the exact psychophysics
scope should a canonical B1-to-B2 loader be considered. This preserves the
chemical-entity observation without falsely promoting it to the user's physical
material or to ODT/OAV authority.
