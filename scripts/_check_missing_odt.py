"""Find missing ODT entries across all active formulas"""

import sys

sys.path.insert(0, ".")
from engine.odor_thresholds import ODT_DATA

materials = [
    "Iso E Super",
    "Cedarwood EO",
    "Kephalis",
    "Cashmeran",
    "Javanol",
    "Sandalore",
    "Ebanol",
    "Vertofix",
    "Azarbre",
    "Patchouli EO",
    "Olibanum Resinoid",
    "Siam Benzoin",
    "Labdanum Absolute",
    "Romandolide",
    "Ethylene Brassylate",
    "Musk Ketone",
    "Jasmine Absolute",
    "Hedione",
    "Hedione HC",
    "cis-Jasmone",
    "Benzyl Acetate",
    "Gamma Undecalactone",
    "Dihydrojasmone",
    "Indole",
    "Paradisamide",
    "Alpha Irone",
    "Myristic Acid",
    "Dihydro Beta Ionone",
    "Alpha Ionone",
    "Orivone",
    "Alpha Isomethyl Ionone",
    "Allyl Ionone",
    "Ultralia",
    "PEA",
    "Geraniol",
    "Rose Oxide",
    "Alpha Damascone",
    "Cardamom EO",
    "Bergamot FCF",
    "Petitgrain EO",
    "D-Limonene",
    "Ethyl Safranate",
    "Hexyl Salicylate",
    "Benzyl Salicylate",
    "Benzyl Benzoate",
    "Geosmin",
    "Cedrat FCF",
    "Calone",
    "Floralozone",
    "Scentenal",
    "Coumarin",
    "Heliotropal",
    "Ambrettolide",
    "Evernyl",
    "Vetiver EO",
    "Irotyl",
    "Red Mandarin EO",
    "Ethyl Linalool",
    "Habanolide",
    "Aldehyde C12 MNA",
    "Norlimbanol Dextro",
    "Nagarmortha Oil",
    "Costus Olifac",
    "Beta Ionone",
    "Dihydrojasmone",
    "Helional",
    "Ambrofix",
    "Ambrox Super",
    "Ambermax",
    "Clearwood",
    "Koavone",
    "Vetival",
    "Timberol",
    "Suederal",
    "Parmavert",
    "Leafovert",
    "Triplal",
    "Dynascone",
    "Undecavertol",
    "Linalyl Acetate",
    "Citronellol",
    "Damascenone",
    "Cinnamyl alcohol",
    "Aurantiol",
    "Freesia HDI",
    "Lilyreal ND",
    "Mayol",
    "Nympheal",
    "Bourgeonal",
    "PEDMC",
    "Farnesol",
    "Oranger Crystals",
    "Alpha Ionone",
    "Allyl Ionone",
    "Irotyl",
    "Carrot Seed EO",
    "Dihydro Beta Ionone",
    "Violet Fleuressence",
    "Polysantol",
    "Patchouli EO",
    "Vetiver India EO",
    "Galaxolide",
    "Tonalide",
    "Zenolide",
    "Exaltolide",
    "Macrolide",
    "Ethyl Maltol",
    "Vanillin",
    "Ethyl Vanillin",
    "Maple Lactone",
    "Raspberry Ketone",
    "Anisaldehyde",
    "Gamma Decalactone",
    "Delta Decalactone",
    "Allyl Amyl Glycolate",
    "Dihydromyrcenol",
    "cis-3-Hexenol",
    "Verdox",
    "Galbanum Resinoid",
    "Cyclamen Aldehyde",
    "Blood Orange",
    "Red Mandarin EO",
    "Lime Distilled EO",
    "Orange Peel EO",
    "Lemonile",
    "Methyl Benzoate",
    "Methyl Anthranilate",
    "Methyl Salicylate",
    "Terpinyl Acetate",
    "Apritone",
]


def nn(s):
    return s.lower().strip()


odt_keys = {nn(k): v["odt_air"] for k, v in ODT_DATA.items()}
all_odt_names = sorted(odt_keys.keys())
missing = []

for m in sorted(set(materials)):
    key = nn(m)
    if key in odt_keys:
        continue
    # try partial match
    for ok in all_odt_names:
        if ok in key or key in ok:
            break
    else:
        missing.append(m)

if missing:
    print(f"{len(missing)} materials missing ODT entries:\n")
    for m in missing:
        print(f'  "{m}": {{"odt_air": None, "odt_eth": None, "char": ""}},')
else:
    print("All materials covered.")
