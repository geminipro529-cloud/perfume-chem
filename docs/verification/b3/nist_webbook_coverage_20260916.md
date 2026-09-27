# B3 cached NIST WebBook coverage

Decision: **READY for evidence installation; scientific/runtime promotion remains HOLD**.

This proposed evidence record covers the 17 exact-CAS B3 intake entries. It is a collection and validation table only. The retained cached packet under `output/worklist_20260916/b3_luna/` is the source-of-record for the bytes; no new network request is made by the validator.

## Traceability and contract

- Intake: `output/worklist_20260916/b3_luna/intake_payload.json`; SHA-256 `0d81c5fe4e97c1aa468de0920760657c28a515bf186972ee293607800ad0357d`.
- Retrieval manifest: `output/worklist_20260916/b3_luna/retrieval_manifest.json`; SHA-256 `096625a80f9e656a3922fd37f4ee5a053bc38875eaa845149fb9daab10a94494`.
- Existing packet receipt: `output/worklist_20260916/b3_luna/validation.json`; SHA-256 `7864b347d5d69e473672f6784dcfa9d85cf43958f7682553a16f34f945b65fc3`; stored status `PASS`.
- Proposed validator: `scripts/validate_nist_webbook_coverage.py`; it reads cached files only and fails closed on hash, endpoint, identity, table, unit, status, or null-evaluation drift.
- NIST endpoint binding: `https://webbook.nist.gov/cgi/cbook.cgi?ID=C<cas-digits>&Units=SI&Mask=4`.
- Antoine convention: `log10(P) = A - B / (T + C)` with pressure in bar and temperature in K, as published by NIST.
- Temperature rule: the interval is inclusive. Evaluate at 298.15 K only when `lower <= 298.15 <= upper`; otherwise retain `evaluation_25c_status=NOT_COVERED` and `vp_pa_25c=null`. No extrapolation.
- Identity rule: natural oils and the 10% tuberose dilution remain exact mixture records; no component or surrogate CAS is substituted.

## Per-CAS coverage

| Material | CAS | Cached source | NIST identity / page state | Coverage status | Antoine window (K) | A / B / C | Units | 298.15 K in window | 25 C VP (Pa) |
|---|---|---|---|---|---|---|---|---:|---:|
| Citronellyl Acetate | 150-84-5 | `C150845.html` `13996afbc121…` | 6-Octen-1-ol, 3,7-dimethyl-, acetate | `ANTOINE_OUTSIDE_25C` | 347.8 to 490.0 | 6.30484 / 2855.761 / -36.775 | bar / K | NO | `null` |
| Neryl Acetate | 141-12-8 | `C141128.html` `681c31f60424…` | 2,6-Octadien-1-ol, 3,7-dimethyl-, acetate, (Z)- | `PHASE_DATA_WITHOUT_VP_FIT` | — | — | — | — | `null` |
| Anisyl Acetate | 104-21-2 | `C104212.html` `9524d65e29a5…` | Benzenemethanol, 4-methoxy-, acetate | `PHASE_DATA_WITHOUT_VP_FIT` | — | — | — | — | `null` |
| Dimethyl Benzyl Carbinol | 100-86-7 | `C100867.html` `8971a490345f…` | Benzeneethanol, α,α-dimethyl- | `PHASE_DATA_WITHOUT_VP_FIT` | — | — | — | — | `null` |
| Phenyl Ethyl Dimethyl Carbinyl Acetate | 103-07-1 | `C103071.html` `0aa8a055c027…` | Dimethyl phenylethyl carbinyl acetate | `RECORD_WITHOUT_PHASE_DATA` | — | — | — | — | `null` |
| Hexyl Cinnamic Aldehyde (HCA) | 101-86-0 | `C101860.html` `ea1c08c5fea1…` | Octanal, 2-(phenylmethylene)- | `PHASE_DATA_WITHOUT_VP_FIT` | — | — | — | — | `null` |
| Alpha Terpineol | 98-55-5 | `C98555.html` `6494073e48fc…` | α-Terpineol | `ANTOINE_OUTSIDE_25C` | 357.0 to 490.1 | 4.42892 / 1844.962 / -74.617 | bar / K | NO | `null` |
| Tetrahydro Muguol | 41678-36-8 | `C41678368.html` `be0b91d2da87…` | Registry Number Not Found | `CAS_RECORD_NOT_FOUND` | — | — | — | — | `null` |
| Linalool Oxide | 5989-33-3 | `C5989333.html` `270608e29c88…` | 2-Furanmethanol, 5-ethenyltetrahydro-α,α,5-trimethyl-, cis- | `RECORD_WITHOUT_PHASE_DATA` | — | — | — | — | `null` |
| Hindinol | 28219-60-5 | `C28219605.html` `9214cff1606e…` | Registry Number Not Found | `CAS_RECORD_NOT_FOUND` | — | — | — | — | `null` |
| Cedroxyde | 71735-79-0 | `C71735790.html` `5bd3d3c38d36…` | Registry Number Not Found | `CAS_RECORD_NOT_FOUND` | — | — | — | — | `null` |
| Vetiveryl Acetate | 62563-80-8 | `C62563808.html` `8b53aff64c43…` | Registry Number Not Found | `CAS_RECORD_NOT_FOUND` | — | — | — | — | `null` |
| Benzyl Alcohol (BA) | 100-51-6 | `C100516.html` `f73c16e133a6…` | Benzyl alcohol | `ANTOINE_OUTSIDE_25C` | 395.67 to 478.56 | 4.47713 / 1738.9 / -89.559 | bar / K | NO | `null` |
| Caraway Seed Essential Oil | 8000-42-8 | `C8000428.html` `9f5a303ea411…` | Registry Number Not Found | `CAS_RECORD_NOT_FOUND` | — | — | — | — | `null` |
| Guaiacwood Essential Oil | 8016-23-7 | `C8016237.html` `995bd005b504…` | Registry Number Not Found | `CAS_RECORD_NOT_FOUND` | — | — | — | — | `null` |
| Ylang Madagascar Complete ORGANIC Ess. oil | 8006-81-3 | `C8006813.html` `a6dfff992843…` | Registry Number Not Found | `CAS_RECORD_NOT_FOUND` | — | — | — | — | `null` |
| Tuberose Absolute 10% in TEC | 8024-05-3 | `C8024053.html` `a2426e866061…` | Registry Number Not Found | `CAS_RECORD_NOT_FOUND` | — | — | — | — | `null` |

