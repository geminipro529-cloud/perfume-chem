"""Cross-validate external AHS report ODT values against pipeline ODT_DATA."""
import sys
sys.path.insert(0, r"D:\chatbots\perfume-chem")
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

report_odts = {
    "Limonene": 10,
    "Linalool": 0.8,
    "Geraniol": 0.04,
    "Citronellol": 0.3,
    "Coumarin": 0.7,
    "Alpha-Isomethyl Ionone": 0.8,
    "Vanillin": 0.02,
    "Benzyl Salicylate": 10,
    "Citral": 20,
    "Linalyl Acetate": 2,
    "Eugenol": None,
    "Santalol": 0.01,
    "TMAHON": 0.1,
}

HDR = f"{'Material':35s} {'Report ODT(ppb)':>18s} {'Pipeline ODT(ppb)':>20s} {'Ratio':>8s} {'Verification'}"
print(HDR)
print("-" * 95)

mismatches = []
not_found = []
for name, report_odt in sorted(report_odts.items()):
    norm = normalize_name(name)
    pip_odt = None
    pip_src = "?"
    for odt_name, data in ODT_DATA.items():
        if normalize_name(odt_name) == norm:
            pip_odt = data.get("odt_air")
            pip_src = str(data.get("verification", "?"))
            break

    if pip_odt is not None and report_odt is not None:
        ratio = report_odt / pip_odt if pip_odt else float("inf")
        is_mismatch = ratio < 1/3 or ratio > 3
        flag = " <<<" if is_mismatch else ""
        if is_mismatch:
            mismatches.append((name, report_odt, pip_odt, ratio))
        print(f"{name:35s} {str(report_odt):>18s} {str(pip_odt):>20s} {ratio:>7.1f}x{flag:>4s} {pip_src}")
    elif pip_odt is not None:
        print(f"{name:35s} {'?':>18s} {str(pip_odt):>20s} {'?':>8s} {pip_src}")
    else:
        not_found.append(name)
        print(f"{name:35s} {str(report_odt or '-'):>18s} {'NOT IN ODT_DATA':>20s} {'?':>8s} ?")

print("\n\nODT MISMATCHES (>3x difference):")
print("=" * 60)
for name, rep, pip, ratio in mismatches:
    direction = "LOWER (report underestimates perceptibility)" if rep < pip else "HIGHER (report overestimates perceptibility)"
    print(f"  {name:30s} report={rep} ppb  pipeline={pip} ppb  ratio={ratio:.1f}x — report is {direction}")

print("\n\nKEY AHS MATERIALS MISSING FROM INCI-BASED REPORT:")
print("=" * 60)
print("The report only sees EU-declared allergens. These AHS-essential")
print("materials are hidden under PARFUM in the INCI:")
key_ahs = [
    ("Dihydromyrcenol", "The SPORT signature — OAV ~10,000"),
    ("Hedione HC", "Jasmonate radiance — OAV ~620"),
    ("Ambrofix", "Ambergris backbone — OAV ~21"),
    ("Habanolide", "White musk — THE Chanel sport musk"),
    ("Galaxolide", "Soapy-clean musk"),
    ("Iso E Super", "Spatial volume — OAV ~4,500"),
    ("Helional", "Marine-ozone — the sport aquatic dimension"),
    ("Floralozone", "Ozonic transparency"),
    ("Cashmeran", "Textile-cashmere warmth"),
    ("Aldehyde C10/C11/C12 MNA", "Chanel aldehydic DNA"),
    ("Orivone/Ultralia/Irotyl", "Iris texture complex"),
]
for mat, reason in key_ahs:
    norm = normalize_name(mat)
    odt_val = None
    for odt_name, data in ODT_DATA.items():
        if normalize_name(odt_name) == norm:
            odt_val = data.get("odt_air")
            break
    odt_str = f"ODT={odt_val} ppb" if odt_val else ""
    print(f"  - {mat:30s} {odt_str:15s} {reason}")
