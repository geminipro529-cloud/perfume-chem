# Whole-inventory chemical audit: all 280 stock rows

Snapshot: 2026-09-07, canonical checkout `codex/astra` at `e7002d4dacde0ae4c6b92db454fa4034c830e8f4`. This is a read-only audit, not a corrected inventory or compounding authorization.

Every original stock row is retained, including unavailable stocks, separate concentrations, grades and planned preparations. Numbers below are distinct values found across alias-candidate YAML records, runtime profiles, the generated cache and the runtime ODT table. A slash means the local sources disagree; it does not mean a measured range. Equal numbers are not proof of correct chemistry. Exact source records and per-field status appear in [the machine-readable matrix](./INVENTORY_CHEMICAL_AUDIT_20260907_rows.json). Missing values are shown as an em dash. Molecule-like numbers for naturals and blends are provisional proxies, not a pure-compound identity.

MW: g/mol. VP: locally labeled Pa at 25 C; source temperatures have not all been verified. Air ODT: ppb; ethanol ODT: ppm. Thresholds belong to different media and cannot be compared as interchangeable values. `CAS hits` are source-query evidence records, not verified bottle identities. Read the [main findings report](../research/INVENTORY_CHEMICAL_AUDIT_20260907.md) before relying on any number.

| Inventory line | Parsed material / stock fraction | MW values | VP values | logP values | Air ODT values | Ethanol ODT values | Review flags |
|---:|---|---|---|---|---|---|---|
| 9 | Ethanol 96%; 0.96 unspecified  | 46.07 | 5900 | -0.31 | 100000 | 20000 | No local scalar conflict detected; external verification incomplete |
| 10 | Dipropylene Glycol; 1 neat  | 134.17 / 268.35 | 0.01 | -0.5 | 100000 | 2000 | mw_g_mol:LOCAL_CONFLICT; MULTIPLE_YAML_CANDIDATES |
| 11 | Isopropyl Myristate; 1 neat  | 270.46 | 0.001 | 7 | 10000 | 2000 | MULTIPLE_YAML_CANDIDATES |
| 12 | Triethyl Citrate; 1 neat  | 276.29 | 0.001 | 1.2 / 0.1 | 10000 | 2000 | logp:LOCAL_CONFLICT; MULTIPLE_YAML_CANDIDATES |
| 13 | Diethyl Phthalate; 1 neat  | 222.24 | 0.002 | 2.5 | 1000 | 2000 | MULTIPLE_YAML_CANDIDATES |
| 14 | Myristic Acid Powder; 1 neat  | 228.38 | 0.013 | 6.11 / 6.1 | 5000 | 1000 | MULTIPLE_YAML_CANDIDATES |
| 17 | Hexyl Acetate 1%; 0.01 unspecified  | — | — | — | — | — | NO_ALIAS_CANDIDATE_YAML; NO_PROFILE; NO_RUNTIME_ODT |
| 18 | Red Mandarin EO; 1 neat  | 136.2 / 136.23 | 1.8 | 4.4 | 5 | 2 | No local scalar conflict detected; external verification incomplete |
| 19 | Citral; 1 neat  | 152.23 | 3.5 | 2.76 | 20 | 0.032 | No local scalar conflict detected; external verification incomplete |
| 20 | Citronellal; 1 neat  | 154.25 | 40 | 3.09 | 40 | 0.015 | No local scalar conflict detected; external verification incomplete |
| 21 | D-Limonene; 1 neat  | 136.2 / 136.23 | 190 | 4.6 / 4.57 | 10 | 2 | NO_PROFILE; MULTIPLE_YAML_CANDIDATES |
| 22 | Linalool; 1 neat  | 154.3 / 154.25 | 21.3 / 15.8 | 2.7 / 2.97 | 1.5 | 0.1 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 23 | Linalyl Acetate; 1 neat  | 196.3 / 196.29 | 17.5 | 3.2 / 3.56 | 2.7 | 0.5 | logp:LOCAL_CONFLICT |
| 24 | Terpinyl Acetate; 1 neat  | 196.3 / 196.29 | 0.4 | 3.48 / 2.4 | 35 | 15 | logp:LOCAL_CONFLICT |
| 25 | Apritone; 0.1 unspecified  | 178.27 / 220.35 | 0.133 | 3.2 / 4.2 | 3.5 | 0.52 | mw_g_mol:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 26 | Hexyl Acetate; 0.1 unspecified  | 144.21 | 194 | 2.83 | 2 | 0.4 | No local scalar conflict detected; external verification incomplete |
| 27 | Aldehyde C10; 0.01 unspecified  | 156.3 / 156.27 | 10 / 8.2 | 3 / 3.76 | 0.44 | 0.081 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 28 | Aldehyde C11 undecylenic; 0.01 unspecified  | 168.3 / 168.28 | 0.1 | 3.3 / 3.8 | 0.8 | 0.4 | logp:LOCAL_CONFLICT |
| 29 | Aldehyde C12 MNA; 0.01 unspecified  | 184.3 / 184.32 | 0.01 | 3 / 4.83 | 11 | 2.2 | logp:LOCAL_CONFLICT |
| 30 | Aldehyde C12 MNA; 1 neat  | 184.3 / 184.32 | 0.01 | 3 / 4.83 | 11 | 2.2 | logp:LOCAL_CONFLICT |
| 31 | Methyl Pamplemousse; 0.1 unspecified tec | 168.2 / 168.23 | 0.5 | 2.1 | 3 | 0.5 | No local scalar conflict detected; external verification incomplete |
| 32 | Bergamot FCF oil Sicilian; 1 neat  | 170 | 2.5 | 3.2 / 2.8 | 6 | 2 | logp:LOCAL_CONFLICT |
| 33 | Grapefruit FCF oil Sicilian; 1 neat  | — | — | — | — | — | NO_PROFILE; NO_RUNTIME_ODT; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 34 | Cedrat FCF oil Sicilian; 1 neat  | 152 / 152.23 | 2 | 2.7 | 8 | 2 | No local scalar conflict detected; external verification incomplete |
| 35 | Blood Orange oil Sicilian; 1 neat  | 136.2 / 136.23 | 3 | 4.57 / 3.5 | 8 | 2 | logp:LOCAL_CONFLICT |
| 36 | Lime Distilled EO; 1 neat  | 136.2 / 170 | 170 / 200 / 1.8 | 4.2 / 3.5 | 8 | 2 | mw_g_mol:LOCAL_CONFLICT; vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; NO_PROFILE; MULTIPLE_YAML_CANDIDATES |
| 37 | Ethyl 2-Methylbutyrate; 0.001 unspecified  | 130.18 | 5 | 1.9 | 0.06 | 0.012 | No local scalar conflict detected; external verification incomplete |
| 38 | Lemonile; 1 neat  | 163.26 | 1.2 | 3.7 | 0.5 | 2 | No local scalar conflict detected; external verification incomplete |
| 39 | Lemonile; 0.01 unspecified dpg | 163.26 | 1.2 | 3.7 | 0.5 | 2 | No local scalar conflict detected; external verification incomplete |
| 40 | Orange Peel EO; 1 neat  | 136.23 | 1.9 | 4.57 | 10 | 2 | No local scalar conflict detected; external verification incomplete |
| 41 | Pamzest; 1 neat  | 150 | 30 | 3 | 5 | 1 | NO_PROFILE |
| 42 | Petitgrain EO Paraguay; 1 neat  | 136 | 6 | 3 | 4 | 1 | No local scalar conflict detected; external verification incomplete |
| 43 | Ginger EO; 1 neat  | 136 | 10 | 3.5 | 5 | 0.5 | No local scalar conflict detected; external verification incomplete |
| 44 | Neroli EO; 1 neat  | 170 | 1.2 | 2.5 | 2 | 2 | NO_PROFILE; MULTIPLE_YAML_CANDIDATES |
| 47 | Cis-3-Hexenol; 0.01 unspecified  | 100.2 / 100.16 | 1.4 | 1.6 / 1.61 | 0.01 | 0.001 | No local scalar conflict detected; external verification incomplete |
| 48 | Verdyl Acetate; 1 neat  | 192.25 | 2 | 2.2 | 10 | 0.02 | No local scalar conflict detected; external verification incomplete |
| 49 | Adoxal; 0.1 unspecified dpg | 210.36 | 0.4 | 6.2 / 5 | 0.3 | 0.05 | logp:LOCAL_CONFLICT |
| 50 | Blackcurrant Absolute; 0.1 unspecified dpg | 180 | 0.05 | 3.5 | 0.1 | 0.02 | No local scalar conflict detected; external verification incomplete |
| 51 | Dihydromyrcenol; 1 neat  | 156.3 / 156.27 | 17 / 14.8 | 3.47 / 2.9 | 1 | 0.3 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 52 | Verdox; 1 neat  | 170.25 / 198.3 | 0.3 | 3.2 | 20 | 5 | mw_g_mol:LOCAL_CONFLICT |
| 53 | Galbanum EO; 1 neat  | 136 | 15 | 3.5 | 0.1 | 0.01 | No local scalar conflict detected; external verification incomplete |
| 54 | Cyclamen Aldehyde; 1 neat  | 190.3 / 190.28 | 0.52 | 3.2 / 3.1 | 0.76 | 0.0025 | logp:LOCAL_CONFLICT; MULTIPLE_YAML_CANDIDATES |
| 55 | Scentenal; 0.01 unspecified  | 166.2 / 166.22 | 6 / 6.5 | 2 / 2.8 | 0.02 | 0.05 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 56 | Calone; 0.01 unspecified  | 178.18 | 0.0965 | 1.5 / 1.4 | 0.05 | 0.0002 | logp:LOCAL_CONFLICT |
| 57 | Floralozone; 0.1 unspecified  | 192.26 / 184.27 | 0.431 | 3.3 / 2.6 / 3.4 | 1 | 0.1 | mw_g_mol:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 58 | Undecavertol; 0.01 unspecified  | 170.29 | 0.06 | 3.8 | 10 | 2 | No local scalar conflict detected; external verification incomplete |
| 59 | Dynascone; 0.1 unspecified  | 192.3 | 1.33322 | 2.5 / 3.4 | 0.05 | 0.05 | logp:LOCAL_CONFLICT |
| 60 | Parmavert; 1 neat  | 192.3 | 0.1 | 2.5 / 3.5 | 15 | 3 | logp:LOCAL_CONFLICT |
| 61 | Leafovert; 1 neat  | 154.3 / 154.25 | 0.5 | 2 / 3 | 8 | 0.05 | logp:LOCAL_CONFLICT |
| 62 | Triplal; 1 neat  | 152.23 / 138.21 | 66.1 | 1.4 | 0.5 | 0.001 | mw_g_mol:LOCAL_CONFLICT; NO_PROFILE |
| 63 | Geosmin; 0.001 unspecified tec | 182.3 | 0.1 | 3.6 | 0.006 | 0.001 | No local scalar conflict detected; external verification incomplete |
| 64 | Geosmin; 0.01 unspecified tec | 182.3 | 0.1 | 3.6 | 0.006 | 0.001 | No local scalar conflict detected; external verification incomplete |
| 65 | Peppermint Essential Oil; 1 neat  | 159 | 12 | 3.1 | 20 | 4 | MULTIPLE_YAML_CANDIDATES; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 66 | Eucalyptus Essential Oil; 1 neat  | 155 | 210 | 2.7 | 80 | 12 | No local scalar conflict detected; external verification incomplete |
| 67 | Tagetes EO; 0.1 unspecified dpg | 155 | 3 | 3.2 | 3 | 0.3 | NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 68 | Liffarome; 0.1 mass_fraction  | — | — | — | — | — | NO_PROFILE; NO_RUNTIME_ODT |
| 71 | Nerolidol; 1 neat  | 222.37 | 0.006 | 4.6 | 150 | 0.9 | No local scalar conflict detected; external verification incomplete |
| 72 | Helional 10% v/v; 0.1 volume_fraction  | — | — | — | — | — | NO_ALIAS_CANDIDATE_YAML; NO_PROFILE; NO_RUNTIME_ODT |
| 73 | Stralyl Acetate; 1 neat  | 164.2 | 7 | 2 | 40 | 1 | No local scalar conflict detected; external verification incomplete |
| 74 | Heliotropin; 1 neat  | 150.13 / 150.1 | 1.41322 / 0.15 / 0.6 | 1.5 / 0.87 / 1.05 | 1 / 0.006 | 0.01 / 5 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; odt_air_ppb:LOCAL_CONFLICT; odt_eth_ppm:LOCAL_CONFLICT; MULTIPLE_YAML_CANDIDATES |
| 75 | PADMA; 1 neat  | 166.22 | 20 | 2.1 | 200 | 0.5 | NO_ALIAS_CANDIDATE_YAML |
| 76 | Tuberlia Base; 1 neat  | 190 | 0.1 | 2.5 | 10 | 0.02 | No local scalar conflict detected; external verification incomplete |
| 77 | Tuberose EO; 1 neat  | 220 / 190 | 0.005 / 0.1 | 3 / 2.5 | 20 / 1.5 | 0.05 / 0.015 | mw_g_mol:LOCAL_CONFLICT; vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; odt_air_ppb:LOCAL_CONFLICT; odt_eth_ppm:LOCAL_CONFLICT; NO_PROFILE; MULTIPLE_YAML_CANDIDATES |
| 78 | Helichrysum EO; 1 neat  | 180 | 0.5 | 3 | 5 | 0.01 | NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 79 | Jasmine Absolute; 0.1 unspecified dpg | 170 | 0.005 | 3 | 1 | 1.5 | MULTIPLE_YAML_CANDIDATES |
| 80 | Geranium EO; 1 neat  | 157 | 1.5 / 2.5 | 3 / 3.2 | 0.3 | 1 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; NO_PROFILE |
| 81 | Hedione; 1 neat  | 226.3 / 226.31 | 0.09466 | 2.7 / 3 | 0.05 | 0.01 | logp:LOCAL_CONFLICT |
| 82 | Dihydrojasmone; 1 neat  | 166.3 / 166.26 | 7.66 / 7.67 | 2.9 | 0.75 | 0.15 | No local scalar conflict detected; external verification incomplete |
| 83 | Jessemal; 1 neat  | 214.3 | 0.5 | 2.8 | 5 | 1 | MULTIPLE_YAML_CANDIDATES |
| 84 | Hydroxycitronellol; 1 neat  | 174.28 | 0.0736 | 1.5 | 100 | 20 | No local scalar conflict detected; external verification incomplete |
| 85 | Phenethyl Alcohol; 1 neat  | 122.17 | 0.116 | 1.36 | 26 | 0.026 | No local scalar conflict detected; external verification incomplete |
| 86 | Cinnamyl alcohol 50% in DPG; 0.5 unspecified dpg | 134.18 | 0.03 | 1.9 | 3 | 0.081 | NO_RUNTIME_ODT |
| 87 | Florol; 1 neat  | 154.25 / 138.21 | 0.007 | 2.5 / 2.3 / 1.4 | 10 | 2 | mw_g_mol:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 88 | Peonile; 1 neat  | 197.27 / 192.3 | 0.0056 | 3.6 | 5 | 1 | mw_g_mol:LOCAL_CONFLICT |
| 89 | Aurantiol; 1 neat  | 305.4 / 254.26 | 0.533 | 3.3 / 4.8 / 0 | 30 | 5 | mw_g_mol:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 90 | Geraniol; 1 neat  | 154.3 / 154.25 | 4 / 2.67 | 3.56 / 2.9 | 0.04 | 0.3 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 91 | Geraniol; 0.1 unspecified dpg | 154.3 / 154.25 | 4 / 2.67 | 3.56 / 2.9 | 0.04 | 0.3 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 92 | Citronellol; 1 neat  | 156.3 / 156.27 | 2.26 | 3.91 / 3.2 | 40 | 5 | logp:LOCAL_CONFLICT |
| 93 | Rhodinol ex Citronella; 1 neat  | 156.26 | 7 | 3.5 | 0.3 | 5 | No local scalar conflict detected; external verification incomplete |
| 94 | Geranium Flower EO; 1 neat  | 157 | 1.5 / 2.5 | 3 / 3.2 | 0.3 | 1 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; NO_PROFILE |
| 95 | Rose Oxide; 0.01 unspecified  | 154.3 / 154.25 | 5.3 | 2.9 / 3.2 | 0.5 | 0.001 | logp:LOCAL_CONFLICT |
| 96 | Rose Oxide; 0.1 unspecified  | 154.3 / 154.25 | 5.3 | 2.9 / 3.2 | 0.5 | 0.001 | logp:LOCAL_CONFLICT |
| 97 | Benzyl Salicylate; 1 neat  | 228.3 / 228.24 | 0.01 | 3.2 / 4.31 | 10 | 0.24 | logp:LOCAL_CONFLICT |
| 98 | Hexyl Salicylate; 1 neat  | 222.3 / 222.28 | 0.077 | 5.7 / 4.87 | 35 | 30 | logp:LOCAL_CONFLICT |
| 99 | Benzyl Benzoate; 1 neat  | 212.2 / 212.24 | 0.02986 / 0.001 | 4 / 3.97 | 810 | 0.15 / 2 | vp_25c_pa:LOCAL_CONFLICT; odt_eth_ppm:LOCAL_CONFLICT; NO_PROFILE |
| 100 | Benzyl Alcohol; 0.5 unspecified dpg | 108.14 | 8 | 1.1 | 50 | 5 | No local scalar conflict detected; external verification incomplete |
| 101 | Benzaldehyde; 1 neat  | 106.12 | 120 | 1.5 | 0.04 | 0.005 | No local scalar conflict detected; external verification incomplete |
| 102 | Benzaldehyde; 0.01 unspecified dpg | 106.12 | 120 | 1.5 | 0.04 | 0.005 | No local scalar conflict detected; external verification incomplete |
| 103 | Benzyl Acetate; 1 neat  | 150.2 / 150.17 | 0.22 | 2 / 1.96 | 20 | 5 | logp:LOCAL_CONFLICT |
| 104 | Indole; 0.1 unspecified  | 117.2 / 117.15 | 0.01 | 2.1 / 2.14 | 0.14 | 0.05 | logp:LOCAL_CONFLICT |
| 105 | Bourgeonal; 0.2 unspecified tec | 176.25 / 190.28 | 0.01 | 2.8 / 2.9 | 0.03 | 0.05 | mw_g_mol:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 106 | Freesia HDI; 1 neat  | 170.25 | 0.02 | 2.5 / 2.8 | 3 | 0.5 | logp:LOCAL_CONFLICT; NO_PROFILE |
| 107 | Lilyreal ND; 1 neat  | 192.3 | 0.01 | 3.5 | 2 | 0.3 | No local scalar conflict detected; external verification incomplete |
| 108 | Lilial; 1 neat  | 204.31 | 0.33 | 3.9 | 0.5 | 0.1 | No local scalar conflict detected; external verification incomplete |
| 109 | Nympheal; 1 neat  | 204.3 / 204.31 | 0.01 | 3 / 3.8 | 2 | 0.4 | logp:LOCAL_CONFLICT |
| 110 | Helional; 1 neat  | 192.2 / 192.21 | 0.01 | 2.2 / 1.7 | 0.1 | 0.1 | logp:LOCAL_CONFLICT |
| 111 | Lemon FCF oil Sicilian; 1 neat  | 136.7 / 170 | 210 / 2.5 | 3.5 / 3 | 8 | 2 | mw_g_mol:LOCAL_CONFLICT; vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; NO_PROFILE |
| 112 | Ylang Comoros Complete EO F3255; 1 neat  | 200 | 0.05 | 3 | 30 | 6 | MULTIPLE_YAML_CANDIDATES |
| 113 | Ylang Comoros III EO F3295; 1 neat  | 200 | 0.03 | 3.2 | 40 | 8 | No local scalar conflict detected; external verification incomplete |
| 114 | Champaca Flower EO; 1 neat  | 200 | 0.03 | 2.8 / 3 | 8 | 1.5 | logp:LOCAL_CONFLICT; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 115 | Magnolia EO; 1 neat  | — | — | — | — | — | NO_PROFILE; NO_RUNTIME_ODT; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 116 | Methyl Benzoate; 1 neat  | 136.15 | 40 | 2.12 | 50 | 40 | No local scalar conflict detected; external verification incomplete |
| 117 | p-Cresyl Methyl Ether (PCME); 0.1 unspecified  | 122.16 | 270 | 2.7 | 0.5 | 0.1 | NO_ALIAS_CANDIDATE_YAML; NO_RUNTIME_ODT |
| 118 | Paradisamide; 0.1 unspecified  | 219.32 | 0.002 | 3.4 | 8 | 0.1 | No local scalar conflict detected; external verification incomplete |
| 119 | Cis Jasmone; 1 neat  | 164.24 | 1.333 | 2.2 | 0.5 | 0.1 | No local scalar conflict detected; external verification incomplete |
| 120 | Methyl Salicylate; 1 neat  | 152.15 | 5.3 | 2.55 | 40 | 8 | No local scalar conflict detected; external verification incomplete |
| 121 | Methyl Anthranilate; 1 neat  | 151.16 | 0.03 | 1.9 / 1.88 | 2 | 0.5 | logp:LOCAL_CONFLICT |
| 122 | Alpha Damascone; 0.1 unspecified  | 192.3 | 1.10657 | 3.6 | 0.04 | 0.01 | No local scalar conflict detected; external verification incomplete |
| 123 | Damascone Beta; 0.1 unspecified  | 190.3 | 0.08 | 3.7 | 0.04 | 0.01 | MULTIPLE_YAML_CANDIDATES |
| 124 | Damascenone; 0.01 unspecified  | 190.3 | 1 / 0.693 | 3.2 / 3.9 | 0.04 | 0.0004 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 125 | Damascol; 0.1 unspecified  | 194.3 | 0.6 | 3.5 | 0.5 | 0.005 | No local scalar conflict detected; external verification incomplete |
| 126 | Heliotropal; 1 neat  | 150.13 / 150.1 | 1.41322 / 0.15 / 0.6 | 1.5 / 0.87 / 1.05 | 1 / 0.006 | 0.01 / 5 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; odt_air_ppb:LOCAL_CONFLICT; odt_eth_ppm:LOCAL_CONFLICT; MULTIPLE_YAML_CANDIDATES |
| 127 | Amyl Cinnamic Aldehyde; 1 neat  | 202.3 | 0.02 | 3.9 | 1.5 / 2 | 2 | odt_air_ppb:LOCAL_CONFLICT; MULTIPLE_YAML_CANDIDATES |
| 128 | Phenyl Ethyl Dimethyl Carbinol; 1 neat  | 164.24 | 0.3 | 2.1 | 3 | 0.8 | NO_RUNTIME_ODT |
| 129 | Farnesol; 1 neat  | 222.4 | 0.08 | 5.3 | 20 | 10 | No local scalar conflict detected; external verification incomplete |
| 130 | Mayol; 1 neat  | 166.3 / 156.26 | 1.5 | 2.9 | 3 | 0.5 | mw_g_mol:LOCAL_CONFLICT |
| 131 | Oranger Crystals; 0.1 unspecified dpg | 170.21 | 0.12 / 0.133 | 2.678 / 3.2 | 100 | 1 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 132 | Nerol; 1 neat  | 154.25 | 2 | 2.9 | 0.5 | 0.3 | No local scalar conflict detected; external verification incomplete |
| 133 | Nerolin Bromelia; 0.1 unspecified dpg | 172.22 | 0.5 | 3.8 | 3 | 2 | No local scalar conflict detected; external verification incomplete |
| 134 | Osmanthus Absolute; 0.1 unspecified dpg | 200 | 0.01 | 3.2 | 0.5 | 0.005 | MULTIPLE_YAML_CANDIDATES |
| 135 | Rose de Mai Absolute; 0.1 unspecified dpg | 220 | 0.001 | 3 | 5 | 0.05 | MULTIPLE_YAML_CANDIDATES |
| 136 | Tuberose Base; 1 neat  | — | — | — | — | — | NO_ALIAS_CANDIDATE_YAML; NO_PROFILE; NO_RUNTIME_ODT |
| 137 | Tuberose Absolute; 0.1 unspecified dpg | 220 | 0.005 | 3 | 1 | 0.01 | MULTIPLE_YAML_CANDIDATES |
| 138 | Phenyl Ethyl Acetate; 1 neat  | 164.2 | 3 | 2.3 | 3 | 0.03 | MULTIPLE_YAML_CANDIDATES |
| 139 | Immortelle Absolute; 0.1 unspecified dpg | 200 | 0.02 | 3.5 | 1 | 0.01 | MULTIPLE_YAML_CANDIDATES |
| 140 | Rose Essential Oil; 1 neat  | 175 | 1 | 3 | 3 | 0.5 | No local scalar conflict detected; external verification incomplete |
| 141 | Jasmine Sambac Blossoms; 1 neat  | 220 | 0.3 | 3 | 3 | 0.5 | MULTIPLE_YAML_CANDIDATES |
| 142 | Blue Chamomile EO; 1 neat  | 200 | 1 | 3.5 | 4 | 0.4 | No local scalar conflict detected; external verification incomplete |
| 143 | Mimosa Absolute; 0.1 unspecified dpg | 240 | 0.05 | 3.8 | 2 | 0.3 | MULTIPLE_YAML_CANDIDATES |
| 144 | Osmanthus Absolute; 1 neat  | 200 / 210 | 0.01 / 0.08 | 3.2 / 3 | 0.5 / 2 | 0.005 / 0.4 | mw_g_mol:LOCAL_CONFLICT; vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; odt_air_ppb:LOCAL_CONFLICT; odt_eth_ppm:LOCAL_CONFLICT; MULTIPLE_YAML_CANDIDATES |
| 145 | Tuberose Absolute; 1 neat  | 220 / 230 | 0.005 / 0.04 | 3 / 3.5 | 1 / 1.5 | 0.01 / 0.3 | mw_g_mol:LOCAL_CONFLICT; vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; odt_air_ppb:LOCAL_CONFLICT; odt_eth_ppm:LOCAL_CONFLICT; MULTIPLE_YAML_CANDIDATES |
| 146 | Isobutavan; 1 neat  | 222.24 | 0.03 | 2.1 | 0.5 | 0.05 | MULTIPLE_YAML_CANDIDATES |
| 147 | Allyl Cyclohexyl Propionate; 0.1 unspecified dpg | 196.29 | 5 | 3.3 | 8 | 0.8 | MULTIPLE_YAML_CANDIDATES |
| 148 | Cis-3-Hexenyl Salicylate; 0.2 mass_fraction  | — | — | — | 25 | 0.3 | NO_PROFILE |
| 151 | Violet Leaf Absolute; 0.1 unspecified dpg | 220 | 0.005 | 4 | 0.2 | 0.02 | No local scalar conflict detected; external verification incomplete |
| 152 | Alpha Ionone; 1 neat  | 192.3 | 1.5 | 3 / 2.9 | 0.4 | 0.1 | logp:LOCAL_CONFLICT |
| 153 | Beta Ionone; 1 neat  | 192.3 | 1.2 | 3 / 2.9 | 0.007 | 0.05 | logp:LOCAL_CONFLICT |
| 154 | Beta Ionone; 0.001 unspecified tec | 192.3 | 1.2 | 3 / 2.9 | 0.007 | 0.05 | logp:LOCAL_CONFLICT |
| 155 | Allyl Ionone; 1 neat  | 232.37 | 0.0664 | 5.3 / 4 | 1 | 0.5 | logp:LOCAL_CONFLICT |
| 156 | Alpha Isomethyl Ionone; 1 neat  | 206.32 / 206.33 | 0.4 | 3.3 / 3.2 / 4.1 | 0.8 | 0.5 | logp:LOCAL_CONFLICT; MULTIPLE_YAML_CANDIDATES |
| 157 | Alpha Irone; 0.1 mass_fraction dep | 206.32 / 206.33 | 0.559 | 3.2 / 3.8 | 0.9 | 0.16 | logp:LOCAL_CONFLICT |
| 158 | Orris Liquid; 0.09 mass_fraction dep | 206.32 | 0.559 | 3.2 | 0.9 | 0.16 | No local scalar conflict detected; external verification incomplete |
| 159 | Irotyl; 1 neat  | 206.33 | 0.005 | 3.5 | 1 | 0.2 | No local scalar conflict detected; external verification incomplete |
| 160 | Dihydro Beta Ionone; 1 neat  | 194.3 / 194.31 | 0.02 | 2.7 / 4.5 | 5 | 0.3 | logp:LOCAL_CONFLICT |
| 161 | Orivone; 1 neat  | 168.28 | 8.6 | 2.9 / 3.4 | 0.3 | 0.5 | logp:LOCAL_CONFLICT |
| 162 | Ultralia; 1 neat  | 222.37 | 0.002 | 2.5 / 4 | 0.3 | 0.05 | logp:LOCAL_CONFLICT |
| 163 | Carrot Seed EO; 1 neat  | 220 | 0.01 | 3.5 | 5 | 1 | No local scalar conflict detected; external verification incomplete |
| 166 | Sandalwood Base 3X; 1 neat  | 220 | 0.1 | 3.5 | 100 | 0.5 | NO_PROFILE; MULTIPLE_YAML_CANDIDATES |
| 167 | Sandalwood EO; 0.1 unspecified dpg | 220 | 0.001 | 4 | 5 | 1 | NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 168 | Cypress EO; 1 neat  | 136 | 250 | 3.8 | 200 | 0.5 | NO_ALIAS_CANDIDATE_YAML; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 169 | Black Agarwood Artificial; 0.1 mass_fraction dpg | 220 | 0.001 | 4.5 | 0.5 | 0.05 | No local scalar conflict detected; external verification incomplete |
| 170 | Cabreuva EO; 0.5 mass_fraction dpg | 222 | 0.006 | 4.6 | 150 | 0.9 | NO_ALIAS_CANDIDATE_YAML; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 171 | Black Agarwood Artificial; 1 neat  | 220 | 0.001 | 4.5 | 0.5 | 0.05 | No local scalar conflict detected; external verification incomplete |
| 172 | Iso E Super; 1 neat  | 234.4 / 234.38 | 0.23129 | 3.6 | 0.05 | 0.01 | No local scalar conflict detected; external verification incomplete |
| 173 | Cashmeran; 1 neat  | 206.3 / 206.32 | 1.242 | 3.3 | 2 | 0.5 | No local scalar conflict detected; external verification incomplete |
| 174 | Cashmeran; 0.2 unspecified  | 206.3 / 206.32 | 1.242 | 3.3 | 2 | 0.5 | No local scalar conflict detected; external verification incomplete |
| 175 | Polysantol; 1 neat  | 222.37 | 0.003 | 4.2 | 0.01 | 0.5 | No local scalar conflict detected; external verification incomplete |
| 176 | Cedramber; 1 neat  | 234.38 | 0.35 / 0.002 | 5 | 240 | 0.2 | vp_25c_pa:LOCAL_CONFLICT |
| 177 | Ambermax; 0.5 unspecified  | 234 | 0.001 | 4.2 / 4 | 0.5 | 0.1 | logp:LOCAL_CONFLICT; NO_PROFILE |
| 178 | Ebanol; 1 neat  | 220.4 / 220.35 / 208.34 | 0.89 | 3.3 / 4.5 | 0.21 | 1.5 | mw_g_mol:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 179 | Bacdanol; 1 neat  | 210.36 | 0.001 | 3.6 / 3.8 | 12 | 2.5 | logp:LOCAL_CONFLICT |
| 180 | Sandalore; 1 neat  | 210.4 / 210.36 | 0.08 | 3.9 / 4.2 | 10 | 2 | logp:LOCAL_CONFLICT |
| 181 | Vetival; 1 neat  | 218.33 / 262.4 | 6.53 | 3 / 4 | 7 | 0.5 | mw_g_mol:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 182 | Vertofix; 1 neat  | 234.4 / 234.38 / 246.4 | 0.0112 | 4 / 5 | 6.3 | 1 | mw_g_mol:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 183 | Suederal; 0.1 unspecified  | 168.28 | 0.01 | 3.5 / 3 | 0.5 | 0.5 | logp:LOCAL_CONFLICT |
| 184 | Suederal; 1 neat  | 168.28 | 0.01 | 3.5 / 3 | 0.5 | 0.5 | logp:LOCAL_CONFLICT |
| 185 | Javanol; 1 neat  | 222.37 | 0.1 | 4.1 | 0.0016 | 0.0003 | No local scalar conflict detected; external verification incomplete |
| 186 | Amberwood F; 1 neat  | 234.4 / 234 | 0.001 | 3.8 / 4.5 | 1 | 0.3 | logp:LOCAL_CONFLICT |
| 187 | Ambrox Super; 0.25 mass_fraction  | 236.4 | 0.05 | 4.5 / 4.92 | 0.3 | 0.005 | logp:LOCAL_CONFLICT |
| 188 | Ambrofix; 0.0727 mass_fraction dep + ethanol | 236.4 | 0.066 / 0.05 | 4.7 / 4.5 / 4.92 / 4.9 | 0.3 | 0.005 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; MULTIPLE_YAML_CANDIDATES |
| 189 | Ambrofix Crystals; 1 neat  | 236.4 | 0.066 | 4.7 | 0.5 | 0.005 | NO_PROFILE; NO_RUNTIME_ODT |
| 190 | Timberol; 1 neat  | 226.4 | 0.066661 | 3.8 / 4.1 / 5.2 | 0.6 | 0.5 | logp:LOCAL_CONFLICT |
| 191 | Koavone; 1 neat  | 206.33 | 0.3 / 0.45 | 3.5 / 4 | 5 | 0.5 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 192 | Cedarwood EO; 1 neat  | 204.4 | 0.25 | 3.9 | 15 | 3 | No local scalar conflict detected; external verification incomplete |
| 193 | Guaiacwood EO; 0.3333333333333333 mass_fraction ethanol + dep | — | — | — | — | — | NO_ALIAS_CANDIDATE_YAML; NO_PROFILE; NO_RUNTIME_ODT; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 194 | Cedarwood oil Virginia; 1 neat  | 222.37 | 0.005 | 5 | 15 | 3 | No local scalar conflict detected; external verification incomplete |
| 195 | Himalayan Cedarwood EO; 1 neat  | 204.4 | 0.02 | 4.5 | 15 | 3 | NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 196 | Indian Vetiver EO; 1 neat  | 222.4 | 0.04 | 3.8 | 15 | — | NO_PROFILE; NO_RUNTIME_ODT; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 197 | Nagarmortha Oil; 1 neat  | 220 / 204 | 0.005 / 0.01 / 0.13 | 4.6 / 4.5 / 4 | 5 / 8 | 1 | mw_g_mol:LOCAL_CONFLICT; vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; odt_air_ppb:LOCAL_CONFLICT; MULTIPLE_YAML_CANDIDATES |
| 198 | Vetikon; 1 neat  | 176.25 | 4.16 | 2.7 | 5 | 1 | No local scalar conflict detected; external verification incomplete |
| 199 | Norlimbanol Dextro; 1 neat  | 224.38 | 0.067 | 5.2 | 0.8 | 0.1 | No local scalar conflict detected; external verification incomplete |
| 200 | Azarbre; 1 neat  | 220 / 180.29 | 4.3 | 4.8 / 2.9 | 2 | 0.5 | mw_g_mol:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 201 | Kephalis; 1 neat  | 224.34 | 0.46 | 4.5 / 3.1 | 50 | 0.1 | logp:LOCAL_CONFLICT |
| 202 | Amber Xtreme; 0.1 mass_fraction dep | 236 | 0.001 | 4.5 | 0.05 | 0.15 | NO_ALIAS_CANDIDATE_YAML |
| 203 | Clearwood; 1 neat  | 222.4 / 222.37 | 0.002 | 4 / 4.3 | 10 | 1 | logp:LOCAL_CONFLICT |
| 204 | Givaudan AIMI; 1 neat  | 206.32 / 206.33 | 0.4 | 3.3 / 3.2 | 0.8 | 0.5 | logp:LOCAL_CONFLICT; NO_PROFILE; MULTIPLE_YAML_CANDIDATES |
| 207 | Ethylene Brassylate; 1 neat  | 270.4 / 270.37 | 0.008 | 4.2 / 3.89 | 0.97 | 1 | logp:LOCAL_CONFLICT |
| 208 | Galaxolide; 0.5 unspecified dep | 258.4 | 0.0727 | 4.8 | 0.31 | 1 | No local scalar conflict detected; external verification incomplete |
| 209 | Tonalide; 0.1 unspecified  | 258.4 | 0.0001 | 5.7 | 3 | 1 | No local scalar conflict detected; external verification incomplete |
| 210 | Habanolide; 1 neat  | 238.4 / 238.37 | 0.000053 | 4.5 / 5.5 | 2.8 | 0.2 | logp:LOCAL_CONFLICT |
| 211 | Zenolide; 1 neat  | 254.41 | 0.0001 | 3.6 / 6 | 3 | 1 | logp:LOCAL_CONFLICT |
| 212 | Romandolide; 1 neat  | 270.36 | 0.1 | 4.56 | 4.9 | 0.5 | No local scalar conflict detected; external verification incomplete |
| 213 | Exaltolide; 0.1 unspecified  | 240.4 / 240.38 | 0.0001 | 5.8 / 5.3 | 3.2 | 1 | logp:LOCAL_CONFLICT |
| 214 | Macrolide; 0.1 unspecified  | 254.41 | 0.0001 | 5 / 6.5 | 2 | 1.5 | logp:LOCAL_CONFLICT |
| 215 | Ambrettolide; 0.1 mass_fraction dpg | 252.4 / 252.39 | 0.003 | 5.5 | 0.136 | 0.014 | No local scalar conflict detected; external verification incomplete |
| 216 | Musk Ketone; 1 neat  | 294.3 | 0.000039997 | 3.8 / 3.7 | 2 | 0.4 | logp:LOCAL_CONFLICT |
| 217 | Musk Ketone; 0.1 unspecified dpg | 294.3 | 0.000039997 | 3.8 / 3.7 | 2 | 0.4 | logp:LOCAL_CONFLICT |
| 220 | Hay Absolute; 0.1 unspecified  | 146 | 0.3 | 1.4 | 4 | 0.01 | NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 221 | Anisaldehyde 10%; 0.1 unspecified  | — | — | — | — | — | NO_ALIAS_CANDIDATE_YAML; NO_PROFILE; NO_RUNTIME_ODT |
| 222 | Ethyl Maltol 1%; 0.01 unspecified  | — | — | — | — | — | NO_ALIAS_CANDIDATE_YAML; NO_PROFILE; NO_RUNTIME_ODT |
| 223 | Raspberry Ketone; 0.2 mass_fraction dpg w/w | 164.2 | 0.001 | 1.5 | 0.4 | 0.08 | No local scalar conflict detected; external verification incomplete |
| 224 | Vietnamese Benzoin Styrax Tonkinensis resin ethanol tincture; 0.2 unspecified  | 212 | 0.02 | 2.5 | 3 | 0.01 | NO_PROFILE |
| 225 | Turkish Storax Liquidambar Orientalis resin ethanol tincture; 0.2 unspecified  | 148 | 1 | 2 | 20 | 0.05 | NO_PROFILE |
| 226 | Coffee Absolute Grasse; 0.1 unspecified dpg | 190 | 0.01 | 3.5 | 0.2 | 0.05 | No local scalar conflict detected; external verification incomplete |
| 227 | 2-Acetyl Pyrazine; 0.01 unspecified dpg | 122.12 | 0.02 | 0.7 | 0.3 | 0.01 | No local scalar conflict detected; external verification incomplete |
| 228 | Ethyl Maltol; 0.1 unspecified  | 140.1 / 140.14 | 0.029 | 0.8 / 0.03 | 0.3 | 0.06 | logp:LOCAL_CONFLICT |
| 229 | Coumarin; 0.3 unspecified  | 146.2 / 146.14 | 0.19 / 0.133 | 1.4 / 1.39 | 0.7 | 0.5 | vp_25c_pa:LOCAL_CONFLICT |
| 230 | Coumarin; 1 neat  | 146.2 / 146.14 | 0.19 / 0.133 | 1.4 / 1.39 | 0.7 | 0.5 | vp_25c_pa:LOCAL_CONFLICT |
| 231 | Vanillin; 0.1 unspecified  | 152.2 / 152.15 | 0.2 | 1.2 / 1.21 | 20 | 10 | No local scalar conflict detected; external verification incomplete |
| 232 | Ethyl Vanillin; 0.1 unspecified  | 166.2 / 166.17 | 0.019 | 1.6 / 1.58 | 6 | 3 | logp:LOCAL_CONFLICT |
| 233 | Maple Lactone; 0.2 unspecified  | 128.1 / 128.13 | 0.01 | 0.5 / 0.1 | 1 | 0.2 | logp:LOCAL_CONFLICT |
| 234 | Raspberry Ketone; 1 neat  | 164.2 | 0.001 | 1.5 | 0.4 | 0.08 | No local scalar conflict detected; external verification incomplete |
| 235 | Siam Benzoin; 0.5 unspecified dpg | 212.24 | 0.0001 | 2.5 | 40 | 2 | No local scalar conflict detected; external verification incomplete |
| 236 | Benzoin Sumatra Resinoid; 0.1 unspecified  | 212.24 | 0.0001 | 2.5 | 3 | 2 | No local scalar conflict detected; external verification incomplete |
| 237 | Anisaldehyde; 1 neat  | 136.2 / 136.15 | 0.05 / 0.04 | 1.8 / 1.76 | 5 | 1 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 238 | Gamma Decalactone; 1 neat  | 170.3 / 170.25 | 0.005 | 3 / 2.9 | 1.5 | 0.3 | logp:LOCAL_CONFLICT |
| 239 | Gamma Undecalactone; 1 neat  | 184.3 / 184.28 | 0.002 | 3.3 / 3.4 | 1 | 0.2 | logp:LOCAL_CONFLICT |
| 240 | Delta Decalactone; 1 neat  | 170.3 / 170.25 | 0.003 | 2.5 | 10 | 2 | No local scalar conflict detected; external verification incomplete |
| 241 | Aldehyde C-18; 0.1 unspecified  | — | — | — | — | — | NO_ALIAS_CANDIDATE_YAML; NO_PROFILE; NO_RUNTIME_ODT |
| 242 | Aldehyde C-18; 1 neat  | — | — | — | — | — | NO_ALIAS_CANDIDATE_YAML; NO_PROFILE; NO_RUNTIME_ODT |
| 243 | Allyl Amyl Glycolate; 0.1 unspecified  | 158.2 / 158.19 / 186.25 | 0.2 | 1 / 1.5 / 2.3 | 2 | 0.3 | mw_g_mol:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 244 | Labdanum Resinoid; 0.1 unspecified dpg | 300 | 1e-05 / 0.00001 | 4.5 / 5 | 5 | 0.05 / 2 | vp_25c_pa:INVALID_VALUE; logp:LOCAL_CONFLICT; odt_eth_ppm:LOCAL_CONFLICT; MULTIPLE_YAML_CANDIDATES |
| 245 | Tonkarome; 0.2 mass_fraction tec | 160 | 0.05 | 2.5 | 0.5 | 0.01 | MULTIPLE_YAML_CANDIDATES |
| 246 | Cocoa Absolute; 1 neat  | 250 | 0.01 | 4 | 5 | 0.05 | No local scalar conflict detected; external verification incomplete |
| 247 | Tonka Bean Absolute; 0.1 unspecified dpg | 195 | 0.02 | 2.5 | 1 | 0.2 | MULTIPLE_YAML_CANDIDATES |
| 248 | Cocoa CO2 Extract; 0.077 unspecified  | 260 | 0.01 | 3.5 | 3 | 0.5 | No local scalar conflict detected; external verification incomplete |
| 249 | Peru Balsam Resinoid; 0.5 unspecified dpg | 275 | 0.03 | 3.5 | 30 | 10 | MULTIPLE_YAML_CANDIDATES; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 250 | Opoponax Resinoid; 0.5 unspecified dep | 220 | 0.02 | 3.2 | 10 | 5 | MULTIPLE_YAML_CANDIDATES; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 251 | Myrrh EO; 0.5 unspecified dep | 222.4 / 222.37 | 0.001 | 3.5 | 7 | 5 | NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 254 | Castoreum Synthetic; 0.1 unspecified dep | 200 | 0.001 | 3 | 0.5 | 0.05 | No local scalar conflict detected; external verification incomplete |
| 255 | Tobacco Absolute; 0.1 unspecified dpg | 195 | 0.03 | 3.5 | 1 | 0.5 | No local scalar conflict detected; external verification incomplete |
| 256 | Isobutyl Quinoline; 0.1 unspecified  | 185.3 / 185.27 | 0.129 | 2.9 / 3.5 | 0.05 | 0.02 | logp:LOCAL_CONFLICT |
| 257 | Birch Tar Rectified; 0.1 unspecified dpg | 124.14 / 124.1 | 13.3 | 1.5 / 2.5 | 2 | 1 / 0.3 | logp:LOCAL_CONFLICT; odt_eth_ppm:LOCAL_CONFLICT; MULTIPLE_YAML_CANDIDATES |
| 258 | Costus Olifac; 0.1 unspecified dpg | 200 | 0.001 | 3.5 | 5 | 0 | odt_eth_ppm:INVALID_VALUE; NO_PROFILE |
| 259 | Cade Oil Rectified; 0.01 unspecified dpg | 200 | 0.01 | 3.5 | 3 | 0.5 | NO_RUNTIME_ODT; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 260 | Guaiacol; 0.1 unspecified  | 124.1 / 124.14 | 0.053 | 1.3 / 1.32 | 0.5 | 0.1 | logp:LOCAL_CONFLICT |
| 261 | Evernyl; 1 neat  | 196.2 | 0.1 / 0.129 | 2.8 / 2.1 | 0.3 | 0.5 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 262 | Evernyl; 0.2 mass_fraction dpg | 196.2 | 0.1 / 0.129 | 2.8 / 2.1 | 0.3 | 0.5 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 263 | Evernyl; 0.1 mass_fraction dep | 196.2 | 0.1 / 0.129 | 2.8 / 2.1 | 0.3 | 0.5 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT |
| 264 | Skatole; 0.01 unspecified  | 131.17 | 0.01 | 2.6 | 0.004 | 0.0008 | No local scalar conflict detected; external verification incomplete |
| 265 | Oakmoss Absolute; 0.1 unspecified dpg | 400 | 0.001 | 4.5 | 0.5 | 0.01 | No local scalar conflict detected; external verification incomplete |
| 268 | Elemi EO; 1 neat  | 204 | 5 | 4 | 10 | 2 | NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 269 | Safraleine; 0.1 mass_fraction dpg | 174.24 | 0.02 | 2.3 / 3.1 | 0.1 | 0.02 | logp:LOCAL_CONFLICT |
| 270 | Caraway Seed Oil; 0.1 mass_fraction dpg | 150 | 6 | 2.6 | 2 | 0.01 | NO_ALIAS_CANDIDATE_YAML; NO_PROFILE; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 271 | Safraleine; 1 neat  | 174.24 | 0.02 | 2.3 / 3.1 | 0.1 | 0.02 | logp:LOCAL_CONFLICT |
| 272 | Coriander Essential Oil; 1 neat  | 154.25 | 15 | 3.2 | 1.5 | 0.5 | No local scalar conflict detected; external verification incomplete |
| 273 | Pink Pepper EO; 1 neat  | 136.23 | 0.4 | 3.5 | 2 | 0.3 | No local scalar conflict detected; external verification incomplete |
| 274 | Black Pepper EO; 1 neat  | 204.35 | 0.3 | 4.5 | 2 | 0.3 | NO_PROFILE |
| 275 | Cardamom EO; 1 neat  | 170.25 | 15 | 2.5 | 3 | 0.5 | No local scalar conflict detected; external verification incomplete |
| 276 | Ethyl Safranate; 0.1 unspecified  | 168.23 / 194.27 | 0.05 | 2.5 | 0.5 | 0.1 | mw_g_mol:LOCAL_CONFLICT |
| 277 | Eugenol; 1 neat  | 164.2 | 0.01 | 2.2 / 2.49 | 6 | 1 | logp:LOCAL_CONFLICT |
| 278 | Eugenol; 0.1 unspecified  | 164.2 | 0.01 | 2.2 / 2.49 | 6 | 1 | logp:LOCAL_CONFLICT |
| 279 | Isoeugenol; 1 neat  | 164.2 | 0.005 | 2.58 | 6 | 0.4 | No local scalar conflict detected; external verification incomplete |
| 280 | Clove EO; 1 neat  | 164.2 | 2.5 | 2.5 | 3 | 0.5 | NO_PROFILE |
| 281 | Anise EO; 1 neat  | 148.2 | 5 | 3.3 | 5 | 1 | NO_PROFILE; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 282 | Cinnamaldehyde; 0.01 unspecified  | 132.16 | 0.05 | 1.9 | 62 | 0.05 | No local scalar conflict detected; external verification incomplete |
| 283 | Cinnamon Bark EO - Telvada USDA Organic; 1 neat  | — | — | — | — | — | NO_ALIAS_CANDIDATE_YAML; NO_PROFILE; NO_RUNTIME_ODT; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 284 | Nutmeg EO; 1 neat  | — | — | — | 10 | 2 | NO_PROFILE; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 285 | Lavender EO; 0.01 unspecified  | 170 | 3.5 | 2.2 / 2.5 | 2 | 5 | logp:LOCAL_CONFLICT |
| 286 | Lavender EO High Altitude; 1 neat  | 154.3 / 170 | 22 / 0.5 | 2.3 / 2.5 | 2 | 5 | mw_g_mol:LOCAL_CONFLICT; vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; NO_PROFILE |
| 287 | Lavender EO; 1 neat  | 170 / 154.3 | 3.5 / 22 | 2.2 / 2.3 / 2.5 | 2 | 5 | mw_g_mol:LOCAL_CONFLICT; vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; MULTIPLE_YAML_CANDIDATES |
| 288 | Spike Lavender EO; 1 neat  | 154.3 / 154 / 170 | 0.3 / 70 | 2.4 / 3.2 / 3 | 20 / 15 | 3 | mw_g_mol:LOCAL_CONFLICT; vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; odt_air_ppb:LOCAL_CONFLICT; NO_PROFILE; MULTIPLE_YAML_CANDIDATES; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 289 | Beta-Pinene; 1 neat  | 136.23 / 136.2 / 136.24 | 390 / 400 / 320 | 3.1 / 4.2 | 25 / 3 | 0.5 / 0.6 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; odt_air_ppb:LOCAL_CONFLICT; odt_eth_ppm:LOCAL_CONFLICT; MULTIPLE_YAML_CANDIDATES |
| 290 | Pine EO; 1 neat  | 136.2 / 136.23 | 180 / 250 | 4.3 / 4.2 | 25 / 12 | 5 | vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; odt_air_ppb:LOCAL_CONFLICT; NO_PROFILE; MULTIPLE_YAML_CANDIDATES; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 291 | Juniper Berry EO; 1 neat  | 136.2 / 170 | 65 / 0.5 | 4.3 / 3.8 | 10 / 15 | 3 | mw_g_mol:LOCAL_CONFLICT; vp_25c_pa:LOCAL_CONFLICT; logp:LOCAL_CONFLICT; odt_air_ppb:LOCAL_CONFLICT; NO_PROFILE; MULTIPLE_YAML_CANDIDATES |
| 292 | Rosemary EO; 1 neat  | 170 | 0.3 | 2.8 / 3.2 | 20 / 7 | 0.15 / 5 | logp:LOCAL_CONFLICT; odt_air_ppb:LOCAL_CONFLICT; odt_eth_ppm:LOCAL_CONFLICT; NO_PROFILE |
| 293 | Clary Sage EO; 1 neat  | 196.3 / 196.29 | 5 | 3.5 | 2 | 3 | No local scalar conflict detected; external verification incomplete |
| 294 | Basil EO; 1 neat  | 152 | 8 | 3 | 5 | 1 | NO_PROFILE; NO_NATURAL_COMPOSITE_FOR_PARSED_NAME |
| 295 | Patchouli EO; 1 neat  | 222.4 / 222.37 | 0.001 | 4.1 / 4.5 | 3 | 2 | logp:LOCAL_CONFLICT |
| 296 | Cassia Essential Oil; 1 neat  | 135 | 2.5 | 2 | 1.5 | 0.2 | MULTIPLE_YAML_CANDIDATES |
| 297 | Olibanum Resinoid; 0.5 mass_fraction dpg | 220 | 0.08 | 3 | 10 | 3 | MULTIPLE_YAML_CANDIDATES |
| 298 | Caryophyllene Acetate; 0.2 mass_fraction  | — | — | — | — | — | NO_PROFILE; NO_RUNTIME_ODT |
| 301 | Champignol; 0.1 unspecified dpg | 128.21 | 70.8 | 2.7 | 0.1 | 0.01 | No local scalar conflict detected; external verification incomplete |
| 302 | Jasmine Sambac; 0.1 unspecified dpg | 170 | 0.005 | 3 | 1 | 1.5 / 0.5 | odt_eth_ppm:LOCAL_CONFLICT; NO_RUNTIME_ODT; MULTIPLE_YAML_CANDIDATES |
| 303 | Leather FO; 1 neat  | 200 | 0.005 | 3 | 0.1 | 0.2 | No local scalar conflict detected; external verification incomplete |
| 304 | BHT; 1 neat  | 220.35 | 0.001 | 5.3 | 100000 | 500 | No local scalar conflict detected; external verification incomplete |
| 305 | Melonal; 1 neat  | 140.22 | 239 | 2.5 | 0.5 | 0.3 | No local scalar conflict detected; external verification incomplete |
| 306 | Dimethyl Benzyl Carbinyl Acetate; 1 neat  | 192.25 | 6.67 | 3.5 / 2.7 | 3 | 0.1 | logp:LOCAL_CONFLICT; NO_RUNTIME_ODT; MULTIPLE_YAML_CANDIDATES |
| 307 | Methyl Nonyl Ketone; 1 neat  | 170.3 / 170.29 | 0.05 | 4.1 / 3.5 | 5 | 0.3 | logp:LOCAL_CONFLICT |
| 308 | Cassis Base 345B; 1 neat  | 160 | 0.5 | 2.5 | 0.5 | 0.1 | No local scalar conflict detected; external verification incomplete |
