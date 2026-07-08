"""Check registry key names for problematic materials."""
import sys
from engine.data_spine.loader import load_registry
r = load_registry()
mats = [
    "Amyl Cinnamic Aldehyde (ACA)", "Amyl Cinnamic Aldehyde", "ACA",
    "Triplal", "triplal",
    "p-Cresyl Methyl Ether (PCME)", "p-Cresyl Methyl Ether", "PCME", "p-cresyl methyl ether",
    "Phenethyl Alcohol (PEA)", "Phenethyl Alcohol", "phenethyl alcohol",
    "Labdanum Absolute", "labdanum absolute",
]
for m in mats:
    found = m in r
    print(f"'{m}': {'FOUND' if found else 'NOT FOUND'}")

# Show what keys exist containing these words
print("\n--- Keys containing 'amyl cinnamic' ---")
for k in r:
    if "amyl cinnamic" in k.casefold():
        print(f"  '{k}'")
print("\n--- Keys containing 'triplal' ---")
for k in r:
    if "triplal" in k.casefold():
        print(f"  '{k}'")
print("\n--- Keys containing 'cresyl' ---")
for k in r:
    if "cresyl" in k.casefold():
        print(f"  '{k}'")
