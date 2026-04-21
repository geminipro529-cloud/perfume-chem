import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import os
import re
from dataclasses import dataclass

import pandas as pd
import plotly.express as px

try:
    from engine.inventory_parser import parse_inventory
except ImportError:

    @dataclass(frozen=True)
    class InventoryMaterial:
        name: str
        dilution: float
        category: str
        raw_name: str
        status: str

    _HEADING_RE = re.compile(r"^##\s+(.+)")
    _BULLET_RE = re.compile(r"^[-*]\s+(.*)")
    _PERCENT_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*%")
    _STATUS_TAGS = {"OUT OF STOCK", "RAN OUT", "DON'T HAVE", "DONT HAVE"}

    def parse_inventory(
        path=None,
        *,
        unique=True,
        include_solvents=True,
        include_unavailable=True,
    ):
        path = path or Path("inventory.txt")
        if not path.exists():
            return []

        materials = []
        category = ""
        solvent_tokens = {"solvent", "carrier", "diluent", "base"}
        solvent_names = {"ethanol", "dpg", "ipm", "isopropyl myristate"}

        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            hm = _HEADING_RE.match(line)
            if hm:
                category = hm.group(1).strip().lower()
                continue
            bm = _BULLET_RE.match(line)
            if not bm:
                continue

            raw_name = bm.group(1).strip()
            # Status
            upper = raw_name.upper()
            if "OUT OF STOCK" in upper:
                status = "out_of_stock"
            elif "RAN OUT" in upper:
                status = "ran_out"
            elif "DON'T HAVE" in upper or "DONT HAVE" in upper:
                status = "not_owned"
            else:
                status = "owned"
            # Clean name: strip status tags, then trailing parenthetical
            clean = re.sub(r"\s*\[[^\]]+\]\s*$", "", raw_name).strip()
            name = re.sub(r"\s*\([^)]*\)\s*$", "", clean).strip()
            # Dilution
            pm = _PERCENT_RE.search(raw_name)
            dilution = float(pm.group(1)) / 100.0 if pm else 1.0

            rec = InventoryMaterial(
                name=name, dilution=dilution,
                category=category, raw_name=raw_name, status=status,
            )
            if not include_unavailable and status != "owned":
                continue
            if not include_solvents:
                if any(t in category for t in solvent_tokens):
                    continue
                if name.lower() in solvent_names:
                    continue
            materials.append(rec)

        if not unique:
            return materials
        deduped = {}
        for rec in materials:
            key = rec.name.lower()
            if key not in deduped or rec.dilution > deduped[key].dilution:
                deduped[key] = rec
        return list(deduped.values())

WORKBOOK = "opus_v_master_system_complete.xlsx"
INVENTORY_FILE = Path("inventory.txt")

INVENTORY_ALIASES = {
    "d-limonene": "limonene",
    "phenylethyl alcohol": "phenethyl alcohol",
    "myristic acid powder": "myristic acid",
    "ambrox super": "ambroxan",
    "cyclimal aldehyde": "cyclamal",
}


def load_ingredient_master(path):
    df = pd.read_excel(path, sheet_name="Ingredient Master & Pyramid", header=1)
    df = df[df["Ingredient"].notna()].copy()
    df["LogP"] = pd.to_numeric(df["LogP"], errors="coerce")
    df["VP@25°C"] = pd.to_numeric(df["VP@25°C"], errors="coerce")
    if "Skin Depot?" not in df.columns:
        # Simple fallback classification because the workbook exposes LogP but not
        # an explicit depot flag.
        df["Skin Depot?"] = df["LogP"].apply(
            lambda value: "Likely" if pd.notna(value) and value >= 3 else "Lower"
        )
    return df


