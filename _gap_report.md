# material_properties.json — Field Provenance Report

**210 total entries.** All have odt and odt_ethanol_ppm at minimum.

---

## AUTHORITATIVE — sourced from engine modules

| Field | Description | Coverage | Source |
|---|---|---|---|
| mw | Molecular weight | 187/210 (89%) | ingredient_intelligence.py |
| vp | Vapor pressure (Pa) | 187/210 (89%) | ingredient_intelligence.py |
| clp | cLogP | 187/210 (89%) | ingredient_intelligence.py |
| odt | ODT air (ppb) | 197/210 (94%) | odor_thresholds.py |
| odt_ethanol_ppm | ODT ethanol (ppm) | 197/210 (94%) | odor_thresholds.py |
| note | Volatility note (top/heart/base) | 187/210 (89%) | ingredient_intelligence.py |
| role | Perfumery role | 187/210 (89%) | ingredient_intelligence.py |
| texture | Texture (halo/veil/diffusion/etc) | 187/210 (89%) | ingredient_intelligence.py |
| synergies | Synergies list | 95/210 (45%) | ingredient_intelligence.py |
| or_family | Olfactory family (Raoult) | 95/210 (45%) | ingredient_intelligence.py |
| activity_coef | Activity coefficient | 95/210 (45%) | ingredient_intelligence.py |
| hedonic | Hedonic score | 69/210 (33%) | ingredient_intelligence.py |
| hill_ec50/hill_n | Hill dose-response params | 25/210 (12%) | dose_response.py |
| character_shift | Character shift zones | 29/210 (14%) | dose_response.py |
| ifra_cat4_limit_pct | IFRA Cat4 limit | 81/210 (39%) | ifra_safety.py |
| arctander_character | Arctander description | 106/210 (50%) | material_properties.json (hand-crafted) |
| carles_position | Carles position | 106/210 (50%) | material_properties.json (hand-crafted) |
| sar_class | SAR class | 106/210 (50%) | material_properties.json (hand-crafted) |
| olfactophore | Olfactophore | 105/210 (50%) | material_properties.json (hand-crafted) |

---

## ESTIMATED/CALCULATED — computed by generation script, NOT literature-verified

| Field | Description | Coverage | Method |
|---|---|---|---|
| oav_typical | OAV at typical dose | 104/210 (50%) | dose_pct * 10000 / odt_eth; dose_pct from role/ODT heuristic |
| smell_strength | Smell strength (ultra-strong through very-weak) | 104/210 (50%) | derived from odt_eth ranges |
| anosmic_risk | Anosmia risk flag | 104/210 (50%) | derived from odt_air < 0.01 ppb |
| odor_family | Odor family | 210/210 (100%) | from profile or_family; fallback = keyword match on ODT char description |
| odor_profile | Odor profile text | 210/210 (100%) | generated from profile character dimensions; fallback = ODT char string |
| oav_dose_pct | Estimated typical dose % | 104/210 (50%) | heuristic: role-based defaults + ODT-based tiers |
| typical_pct_range | Typical % range string | 205/210 (98%) | 0.3x to 2x dose_pct; 5 entries null (solvents) |
| arctander_character | Arctander description (new entries) | 103/210 (49%) | copied from ODT char description string when no hand-crafted entry existed |
| best_with | Best-with list (new entries) | 95/210 (45%) | copied from profile synergies when no hand-crafted entry existed |

---

## NULL — needs Perplexity/external fill

| Field | Null count | Notes |
|---|---|
| cas | 104 | CAS number — needs external fill |
| bp | 105 | Boiling point — needs external fill |
| formula_str | 106 | Molecular formula — needs external fill |
| sar_class | 104 | SAR class — only in 106 hand-crafted entries |
| olfactophore | 105 | Olfactophore — only in 105 hand-crafted entries |
| carles_position | 104 | Carles position — only in 106 hand-crafted entries |
| carles_pairing_rule | 108 | Carles pairing rule |
| roudnitska_function | 104 | Roudnitska function |
| roudnitska_craft_note | 210 | Roudnitska craft note — ALL null |
| jellinek_axis | 109 | Jellinek axis |
| jellinek_quadrant | 105 | Jellinek quadrant |
| jellinek_effect | 109 | Jellinek effect |
| stock_form | 105 | Stock form description |
| handle_as | 105 | Handle-as pragmatic advice |
| avoid | 110 | Avoid advice |
| ifra_banned | 209 | IFRA banned flag — only Lilial=True, rest null/false |
| dilution_pct | 106 | Inventory dilution % |