The 17 rows classify as: 3 `ANTOINE_OUTSIDE_25C`, 4 `PHASE_DATA_WITHOUT_VP_FIT`, 2 `RECORD_WITHOUT_PHASE_DATA`, and 8 `CAS_RECORD_NOT_FOUND`. All 17 retain `NOT_COVERED` and a null 25 C VP.

## Antoine rows

| CAS | HTML table / locator | Published window (K) | A | B | C | Reference | Comment | 298.15 K |
|---|---|---:|---:|---:|---:|---|---|---:|
| 150-84-5 | table 2 / cached HTML | 347.8 to 490. | 6.30484 | 2855.761 | -36.775 | Stull, 1947 | Coefficents calculated by NIST from author's data. | **NO** |
| 98-55-5 | table 3 / cached HTML | 357.0 to 490.1 | 4.42892 | 1844.962 | -74.617 | Pickett and Peterson, 1929 | Coefficents calculated by NIST from author's data. | **NO** |
| 100-51-6 | table 4 / cached HTML | 395.67 to 478.56 | 4.47713 | 1738.9 | -89.559 | Dreisbach and Shrader, 1949 | Coefficents calculated by NIST from author's data. | **NO** |

The three published Antoine windows begin at 347.8 K, 357.0 K, and 395.67 K, respectively. None contains 298.15 K, so no Antoine value is evaluated or promoted.

## Reduced-pressure observations

Reduced-pressure rows are retained as observations only. They do not provide an Antoine fit and are not used to evaluate 25 C:

| CAS | T boil (K) | Pressure (bar) | Reference |
|---|---:|---:|---|
| 141-12-8 | 407.2 | 0.033 | Weast and Grasselli, 1989 |
| 104-21-2 | 410. | 0.016 | American Tokyo Kasei, 1988 |
| 100-86-7 | 368.2 | 0.013 | Aldrich Chemical Company Inc., 1990 |
| 101-86-0 | 448.2 | 0.020 | Aldrich Chemical Company Inc., 1990 |
| 100-51-6 | 366.2 | 0.013 | Weast and Grasselli, 1989 |
| 100-51-6 | 366. | 0.013 | Buckingham and Donaghy, 1982 |

## Identity holds and claim ceiling

- `Caraway Seed Essential Oil` (8000-42-8), `Guaiacwood Essential Oil` (8016-23-7), `Ylang Madagascar Complete ORGANIC Ess. oil` (8006-81-3), and `Tuberose Absolute 10% in TEC` (8024-05-3) remain `CAS_RECORD_NOT_FOUND` mixture records with `surrogate_substituted=false`.
- `NOT_COVERED` means this packet does not authorize a 25 C vapour-pressure value. It does not imply zero vapour pressure, absence from NIST outside the requested page, or equivalence to a different CAS.
- The table supports source traceability, coverage classification, and fail-closed validator checks. It does not establish a material-property value, OAV, formulation suitability, safety, or release readiness.

## Validation result

Independent cached-only validation: **PASS** — 17 records, 17 unique CAS, 3 Antoine rows, 0 windows containing 298.15 K, 17 null 25 C results, and all four natural identity holds preserved.