def load_opus_formula(path):
    df = pd.read_excel(path, sheet_name="Opus V Master Formula", header=2)
    df = df[df["Ingredient"].notna()].copy()
    df["Parts"] = pd.to_numeric(df["Parts"], errors="coerce")
    df = df[df["Parts"].notna()].copy()
    df = df[~df["Ingredient"].astype(str).str.startswith("SUBTOTAL:")].copy()
    df = df[df["Ingredient"] != "GRAND TOTAL"].copy()
    return df


def load_accords(path):
    df = pd.read_excel(path, sheet_name="All Accord Formulas", header=1)
    df = df[df["Ingredient"].notna()].copy()
    df["Parts"] = pd.to_numeric(df["Parts"], errors="coerce")
    df = df[df["Parts"].notna()].copy()
    return df


def show_figure(fig, html_path):
    fig.write_html(html_path)
    print(f"  Saved chart: {html_path}")
    if os.environ.get("OPEN_PLOTS") == "1":
        try:
            fig.show()
        except Exception as exc:
            print(f"  Chart display skipped: {exc}")


def normalize_inventory_name(name):
    value = str(name or "").strip().lower()
    value = re.sub(r"#.*$", "", value).strip()
    value = re.sub(r"\s*\([^)]*\)\s*$", "", value)
    value = re.sub(r"\s+\d+(?:\.\d+)?\s*%\s*$", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return INVENTORY_ALIASES.get(value, value)


def load_inventory_index(path=INVENTORY_FILE):
    records = parse_inventory(
        path,
        unique=True,
        include_solvents=True,
        include_unavailable=False,
    )
    index = {}
    for record in records:
        key = normalize_inventory_name(record.name)
        index.setdefault(key, []).append(record.name)
    return records, index


def match_inventory_material(name, inventory_index):
    matches = []
    choices = [name]
    if "/" in str(name):
        choices = [part.strip() for part in str(name).split("/") if part.strip()]

    for choice in choices:
        key = normalize_inventory_name(choice)
        matches.extend(inventory_index.get(key, []))

    return sorted(dict.fromkeys(matches))


def inventory_report(perfume, label, inventory_index):
    matched = {}
    missing = []

    for ingredient in perfume["Ingredient"]:
        hits = match_inventory_material(ingredient, inventory_index)
        if hits:
            matched[ingredient] = hits
        else:
            missing.append(ingredient)

    print(f"\nInventory coverage for {label}: {len(matched)}/{len(perfume)}")

    remapped = {
        ingredient: hits
        for ingredient, hits in matched.items()
        if ingredient not in hits or len(hits) != 1
    }
    if remapped:
        print("Matched via inventory labels:")
        for ingredient, hits in sorted(remapped.items()):
            print(f"  - {ingredient} -> {', '.join(hits)}")

    print(f"Missing from stock: {missing}")
    return {"matched": matched, "missing": missing}


# 1. LOAD YOUR PERFUME SYSTEM
df_ing = load_ingredient_master(WORKBOOK)
df_opusv = load_opus_formula(WORKBOOK)
df_accords = load_accords(WORKBOOK)
inventory_records, inventory_index = load_inventory_index()
BASE_TOTAL = df_opusv["Parts"].sum()

print("Loaded:")
print(f"  - {len(df_ing)} ingredients")
print(f"  - Opus V: {BASE_TOTAL:.0f} parts total")
print(f"  - {df_accords['Accord Family'].nunique()} accord families")
print(f"  - Inventory: {len(inventory_records)} materials")

# 2. MAKE OPUS V EDP (Scale to 100ml)
def make_edp(parts=98, target_ml=100, conc=0.20):
    """Scale Opus V to any size EDP"""
    accord_g = target_ml * conc
    ethanol_g = target_ml * (1-conc)
    print(f"\nTarget: {target_ml}ml EDP ({conc*100}%):")
    print(f"  Accord: {accord_g:.1f}g (scale Sheet2 by {accord_g/parts:.2f})")
    print(f"  EtOH:   {ethanol_g:.1f}g")
    return accord_g / parts

scale = make_edp(BASE_TOTAL, 100, 0.20)  # 20% EDP

# 3. VISUALIZE PYRAMID (Your evaporation timeline)
pyramid = df_ing[df_ing['Layer'].notna()][['Ingredient', 'VP@25°C', 'Layer', 'Perception Window']]
fig1 = px.treemap(pyramid, path=['Layer', 'Ingredient'], values='VP@25°C',
                  color='VP@25°C', hover_data=['Perception Window'],
                  title="Opus V Pyramid: Top evaporates first → Base lasts 168h")
show_figure(fig1, "opus_v_pyramid.html")

# 4. LONGEVITY ANALYSIS (Which molecules last longest?)
longevity = df_ing.sort_values('LogP', ascending=False)[['Ingredient', 'LogP', 'Skin Depot?', 'Layer']]
print("\nTop 10 longest-lasting:")
print(longevity.head(10).to_string(index=False))

# 5. BUILD CUSTOM PERFUME (Example: Opus V + Powder Luxury)
def build_perfume(base_parts=80, accord_name="Powder Iris Luxury Accord", accord_parts=20):
    """Mix base + accord → finished perfume"""
    base_df = df_opusv[["Ingredient", "Parts"]].copy()
    base_df['Parts'] *= base_parts / BASE_TOTAL

    if accord_name and accord_parts:
        accord_mask = df_accords['Accord Family'].astype(str).str.contains(
            accord_name, case=False, na=False
        )
        accord_df = df_accords.loc[accord_mask, ["Ingredient", "Parts"]].copy()
        if accord_df.empty:
            raise ValueError(f"No accord family matched '{accord_name}'")
        accord_df = accord_df.groupby('Ingredient', as_index=False)['Parts'].sum()
        accord_total = accord_df['Parts'].sum()
        accord_df['Parts'] *= accord_parts / accord_total
        perfume = pd.concat([base_df, accord_df], ignore_index=True)
    else:
        perfume = base_df.copy()

    perfume = perfume.groupby('Ingredient')['Parts'].sum().reset_index()
    perfume['EDP%'] = perfume['Parts'] * 0.20  # 20% dilution
    perfume['Final EDP g'] = perfume['EDP%'] * 100 / 100  # for 100ml
    
    label = accord_name if accord_name else "Pure Opus V"
    print(f"\nBlend: {base_parts}% Opus V + {accord_parts}% {label}")
    print(perfume.sort_values('Parts', ascending=False).head(15).to_string(index=False))
    
    # Pyramid chart
    fig2 = px.pie(
        perfume,
        values='Parts',
        names='Ingredient',
        title=f"{base_parts/100:.0%} Opus V + {accord_parts}% {label}",
    )
    html_name = (
        f"opus_v_{label.lower().replace(' ', '_').replace('%', 'pct').replace('/', '_')}.html"
    )
    show_figure(fig2, html_name)
    
    return perfume

# BUILD 3 PERFUMES
perf1 = build_perfume(100, "", 0)  # Pure Opus V
perf2 = build_perfume(80, "Powder Iris Luxury Accord", 20)
perf3 = build_perfume(70, "Iris Longevity and Sillage Max Accord", 30)

# 6. EXPORT TO CSV (for suppliers/inventory)
perf1.to_csv("opus_v_pure_edp.csv", index=False)
perf2.to_csv("opus_v_powder_edp.csv", index=False)
perf3.to_csv("opus_v_longevity_edp.csv", index=False)
print("\nExported 3 finished perfumes to CSV")
print("  - opus_v_pure_edp.csv")
print("  - opus_v_powder_edp.csv")
print("  - opus_v_longevity_edp.csv")

# 7. INVENTORY CHECK (cross-reference your stock)
inventory_report(perf1, "Pure Opus V", inventory_index)
inventory_report(perf2, "Powder Iris Luxury Accord blend", inventory_index)
inventory_report(perf3, "Iris Longevity and Sillage Max blend", inventory_index)