---

## Per-material detail: ESTIMATED vs AUTHORITATIVE

| # | Material | odt_air | odt_eth | mw | vp | note | role | synergies | hedge | oav | smell | anosmic |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ALDEHYDE C10 | 0.0004 | 0.081 | 156.27 | 8.2 | - | - | - | Y | - | - | - |
| 2 | ALDEHYDE C11 | 0.0008 | 0.12 | 170.29 | 0.67 | - | - | - | Y | - | - | - |
| 3 | ALDEHYDE C12 MNA | 0.001 | 0.05 | 184.32 | 0.01 | - | - | - | Y | - | - | - |
| 4 | ALLYL IONONE | 0.003 | 0.5 | 232.36 | 0.0664 | - | - | - | Y | - | - | - |
| 5 | ALPHA IONONE | 0.0004 | 0.1 | 192.3 | 1.35 | - | - | - | Y | - | - | - |
| 6 | ALPHA IRONE | 0.0001 | 0.01 | 206.33 | 0.07 | - | - | - | Y | - | - | - |
| 7 | AMBER CORE | 0.05 | 0.2 | 250.0 | 0.01 | - | - | - | Y | - | - | - |
| 8 | AMBER CORE ACCORD | 0.05 | 0.2 | 250.0 | 0.01 | - | - | - | Y | - | - | - |
| 9 | AMBER XTREME | 0.003 | 0.15 | 214.35 | 0.003 | - | - | - | Y | - | - | - |
| 10 | AMBERMAX | 0.01 | 0.1 | 168.28 | 0.005 | - | - | - | Y | - | - | - |
| 11 | AMBRETTOLIDE | 0.005 | 0.5 | 252.4 | 0.001 | - | - | - | Y | - | - | - |
| 12 | AMBROFIX | 0.0003 | 0.05 | 236.4 | 0.05 | - | - | - | Y | - | - | - |
| 13 | AMBROX SUPER | 0.0003 | 0.05 | 236.4 | 0.05 | - | - | - | Y | - | - | - |
| 14 | AURANTIOL | 0.01 | 0.3 | 305.41 | 0.01 | - | - | - | Y | - | - | - |
| 15 | Aldehyde C11 undecylenic | 0.8 | 0.4 | 168.28 | 0.1 | top | trace | Y | Y | Y | Y | Y |
| 16 | Allyl Amyl Glycolate | 2.0 | 0.3 | 158.19 | 0.2 | top | character | Y | Y | Y | Y | Y |
| 17 | Alpha Damascone | 1.5 | 0.05 | 192.3 | 1.11 | heart | character | Y | Y | Y | Y | Y |
| 18 | Alpha Isomethyl Ionone | 5.0 | 0.5 | 206.33 | 0.4 | heart | modifier | Y | Y | Y | Y | Y |
| 19 | Amberwood F | 1.0 | 0.3 | 234.0 | 0.001 | base | modifier | Y | Y | Y | Y | Y |
| 20 | Amyl Cinnamic Aldehyde | 2.0 | 2.0 | None | None | None | None | - | - | Y | Y | Y |
| 21 | Anisaldehyde | 32.0 | 0.057 | 136.15 | 0.04 | heart | modifier | Y | Y | Y | Y | Y |
| 22 | Apritone | 3.5 | 0.52 | 178.27 | 0.05 | top | character | Y | Y | Y | Y | Y |
| 23 | Azarbre | 2.0 | 0.5 | 220.0 | 4.3 | base | modifier | Y | Y | Y | Y | Y |
| 24 | BACDANOL | 0.005 | 0.08 | 208.34 | 0.03 | - | - | - | Y | - | - | - |
| 25 | BENZOIN RESINOID | 0.01 | 20.0 | 228.24 | 0.001 | - | - | - | Y | - | - | - |
| 26 | BENZOIN SUMATRA RESINOID | 0.1 | 10.0 | 212.24 | 0.0001 | - | - | - | Y | - | - | - |
| 27 | BENZYL BENZOATE | 20.0 | 0.15 | 212.24 | 0.002 | - | - | - | Y | - | - | - |
| 28 | BENZYL SALICYLATE | 1.0 | 0.24 | 228.24 | 0.003 | - | - | - | Y | - | - | - |
| 29 | BERGAMOT EO | 0.001 | 3.0 | 154.0 | 1.5 | - | - | - | Y | - | - | - |
| 30 | BERGAMOT FCF | 0.003 | 1.5 | 154.0 | 1.5 | - | - | - | Y | - | - | - |
| 31 | BETA IONONE | 7e-06 | 0.05 | 192.3 | 0.85 | - | - | - | Y | - | - | - |
| 32 | BIRCH TAR RECTIFIED | 0.001 | 0.3 | 124.14 | 0.1 | - | - | - | Y | - | - | - |
| 33 | BLACK PEPPER FTEC | 0.02 | 1.0 | 204.35 | 0.1 | - | - | - | Y | - | - | - |
| 34 | BLACKCURRANT FTEC | 1e-05 | 0.08 | 160.0 | 0.5 | - | - | - | Y | - | - | - |
| 35 | Benzyl Acetate | 130.0 | 0.055 | 150.17 | 0.22 | heart | character | Y | Y | Y | Y | Y |
| 36 | Bergamot FCF oil Sicilian | 15.0 | 1.5 | 136.23 | 2.5 | top | character | Y | Y | Y | Y | Y |
| 37 | Beta-Pinene | 8.0 | 0.08 | 136.24 | 320.0 | top | modifier | Y | Y | Y | Y | Y |
| 38 | Black Pepper EO | 2.0 | 0.3 | 204.35 | 0.3 | top | character | Y | Y | Y | Y | Y |
| 39 | Blood Orange oil Sicilian | 8.0 | 2.0 | 136.23 | 3.0 | top | character | Y | Y | Y | Y | Y |
| 40 | Bourgeonal | 0.03 | 0.05 | 176.25 | 0.01 | heart | modifier | Y | Y | Y | Y | Y |
| 41 | CALONE | 2.5e-05 | 0.02 | 178.19 | 0.15 | - | - | - | Y | - | - | - |
| 42 | CARDAMOM EO | 25.0 | 0.5 | 154.3 | 15.0 | - | - | - | - | - | - | - |
| 43 | CARDAMOM FTEC | 1.0 | 3.0 | 170.0 | 0.3 | - | - | - | Y | - | - | - |
| 44 | CARROT SEED EO | 0.1 | 1.0 | 222.37 | 0.02 | - | - | - | Y | - | - | - |
| 45 | CASHMERAN | 0.08 | 0.03 | 206.33 | 1.2 | - | - | - | Y | - | - | - |
| 46 | CEDAMBER | 0.05 | 0.2 | 210.0 | 0.005 | - | - | - | Y | - | - | - |
| 47 | CEDARWOOD EO | 0.02 | 3.0 | 222.37 | 9.37 | - | - | - | Y | - | - | - |
| 48 | CEDRAMBER | 0.02 | 0.2 | 212.33 | 0.35 | - | - | - | Y | - | - | - |
| 49 | CITRAL | 0.003 | 0.032 | 152.23 | 5.0 | - | - | - | Y | - | - | - |
| 50 | CITRONELLAL | 0.005 | 0.015 | 154.25 | 40.0 | - | - | - | Y | - | - | - |
| 51 | COUMARIN | 0.002 | 0.02 | 146.14 | 0.02 | - | - | - | Y | - | - | - |
| 52 | CYCLAMEN ALDEHYDE | 0.01 | 0.0025 | 190.28 | 0.52 | - | - | - | Y | - | - | - |
| 53 | Cedarwood oil Virginia | 15.0 | 3.0 | 222.37 | 0.005 | base | character | Y | Y | Y | Y | Y |
| 54 | Cedrat FCF oil Sicilian | 12.0 | 2.0 | 152.23 | 2.0 | top | character | Y | Y | Y | Y | Y |
| 55 | Champaca Flower EO | 8.0 | 1.5 | 200.0 | 0.03 | heart | character | Y | Y | Y | Y | Y |
| 56 | Cinnamaldehyde | 62.0 | 0.05 | 132.16 | 0.05 | heart | character | Y | Y | Y | Y | Y |
| 57 | Cinnamyl alcohol 50% in DPG | 3.0 | 0.081 | 134.18 | 0.03 | heart | modifier | Y | - | Y | Y | Y |
| 58 | Cis Jasmone | 0.5 | 0.1 | 164.24 | 1.333 | heart | modifier | Y | Y | Y | Y | Y |
| 59 | Citronellol | 11.0 | 0.04 | 156.27 | 0.02 | heart | modifier | Y | Y | Y | Y | Y |
| 60 | Clary Sage EO | 15.0 | 3.0 | 196.29 | 5 | top | character | Y | Y | Y | Y | Y |
| 61 | Clearwood | 5.0 | 1.0 | 222.37 | 0.002 | base | modifier | Y | Y | Y | Y | Y |
| 62 | Costus Olifac | 10.0 | 2.0 | 200.0 | 0.001 | base | trace | Y | Y | Y | Y | Y |
| 63 | Cyclimal Aldehyde | 0.1 | 0.0025 | None | None | None | None | - | - | Y | Y | Y |
| 64 | D-Limonene | 10.0 | 2.0 | 136.23 | 190 | top | modifier | Y | Y | Y | Y | Y |
| 65 | DEP | 100.0 | 500.0 | 222.24 | 0.002 | - | - | - | - | - | - | - |
| 66 | DEWBERRY FTEC | 0.01 | 6.0 | 180.0 | 0.1 | - | - | - | Y | - | - | - |
| 67 | DIHYDRO BETA IONONE | 0.02 | 0.3 | 194.31 | 0.8 | - | - | - | Y | - | - | - |
| 68 | DIHYDROMYRCENOL | 0.01 | 0.3 | 156.27 | 14.8 | - | - | - | Y | - | - | - |
| 69 | DIPROPYLENE GLYCOL | 1000.0 | 10000.0 | 134.17 | 2.1 | - | - | - | - | - | - | - |
| 70 | Damascenone | 0.002 | 0.002 | 190.3 | 0.693 | heart | trace | Y | Y | Y | Y | Y |
| 71 | Damascol | 0.05 | 0.005 | 194.3 | 0.6 | heart | character | Y | Y | Y | Y | Y |
| 72 | Damascone Beta | 0.004 | 0.004 | 190.3 | 0.08 | heart | modifier | Y | Y | Y | Y | Y |
| 73 | Delta Decalactone | 10.0 | 2.0 | 170.25 | 0.003 | heart | modifier | Y | Y | Y | Y | Y |
| 74 | Dihydrojasmone | 50.0 | 10.0 | 166.26 | 7.67 | heart | modifier | Y | Y | Y | Y | Y |
| 75 | Dimethyl Benzyl Carbinyl Acetate | 0.5 | 0.1 | 192.25 | 0.8 | heart | character | Y | - | Y | Y | Y |
| 76 | Dynascone | 0.3 | 0.05 | 192.3 | 0.15 | top | trace | Y | Y | Y | Y | Y |
| 77 | EBANOL | 0.003 | 1.5 | 208.34 | 0.02 | - | - | - | Y | - | - | - |
| 78 | ETHANOL 96% | 90.0 | 1000.0 | 46.07 | 5900.0 | - | - | - | - | - | - | - |
| 79 | ETHYL MALTOL | 0.0001 | 0.1 | 140.14 | 0.05 | - | - | - | Y | - | - | - |
| 80 | ETHYLENE BRASSYLATE | 0.5 | 2.0 | 270.37 | 0.0005 | - | - | - | Y | - | - | - |
| 81 | EXALTOLIDE | 0.01 | 1.0 | 240.38 | 0.001 | - | - | - | Y | - | - | - |
| 82 | Ethyl 2-Methylbutyrate | 0.06 | 0.02 | 130.18 | 5.0 | top | modifier | Y | Y | Y | Y | Y |
| 83 | Ethyl Linalool | 8.0 | 1.5 | 182.3 | 0.08 | top | modifier | Y | Y | Y | Y | Y |
| 84 | Ethyl Safranate | 0.5 | 0.1 | 168.23 | 0.05 | heart | character | Y | Y | Y | Y | Y |
| 85 | Ethyl Vanillin | 6.0 | 3.0 | 166.17 | 0.0002 | base | character | Y | Y | Y | Y | Y |
| 86 | Eugenol | 6.0 | 1.0 | 164.2 | 0.01 | heart | character | Y | Y | Y | Y | Y |
| 87 | Evernyl | 2.0 | 0.5 | 196.2 | 0.129 | base | character | Y | Y | Y | Y | Y |
| 88 | FLORALOZONE | 0.05 | 0.1 | 172.27 | 5.0 | - | - | - | Y | - | - | - |
| 89 | FLOROL | 0.01 | 2.0 | 138.21 | 0.007 | - | - | - | Y | - | - | - |
| 90 | Farnesol | 50.0 | 10.0 | 222.4 | 0.08 | heart | fixative | Y | Y | Y | Y | Y |
| 91 | Freesia HDI | 3.0 | 0.5 | 170.25 | 0.02 | heart | modifier | Y | Y | Y | Y | Y |
| 92 | GALAXOLIDE | 0.9 | 1.0 | 258.4 | 0.07 | - | - | - | Y | - | - | - |
| 93 | GALBANUM RESINOID | 0.001 | 1.0 | 192.0 | 0.05 | - | - | - | Y | - | - | - |
| 94 | GERANIOL | 0.005 | 5.0 | 154.25 | 3.0 | - | - | - | Y | - | - | - |
| 95 | GRAPEFRUIT FCF | 0.001 | 1.0 | 136.23 | 1.5 | - | - | - | Y | - | - | - |
| 96 | GUAIACOL | 0.003 | 0.5 | 124.14 | 0.053 | - | - | - | Y | - | - | - |
| 97 | Gamma Decalactone | 1.5 | 0.3 | 170.25 | 0.005 | heart | character | Y | Y | Y | Y | Y |
| 98 | Gamma Undecalactone | 1.0 | 0.2 | 184.28 | 0.002 | heart | character | Y | Y | Y | Y | Y |
| 99 | Geosmin | 0.006 | 0.001 | 182.3 | 0.1 | heart | trace | Y | Y | Y | Y | Y |
| 100 | HABANOLIDE | 0.005 | 0.2 | 238.37 | 0.003 | - | - | - | Y | - | - | - |
| 101 | HEDIONE | 0.5 | 3.0 | 226.31 | 0.1 | - | - | - | Y | - | - | - |
| 102 | HELIOTROPIN | 0.01 | 1.0 | 150.13 | 0.6 | - | - | - | - | - | - | - |
| 103 | HEXYL ACETATE | 0.002 | 0.5 | 144.21 | 194.0 | - | - | - | Y | - | - | - |
| 104 | HYDROXYCITRONELLAL | 0.01 | 3.0 | 172.27 | 0.3 | - | - | - | Y | - | - | - |
| 105 | Helional | 0.5 | 0.1 | 192.21 | 0.01 | heart | modifier | Y | Y | Y | Y | Y |
| 106 | Heliotropal | 5.0 | 1.0 | 150.13 | 1.33 | base | modifier | Y | Y | Y | Y | Y |
| 107 | Heliotropin Fleuressence | 3.0 | 0.8 | 150.13 | 0.003 | heart | modifier | Y | Y | Y | Y | Y |
| 108 | Hexyl Salicylate | 3.0 | 30.0 | 222.28 | 0.077 | base | fixative | Y | Y | Y | Y | Y |
| 109 | I-IRIS F-TEC | 0.3 | 0.3 | 210.0 | 0.005 | - | - | - | Y | - | - | - |
| 110 | ISO E SUPER | 0.04 | 2.0 | 234.38 | 0.03 | - | - | - | Y | - | - | - |
| 111 | ISOBUTYL QUINOLINE | 0.001 | 0.02 | 185.27 | 0.05 | - | - | - | Y | - | - | - |
| 112 | ISOPROPYL MYRISTATE | 500.0 | 1000.0 | 270.45 | 0.001 | - | - | - | - | - | - | - |
| 113 | Indole | 0.3 | 0.05 | 117.15 | 0.01 | heart | trace | Y | Y | Y | Y | Y |
| 114 | Irotyl | 1.0 | 0.2 | 206.33 | 0.005 | heart | modifier | Y | Y | Y | Y | Y |
| 115 | Isoeugenol | 6.0 | 0.4 | 164.2 | 0.005 | heart | modifier | Y | Y | Y | Y | Y |
| 116 | JASMIN ABS F-TEC | 0.002 | 2.0 | 180.0 | 0.005 | - | - | - | Y | - | - | - |
| 117 | JASMINE FO | 0.005 | 3.0 | 200.0 | 0.02 | - | - | - | Y | - | - | - |
| 118 | Javanol | 3.0 | 0.5 | 210.36 | 0.03 | base | character | Y | Y | Y | Y | Y |
| 119 | Jessemal | 5.0 | 1.0 | 214.3 | 0.5 | heart | modifier | Y | Y | Y | Y | Y |
| 120 | Juniper Berry EO | 15.0 | 3.0 | 170.0 | 0.5 | top | character | Y | Y | Y | Y | Y |
| 121 | KEPHALIS | 0.002 | 0.1 | 194.27 | 0.1 | - | - | - | Y | - | - | - |
| 122 | Koavone | 2.0 | 0.5 | 206.33 | 14.87 | base | modifier | Y | Y | Y | Y | Y |
| 123 | LABDANUM ABSOLUTE | 0.1 | 2.0 | 290.0 | 0.001 | - | - | - | Y | - | - | - |
| 124 | LAVENDER EO | 0.003 | 5.0 | 196.29 | 0.3 | - | - | - | Y | - | - | - |
| 125 | LAVENDER EO (BONTAUX SAS) | 10.0 | 3.0 | 154.3 | 22.0 | - | - | - | - | - | - | - |
| 126 | LEATHER FO | 0.02 | 0.2 | 180.0 | 0.03 | - | - | - | Y | - | - | - |
| 127 | LINALOOL | 0.006 | 1.0 | 154.25 | 22.7 | - | - | - | Y | - | - | - |
| 128 | LINALYL ACETATE | 0.02 | 8.0 | 196.29 | 17.5 | - | - | - | Y | - | - | - |
| 129 | Lavender EO High Altitude | 20.0 | 5.0 | 170.0 | 0.5 | top | character | Y | Y | Y | Y | Y |
| 130 | Leafovert | 8.0 | 0.05 | 154.25 | 0.5 | top | character | Y | Y | Y | Y | Y |
| 131 | Lemon FCF oil Sicilian | 10.0 | 2.0 | None | None | None | None | - | - | Y | Y | Y |
| 132 | Lemonile | 10.0 | 2.0 | 151.23 | 0.2 | top | character | Y | Y | Y | Y | Y |
| 133 | Lilial | 5.0 | 0.5 | 204.31 | 0.33 | heart | character | Y | Y | Y | Y | Y |
| 134 | Lilyreal ND | 2.0 | 0.3 | 192.3 | 0.01 | heart | character | Y | Y | Y | Y | Y |
| 135 | Lime Distilled EO | 12.0 | 2.0 | 170.0 | 1.8 | top | character | Y | Y | Y | Y | Y |
| 136 | MACROLIDE | 0.05 | 1.5 | 256.0 | 0.001 | - | - | - | Y | - | - | - |
| 137 | MAPLE LACTONE | 1e-05 | 0.2 | 142.15 | 2.0 | - | - | - | Y | - | - | - |
| 138 | METHYL IONONE | 0.003 | 0.3 | 206.33 | 0.2 | - | - | - | Y | - | - | - |
| 139 | METHYL PAMPLEMOUSSE | 0.0001 | 0.5 | 180.0 | 0.05 | - | - | - | Y | - | - | - |
| 140 | MOLECULE IRIS | 0.003 | 0.1 | 206.0 | 0.2 | - | - | - | - | - | - | - |
| 141 | MUSK KETONE | 0.5 | 2.0 | 294.3 | 0.0001 | - | - | - | Y | - | - | - |
| 142 | MYRRH EO | 0.1 | 5.0 | 222.37 | 0.01 | - | - | - | Y | - | - | - |
| 143 | Mayol | 3.0 | 0.5 | 166.3 | 1.5 | heart | character | Y | Y | Y | Y | Y |
| 144 | Melonal | 1.5 | 0.3 | 156.22 | 0.5 | top | modifier | Y | Y | Y | Y | Y |
| 145 | Methyl Anthranilate | 2.0 | 0.4 | 151.16 | 0.03 | heart | modifier | Y | Y | Y | Y | Y |
| 146 | Methyl Benzoate | 200.0 | 40.0 | 136.15 | 40.0 | heart | modifier | Y | Y | Y | Y | Y |
| 147 | Methyl Nonyl Ketone | 2.0 | 0.3 | 170.29 | 0.05 | heart | modifier | Y | Y | Y | Y | Y |
| 148 | Methyl Salicylate | 40.0 | 8.0 | 152.15 | 5.3 | heart | modifier | Y | Y | Y | Y | Y |
| 149 | Myristic Acid Powder | 5000.0 | 1000.0 | 228.38 | 0.013 | base | fixative | Y | Y | Y | Y | Y |
| 150 | NORLIMBANOL DEXTRO | 1e-05 | 0.1 | 208.34 | 0.01 | - | - | - | Y | - | - | - |
| 151 | Nagarmortha Oil | 5.0 | 1.0 | None | None | None | None | - | - | Y | Y | Y |
| 152 | Nympheal | 2.0 | 0.4 | 204.31 | 0.01 | heart | radiance | Y | Y | Y | Y | Y |
| 153 | OLIBANUM RESINOID | 0.02 | 3.0 | 220.0 | 0.02 | - | - | - | Y | - | - | - |
| 154 | ORIVONE | 0.5 | 0.5 | 168.28 | 0.5 | - | - | - | Y | - | - | - |
| 155 | ORRIS F-TEC | 0.01 | 0.3 | 206.0 | 0.02 | - | - | - | Y | - | - | - |
| 156 | Orange Peel EO | 10.0 | 2.0 | 136.23 | 1.9 | top | character | Y | Y | Y | Y | Y |
| 157 | Oranger Crystals | 250.0 | 1.0 | 170.21 | 0.08 | heart | character | Y | Y | Y | Y | Y |
| 158 | Oud Fleuressence | 0.5 | 0.1 | 220.0 | 0.001 | base | character | Y | Y | Y | Y | Y |
| 159 | PATCHOULI ESSENTIAL OIL | 0.02 | 2.0 | 222.37 | 0.01 | - | - | - | - | - | - | - |
| 160 | PEONILE | 0.002 | 1.0 | 192.3 | 0.3 | - | - | - | Y | - | - | - |
| 161 | PHENETHYL ALCOHOL | 4.0 | 40.0 | 122.16 | 4.5 | - | - | - | Y | - | - | - |
| 162 | PINK PEPPER BASE | 0.1 | 1.0 | 204.35 | 0.05 | - | - | - | Y | - | - | - |
| 163 | Paradisamide | 0.5 | 0.1 | 215.0 | 0.002 | heart | character | Y | Y | Y | Y | Y |
| 164 | Parmavert | 15.0 | 3.0 | 192.3 | 0.1 | top | character | Y | Y | Y | Y | Y |
| 165 | Patchouli EO | 10.0 | 2.0 | 222.37 | 0.001 | base | character | Y | Y | Y | Y | Y |
| 166 | Petitgrain EO | 12.0 | 2.5 | 170.0 | 6 | top | character | Y | Y | Y | Y | Y |
| 167 | Phenyl Ethyl Dimethyl Carbinol | 3.0 | 0.8 | 164.24 | 0.3 | heart | modifier | Y | - | Y | Y | Y |
| 168 | Pine EO | 25.0 | 5.0 | 136.23 | 180.0 | top | character | Y | Y | Y | Y | Y |
| 169 | Polysantol | 0.01 | 0.5 | 222.37 | 0.003 | base | character | Y | Y | Y | Y | Y |
| 170 | RASPBERRY KETONE | 0.01 | 0.08 | 164.2 | 0.03 | - | - | - | Y | - | - | - |
| 171 | ROMANDOLIDE | 0.5 | 1.0 | 214.26 | 0.05 | - | - | - | Y | - | - | - |
| 172 | ROSE OXIDE | 0.0005 | 0.001 | 154.25 | 53.0 | - | - | - | Y | - | - | - |
| 173 | Red Mandarin EO | 10.0 | 2.0 | 136.23 | 1.8 | top | character | Y | Y | Y | Y | Y |
| 174 | Rosemary EO | 20.0 | 5.0 | None | None | None | None | - | - | Y | Y | Y |
| 175 | SANDALWOOD FRAGRANCE OIL | 0.01 | 1.5 | 220.0 | 0.003 | - | - | - | - | - | - | - |
| 176 | SCENTENAL | 0.0001 | 0.05 | 152.0 | 2.0 | - | - | - | Y | - | - | - |
| 177 | STYRAX FTEC | 0.05 | 0.8 | 192.0 | 0.01 | - | - | - | Y | - | - | - |
| 178 | SUEDERAL | 0.05 | 0.5 | 164.24 | 1.0 | - | - | - | Y | - | - | - |
| 179 | Sandalore | 10.0 | 2.0 | 210.36 | 0.08 | base | modifier | Y | Y | Y | Y | Y |
| 180 | Sandalwood FO | 8.0 | 1.5 | 210.0 | 0.001 | base | modifier | Y | Y | Y | Y | Y |
| 181 | Siam Benzoin | 50.0 | 10.0 | 212.24 | 0.0001 | base | fixative | Y | Y | Y | Y | Y |
| 182 | Skatole | 0.3 | 0.05 | 131.17 | 0.01 | base | trace | Y | Y | Y | Y | Y |
| 183 | Spike Lavender EO | 15.0 | 3.0 | 170.0 | 0.3 | top | character | Y | Y | Y | Y | Y |
| 184 | TERPINYL ACETATE | 3.0 | 15.0 | 196.29 | 5.0 | - | - | - | Y | - | - | - |
| 185 | TONALIDE | 0.15 | 1.0 | 258.4 | 0.07 | - | - | - | Y | - | - | - |
| 186 | TONKA BEAN FRAGRANCE OIL | 0.007 | 3.0 | 146.14 | 0.001 | - | - | - | - | - | - | - |
| 187 | TRIETHYL CITRATE | 1000.0 | 5000.0 | 276.28 | 0.02 | - | - | - | - | - | - | - |
| 188 | Timberol | 3.0 | 0.5 | 210.36 | 0.068 | base | character | Y | Y | Y | Y | Y |
| 189 | Tobacco FTEC | 5.0 | 1.0 | 200.0 | 0.01 | heart | character | Y | Y | Y | Y | Y |
| 190 | Tobacco Fleuressence | 5.0 | 1.0 | 200.0 | 0.01 | heart | character | Y | Y | Y | Y | Y |
| 191 | Tonka Bean FO | 15.0 | 3.0 | 180.0 | 0.001 | base | character | Y | Y | Y | Y | Y |
| 192 | Triplal | 0.5 | 0.001 | 152.23 | 0.5 | top | trace | Y | Y | Y | Y | Y |
| 193 | Ultralia | 0.3 | 0.05 | 222.37 | 0.002 | heart | trace | Y | Y | Y | Y | Y |
| 194 | Undecavertol | 10.0 | 2.0 | 170.29 | 0.06 | heart | modifier | Y | Y | Y | Y | Y |
| 195 | VANILLIN | 0.02 | 10.0 | 152.15 | 0.02 | - | - | - | Y | - | - | - |
| 196 | VERDOX | 2.0 | 5.0 | 198.3 | 3.0 | - | - | - | Y | - | - | - |
| 197 | VERTOFIX COEUR | 0.03 | 0.3 | 236.39 | 0.01 | - | - | - | Y | - | - | - |
| 198 | VETIVAL | 0.1 | 0.5 | 262.39 | 0.03 | - | - | - | Y | - | - | - |
| 199 | VETIVER EO (INDIA) | 15.0 | 2.0 | 222.4 | 0.04 | - | - | - | - | - | - | - |
| 200 | VETIVER ESSENTIAL OIL | 0.01 | 1.0 | 220.35 | 0.01 | - | - | - | - | - | - | - |
| 201 | VIOLET FLEURESSENCE | 0.007 | 1.0 | 192.0 | 0.05 | - | - | - | Y | - | - | - |
| 202 | Vertofix | 1.0 | 0.3 | 234.38 | 0.39 | base | fixative | Y | Y | Y | Y | Y |
| 203 | Vetikon | 5.0 | 1.0 | 222.37 | 0.002 | base | volume | Y | Y | Y | Y | Y |
| 204 | Vetiver EO | 5.0 | 1.0 | 222.37 | 0.003 | base | character | Y | Y | Y | Y | Y |
| 205 | Ylang Comoros Complete EO F3255 | 30.0 | 6.0 | 200.0 | 0.05 | heart | character | Y | Y | Y | Y | Y |
| 206 | Ylang Comoros III EO F3295 | 40.0 | 8.0 | 200.0 | 0.03 | heart | character | Y | Y | Y | Y | Y |
| 207 | Ylang Ylang EO | 30.0 | 6.0 | 200.0 | 0.05 | heart | character | Y | Y | Y | Y | Y |
| 208 | ZENOLIDE | 0.1 | 1.0 | 256.34 | 0.005 | - | - | - | Y | - | - | - |
| 209 | cis-3-Hexenol | 70.0 | 15.0 | 100.16 | 1.4 | top | character | Y | Y | Y | Y | Y |
| 210 | p-Cresyl Methyl Ether (PCME) | 0.5 | 0.1 | 122.16 | 40.0 | heart | trace | Y | - | Y | Y | Y |