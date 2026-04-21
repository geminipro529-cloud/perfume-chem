"""Validation engine: Chemistry rules cannot break perfumery, perfumery cannot break chemistry."""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Tuple
import re

@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]

@dataclass
class DosageValidation:
    safe: bool
    odor_value: Optional[float]
    base_compatible: bool
    errors: list[str]
    warnings: list[str]
    recommendation: str

# Global caches
COMPOUNDS = None
OWNED_MATERIALS: set | None = None

def load_owned_materials() -> set:
    """Load list of owned materials from chemical_inventory.md"""
    owned = set()
    inventory_path = Path(__file__).parent.parent / "knowledge" / "chemical_inventory.md"
    
    if not inventory_path.exists():
        return owned
    
    try:
        with open(inventory_path, "r", encoding="utf-8") as f:
            for line in f:
                # Parse table rows: | **Chemical Name** | CAS | ...
                if line.startswith("|") and "**" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 2:
                        # Extract chemical name from **Name** format
                        name = parts[1].strip().replace("**", "").lower()
                        if name and name not in ["chemical name", ""]:
                            owned.add(name)
                            # Also add common variants
                            if "(" in name:
                                base_name = name.split("(")[0].strip()
                                owned.add(base_name)
    except Exception as e:
        print(f"Warning: Could not load inventory: {e}")
    
    return owned

def get_owned_materials() -> set:
    """Get cached set of owned materials"""
    global OWNED_MATERIALS
    if OWNED_MATERIALS is None:
        OWNED_MATERIALS = load_owned_materials()
    return OWNED_MATERIALS

def is_owned(material_name: str) -> bool:
    """Check if material is in inventory (fuzzy match)"""
    owned = get_owned_materials()
    material_lower = material_name.lower().strip()
    
    # Exact match
    if material_lower in owned:
        return True
    
    # Fuzzy match
    for owned_material in owned:
        if material_lower in owned_material or owned_material in material_lower:
            return True
    
    return False

def get_chemical_classes(material: str) -> set[str]:
    """Return all chemical classes the material belongs to"""
    material_lower = material.lower().strip()
    classes = set()
    
    for class_name, members in CHEMICAL_CLASSES.items():
        for member in members:
            if member in material_lower or material_lower in member:
                classes.add(class_name)
                break
    
    return classes

def get_intensity_tier(odt: float) -> str:
    """Determine intensity tier based on ODT"""
    if odt < 0.00001:
        return "ultra_potent"
    elif odt < 0.0001:
        return "extremely_potent"
    elif odt < 0.01:
        return "high_impact"
    elif odt < 0.1:
        return "moderate"
    else:
        return "low"

def check_base_compatibility(material: str, base_type: str) -> tuple[str, list[str]]:
    """
    Check if material is compatible with base type.
    Returns: (compatibility_level, warnings)
    compatibility_level: FORBIDDEN, POOR, RISKY, OK, GOOD, EXCELLENT, UNKNOWN
    """
    warnings = []
    material_classes = get_chemical_classes(material)
    
    if not material_classes:
        return "UNKNOWN", []
    
    # Check incompatibility matrix for each class
    worst_compatibility = "EXCELLENT"  # Start optimistic
    compatibility_order = ["FORBIDDEN", "POOR", "RISKY", "OK", "GOOD", "EXCELLENT", "UNKNOWN"]
    
    for mat_class in material_classes:
        key = (mat_class, base_type)
        if key in INCOMPATIBILITY_MATRIX:
            compat = INCOMPATIBILITY_MATRIX[key]
            if compatibility_order.index(compat) < compatibility_order.index(worst_compatibility):
                worst_compatibility = compat
    
    # Generate warnings based on compatibility
    if worst_compatibility == "FORBIDDEN":
        warnings.append(
            f"❌ INCOMPATIBILITY: {material} ({', '.join(material_classes)}) is FORBIDDEN in {base_type} bases"
        )
        if "animalic" in material_classes:
            warnings.append(
                "   Animalics create fecal/urine smell in clean bases. Use clean musks (ambroxan, exaltolide) instead."
            )
    elif worst_compatibility == "POOR":
        warnings.append(
            f"⚠️ POOR MATCH: {material} ({', '.join(material_classes)}) performs poorly in {base_type} bases"
        )
        if "aldehyde" in material_classes and base_type in ["heavy_oriental", "resinous"]:
            warnings.append(
                "   Aldehydes will be masked/buried under heavy resins. Use <0.5% or reconsider."
            )
        if "fresh_green" in material_classes and base_type == "heavy_oriental":
            warnings.append(
                "   Fresh greens clash with sweet orientals ('salad in bakery'). Use <0.3% or omit."
            )
    elif worst_compatibility == "RISKY":
        warnings.append(
            f"⚠️ RISKY: {material} ({', '.join(material_classes)}) may not work well in {base_type} bases - test small batch"
        )
    
    return worst_compatibility, warnings

def check_degradation_risk(material: str, formula: Dict[str, float]) -> list[str]:
    """Check for oxidation, hydrolysis, photodegradation risks"""
    warnings = []
    material_lower = material.lower().strip()
    
    # Check if BHT is in formula
    has_bht = any("bht" in ing.lower() for ing in formula.keys())
    
    # Oxidation risk
    for oxidation_material in DEGRADATION_RISKS["oxidation"]:
        if oxidation_material in material_lower or material_lower in oxidation_material:
            if not has_bht:
                warnings.append(
                    f"⚠️ OXIDATION RISK: {material} prone to oxidation. ADD BHT 0.05-0.1% to formula."
                )
            warnings.append(
                f"   Store in amber glass, use within 6 months. {material} oxidizes → off-notes (turpentine, rancid)."
            )
            break
    
    # Hydrolysis risk
    for hydrolysis_material in DEGRADATION_RISKS["hydrolysis"]:
        if hydrolysis_material in material_lower:
            warnings.append(
                f"⚠️ HYDROLYSIS RISK: {material} (ester/lactone) can break down with moisture. Keep formula anhydrous (<1% water), pH 4-7."
            )
            break
    
    # Photodegradation risk
    for photo_material in DEGRADATION_RISKS["photo"]:
        if photo_material in material_lower:
            warnings.append(
                f"⚠️ PHOTO RISK: {material} degrades with UV light. Use amber bottles, store away from sunlight."
            )
            if "bergamot" in material_lower:
                warnings.append(
                    "   PHOTOTOXICITY: Bergamot (bergapten) causes skin burns under sunlight. Use Bergamot FCF or limit to <0.4% bergapten."
                )
            break
    
    return warnings
    
def load_compounds() -> dict:
    data_path = Path(__file__).parent.parent / "data" / "compounds.json"
    with open(data_path) as f:
        return {c["name"].lower(): c for c in json.load(f)["compounds"]}

# ODT Database (parts per million in air, converted to % in solution)
# From knowledge/science/odor_threshold_database.md
ODT_DATABASE = {
    # Ultra-potent (will dominate even at trace levels)
    "β-damascenone": 0.000009,   # 0.009 ppb air (Rychlik 1998)
    "damascenone": 0.000009,     # 0.009 ppb air (Rychlik 1998)
    "β-damascone": 0.00008,      # 0.08 ppb air (Leffingwell)
    "α-damascone": 0.00003,      # ~0.03 ppb air (estimated, structural analogy)
    "2-methyl-3-furanthiol": 0.000002,
    "grapefruit mercaptan": 0.000004,
    
    # Extremely potent (animalics - PRIMARY CONCERN)
    "indole": 0.000014,
    "skatole": 0.00002,
    "methyl anthranilate": 0.00004,
    "gamma-decalactone": 0.0001,
    "γ-decalactone": 0.0001,
    "ionone": 0.0007,
    "alpha ionone": 0.0007,
    "alpha-ionone": 0.0007,
    "β-ionone": 0.0007,
    "beta-ionone": 0.0007,
    
    # High impact
    "linalool": 0.0015,
    "eugenol": 0.003,
    "citronellol": 0.005,
    "benzyl acetate": 0.008,
    "phenylethyl alcohol": 0.01,
    "geraniol": 0.004,
    
    # Moderate impact
    "limonene": 0.02,
    "linalyl acetate": 0.025,
    "coumarin": 0.03,
    "hedione": 0.05,
    "benzyl salicylate": 0.07,
    
    # Low impact
    "ethyl vanillin": 0.12,
    "vanillin": 0.2,
    "iso e super": 0.5,
    "galaxolide": 0.8,
    "dihydromyrcenol": 1.0,
    
    # Common aromachemicals
    "ambroxan": 0.3,
    "cetalox": 0.4,
    "exaltolide": 0.15,
    "cashmeran": 0.1,
    "safranal": 0.005,
    "saffron": 0.01,
    "cinnamaldehyde": 0.02,
    "isoeugenol": 0.004,
    "benzoin": 0.5,
    "labdanum": 0.2,
}

# Chemical Class Membership (comprehensive taxonomy)
CHEMICAL_CLASSES = {
    "animalic": {
        "skatole", "indole", "oud", "oud fleuressence", "arabian oud fleuresscence",
        "civet", "castoreum", "hyraceum", "costus", "cumin", "birch tar",
        "skatoe", "exaltolide", "ambrettolide"
    },
    "aldehyde": {
        "c-12 mna", "c-11 undecanol", "c-14 gamma undecalactone", "aldehyde c-14",
        "aldehyde c-11", "benzaldehyde", "citral", "helional", "cyclamen aldehyde"
    },
    "phenol": {
        "eugenol", "isoeugenol", "thymol", "carvacrol", "guaiacol",
        "phenethyl alcohol", "phenylethyl alcohol"
    },
    "terpene": {
        "limonene", "d-limonene", "pinene", "myrcene", "ocimene",
        "terpinolene", "linalool", "linalyl acetate", "bergamot", "bergamot eo"
    },
    "musk": {
        "galaxolide", "exaltolide", "habanolide", "cashmeran",
        "ambrettolide", "ethylene brassylate", "kephalis", "muskofix"
    },
    "ionone": {
        "alpha-ionone", "alpha ionone", "beta-ionone", "ionone beta",
        "alpha irone", "gamma irone", "methyl-ionone", "alpha isomethyl ionone",
        "irotyl", "dihydrobeta ionone"
    },
    "lactone": {
        "gamma-decalactone", "delta-decalactone", "delta decalactone",
        "massoia lactone", "whiskey lactone"
    },
    "resin": {
        "labdanum", "labdamum absolute", "benzoin", "benzoin siam", "benzoin siam resinoid",
        "myrrh", "opoponax", "styrax", "peru balsam", "tolu balsam"
    },
    "fresh_green": {
        "cis-3-hexenol", "galbanum", "undecavertol", "violet leaf"
    },
    "marine": {
        "calone", "helional", "sea breeze"
    },
}

# Animalic materials that require base compatibility checking
ANIMALIC_MATERIALS = CHEMICAL_CLASSES["animalic"]

# Heavy resinous materials
HEAVY_RESINS = CHEMICAL_CLASSES["resin"]

# Base Type Incompatibility Matrix
# Maps (chemical_class, base_type) → compatibility level
INCOMPATIBILITY_MATRIX = {
    # Animalics: FORBIDDEN in clean bases, OK in heavy/leather
    ("animalic", "clean"): "FORBIDDEN",
    ("animalic", "aquatic"): "FORBIDDEN",
    ("animalic", "aldehydic"): "FORBIDDEN",
    ("animalic", "heavy_oriental"): "OK",
    ("animalic", "leather"): "GOOD",
    ("animalic", "chypre"): "OK",
    ("animalic", "tobacco"): "GOOD",
    ("animalic", "gourmand"): "RISKY",
    
    # Aldehydes: EXCELLENT in clean, POOR in heavy/resinous
    ("aldehyde", "clean"): "EXCELLENT",
    ("aldehyde", "aldehydic"): "EXCELLENT",
    ("aldehyde", "floral"): "GOOD",
    ("aldehyde", "heavy_oriental"): "POOR",
    ("aldehyde", "resinous"): "POOR",
    
    # Fresh greens: POOR in heavy oriental
    ("fresh_green", "heavy_oriental"): "POOR",
    ("fresh_green", "chypre"): "EXCELLENT",
    ("fresh_green", "fougere"): "EXCELLENT",
    
    # Marine: POOR with resins
    ("marine", "heavy_oriental"): "POOR",
    ("marine", "resinous"): "POOR",
    ("marine", "aquatic"): "EXCELLENT",
}

# OV Thresholds by Intensity Tier
OV_THRESHOLDS = {
    "ultra_potent": {"safe": 200, "warn": 300, "error": 500},
    "extremely_potent_animalic": {"safe": 300, "warn": 500, "error": 1000},
    "extremely_potent_other": {"safe": 1000, "warn": 2000, "error": 3000},
    "high_impact": {"safe": 2000, "warn": 3000, "error": 5000},
    "moderate": {"safe": 1000, "warn": 2000, "error": 3000},
    "low": {"safe": 2000, "warn": 5000, "error": 10000},
}

# Degradation Risk Materials
DEGRADATION_RISKS = {
    "oxidation": CHEMICAL_CLASSES["terpene"] | CHEMICAL_CLASSES["aldehyde"],
    "hydrolysis": {"linalyl acetate", "benzyl acetate", "terpinyl acetate"} | CHEMICAL_CLASSES["lactone"],
    "photo": {"bergamot", "bergamot eo", "citrus oils", "vanillin"},
}

# Expensive/rare materials that should be conserved
# Substitutes listed with OWNED materials prioritized first
EXPENSIVE_MATERIALS = {
    "benzoin siam resinoid": {
        "cost_per_ml": 0.70, 
        "substitutes_owned": ["vanillin", "ethyl maltol", "tonka bean fo"],
        "substitutes_new": ["vanillin 10%"],
        "substitute_ratio": 0.5
    },
    "benzoin": {
        "cost_per_ml": 0.70, 
        "substitutes_owned": ["vanillin", "ethyl maltol", "tonka bean fo"],
        "substitutes_new": ["vanillin 10%"],
        "substitute_ratio": 0.5
    },
    "iris": {
        "cost_per_ml": 5.0, 
        "substitutes_owned": ["alpha-ionone", "alpha irone", "irotyl", "orris ftec", "alpha isomethyl ionone"],
        "substitutes_new": [],
        "substitute_ratio": 0.3
    },
    "orris": {
        "cost_per_ml": 5.0, 
        "substitutes_owned": ["alpha-ionone", "alpha irone", "irotyl", "orris ftec", "alpha isomethyl ionone"],
        "substitutes_new": [],
        "substitute_ratio": 0.3
    },
    "rose absolute": {
        "cost_per_ml": 10.0, 
        "substitutes_owned": ["phenethyl alcohol", "geranium fo", "rose oxide 10%"],
        "substitutes_new": ["geraniol"],
        "substitute_ratio": 0.4
    },
    "jasmine absolute": {
        "cost_per_ml": 8.0, 
        "substitutes_owned": ["hedione", "indole", "jasmine fo"],
        "substitutes_new": [],
        "substitute_ratio": 0.5
    },
    "oud": {
        "cost_per_ml": 15.0, 
        "substitutes_owned": ["arabian oud fleuresscence"],
        "substitutes_new": ["avoid in clean bases"],
        "substitute_ratio": 0
    },
    "sandalwood oil": {
        "cost_per_ml": 3.0, 
        "substitutes_owned": ["ebanol", "bacdanol", "sandalwood fo"],
        "substitutes_new": [],
        "substitute_ratio": 0.6
    },
    "oakmoss absolute": {
        "cost_per_ml": 2.0, 
        "substitutes_owned": ["evernyl"],
        "substitutes_new": [],
        "substitute_ratio": 0.5
    },
    "saffron": {
        "cost_per_ml": 4.0, 
        "substitutes_owned": ["saffranal", "saffron ftec"],
        "substitutes_new": ["safranal 10%"],
        "substitute_ratio": 0.3
    },
    "hedione": {
        "cost_per_ml": 0.80, 
        "substitutes_owned": [],
        "substitutes_new": ["only if formula needs radiance"],
        "substitute_ratio": 0
    },
    "benzyl benzoate": {
        "cost_per_ml": 0.20, 
        "substitutes_owned": [],
        "substitutes_new": ["only if cloudiness/precipitation"],
        "substitute_ratio": 0
    },
}

# Materials often overused as "generic boosters" (check if needed first)
OVERUSED_BOOSTERS = {
    "hedione": {"max_recommended_pct": 2.0, "reason": "radiance booster—only needed if base is flat/linear"},
    "benzyl benzoate": {"max_recommended_pct": 5.0, "reason": "co-solvent—only needed for solubility issues"},
    "iso e super": {"max_recommended_pct": 15.0, "reason": "woody booster—can become metallic >15%"},
}

# Typical commercial usage ranges (from perfume formula analysis)
# Format: {material: {"typical_min": %, "typical_max": %, "extreme_max": %, "examples": "perfume names"}}
COMMERCIAL_USAGE_RANGES = {
    # Top notes
    "linalool": {"typical_min": 1, "typical_max": 8, "extreme_max": 15, "examples": "Dior Homme (3%), Lavender colognes (8%)"},
    "limonene": {"typical_min": 5, "typical_max": 20, "extreme_max": 40, "examples": "Citrus colognes (20%), Fresh scents (10%)"},
    "bergamot": {"typical_min": 3, "typical_max": 15, "extreme_max": 25, "examples": "Earl Grey style (15%), Classic colognes (10%)"},
    
    # Heart notes
    "hedione": {"typical_min": 0.5, "typical_max": 2, "extreme_max": 5, "examples": "Dior Eau Sauvage (2%), Modern florals (1%)"},
    "geraniol": {"typical_min": 1, "typical_max": 5, "extreme_max": 10, "examples": "Rose fragrances (5%), Geranium accords (3%)"},
    "jasmine": {"typical_min": 0.5, "typical_max": 3, "extreme_max": 8, "examples": "Floral soliflores (3%), Jasmine tea (2%)"},
    "rose": {"typical_min": 0.5, "typical_max": 4, "extreme_max": 10, "examples": "Rose soliflores (5%), Rose accords (2%)"},
    "iris": {"typical_min": 0.5, "typical_max": 8, "extreme_max": 15, "examples": "Dior Homme Parfum (8%), Prada Infusion d'Iris (5%)"},
    
    # Base notes
    "vanillin": {"typical_min": 1, "typical_max": 5, "extreme_max": 10, "examples": "Gourmands (5%), Oriental bases (3%)"},
    "coumarin": {"typical_min": 0.5, "typical_max": 3, "extreme_max": 5, "examples": "Fougères (3%), Tonka accords (2%)"},
    "benzoin": {"typical_min": 1, "typical_max": 5, "extreme_max": 8, "examples": "Oriental bases (5%), Balsamic accords (3%)"},
    "labdanum": {"typical_min": 1, "typical_max": 5, "extreme_max": 10, "examples": "Amber accords (5%), Chypres (3%)"},
    "patchouli": {"typical_min": 1, "typical_max": 8, "extreme_max": 15, "examples": "Hippie-chic (10%), Modern masculine (3%)"},
    "sandalwood": {"typical_min": 2, "typical_max": 10, "extreme_max": 20, "examples": "Sandalwood soliflores (15%), Woody bases (5%)"},
    "cedarwood": {"typical_min": 2, "typical_max": 8, "extreme_max": 15, "examples": "Woody fragrances (8%), Masculine bases (5%)"},
    "vetiver": {"typical_min": 1, "typical_max": 5, "extreme_max": 10, "examples": "Vetiver soliflores (8%), Earthy accords (3%)"},
    "oakmoss": {"typical_min": 0.5, "typical_max": 3, "extreme_max": 5, "examples": "Classic chypres (3%), Mossy bases (2%)"},
    
    # Musks
    "galaxolide": {"typical_min": 2, "typical_max": 10, "extreme_max": 20, "examples": "Clean musks (15%), Laundry scents (10%)"},
    "iso e super": {"typical_min": 5, "typical_max": 15, "extreme_max": 30, "examples": "Escentric Molecules 01 (65% - outlier!), Woody bases (10%)"},
    "ambroxan": {"typical_min": 1, "typical_max": 8, "extreme_max": 15, "examples": "Sauvage (8%), Ambrée fragrances (5%)"},
    "cashmeran": {"typical_min": 0.5, "typical_max": 3, "extreme_max": 8, "examples": "Cashmere woods (5%), Modern bases (2%)"},
    
    # Powerful materials (very low usage)
    "skatole": {"typical_min": 0.001, "typical_max": 0.05, "extreme_max": 0.1, "examples": "Leather fragrances (0.03%), Animalic chypres (0.02%)"},
    "indole": {"typical_min": 0.005, "typical_max": 0.1, "extreme_max": 0.3, "examples": "White florals (0.1%), Jasmine accords (0.05%)"},
    "cumin": {"typical_min": 0.05, "typical_max": 0.3, "extreme_max": 0.5, "examples": "Cumin Note (0.5%), Orientals (0.2%)"},
    "civet": {"typical_min": 0.01, "typical_max": 0.1, "extreme_max": 0.3, "examples": "Vintage chypres (0.2%), Animalic bases (0.05%)"},
}

def check_commercial_usage(material: str, final_conc_pct: float) -> Tuple[bool, list[str]]:
    """
    Check if dose is within normal commercial perfume ranges.
    
    Returns: (is_abnormal, warnings)
    """
    warnings = []
    abnormal = False
    
    material_lower = material.lower()
    
    # Check against commercial ranges
    for ref_material, ranges in COMMERCIAL_USAGE_RANGES.items():
        if ref_material in material_lower or material_lower in ref_material:
            typical_max = ranges["typical_max"]
            extreme_max = ranges["extreme_max"]
            examples = ranges["examples"]
            
            if final_conc_pct > extreme_max:
                warnings.append(
                    f"⚠️ ABNORMAL DOSE: {final_conc_pct:.2f}% exceeds even extreme commercial usage ({extreme_max}%)"
                )
                warnings.append(f"   Commercial perfumes use: {examples}")
                warnings.append(f"   This is {final_conc_pct/extreme_max:.1f}× higher than industry extreme")
                abnormal = True
            elif final_conc_pct > typical_max:
                warnings.append(
                    f"⚠️ HIGH DOSE: {final_conc_pct:.2f}% exceeds typical commercial range (max {typical_max}%)"
                )
                warnings.append(f"   Commercial perfumes typically use: {examples}")
                warnings.append(f"   Consider reducing to {typical_max:.1f}% unless intentionally extreme")
            
            break
    
    return abnormal, warnings

def check_material_conservation(
    material: str,
    dose_ml: float,
    base_ml: float,
    batch_is_large: bool = False  # >50 mL = large
) -> Tuple[bool, list[str], str]:
    """
    Check if expensive material is being wasted.
    
    Returns: (is_wasteful, warnings, alternative_recommendation)
    """
    warnings = []
    wasteful = False
    alternative = ""
    
    material_lower = material.lower()
    final_conc_pct = (dose_ml / base_ml) * 100 if base_ml > 0 else 0
    
    # Check for overused "generic boosters"
    for booster_name, data in OVERUSED_BOOSTERS.items():
        if booster_name in material_lower:
            max_pct = data["max_recommended_pct"]
            reason = data["reason"]
            
            if final_conc_pct > max_pct:
                warnings.append(
                    f"⚠️ OVERUSE: {material} at {final_conc_pct:.1f}% exceeds recommended max ({max_pct}%)"
                )
                warnings.append(f"   {reason}")
                wasteful = True
            elif batch_is_large and final_conc_pct > max_pct * 0.5:
                warnings.append(
                    f"⚠️ CHECK NECESSITY: Using {dose_ml:.1f} mL {material} in large batch"
                )
                warnings.append(f"   {reason} - Is this actually needed?")
    
    # Check if material is expensive
    for expensive_name, data in EXPENSIVE_MATERIALS.items():
        if expensive_name in material_lower:
            cost_per_ml = data["cost_per_ml"]
            total_cost = dose_ml * cost_per_ml
            
            # Warning if using expensive material in large batch
            if batch_is_large and dose_ml > 5:
                warnings.append(
                    f"⚠️ COST WARNING: Using {dose_ml:.1f} mL of {material} in large batch = ${total_cost:.2f}"
                )
                warnings.append(
                    f"   Consider testing in 10-20 mL batch first to avoid waste"
                )
                wasteful = True
            
            # Check if cheaper substitute exists - PRIORITIZE OWNED MATERIALS
            substitutes_owned = data.get("substitutes_owned", [])
            substitutes_new = data.get("substitutes_new", [])
            substitute_ratio = data.get("substitute_ratio", 0)
            
            # Filter to actually owned substitutes
            available_owned = [s for s in substitutes_owned if is_owned(s)]
            
            if substitute_ratio > 0 and (available_owned or substitutes_new):
                substitute_dose = dose_ml * substitute_ratio
                savings = total_cost * (1 - substitute_ratio)
                
                if available_owned:
                    # ✓ YOU OWN THESE - prioritize
                    substitute_list = " OR ".join(available_owned)
                    alternative = (
                        f"✓ OWNED SUBSTITUTES: {substitute_list} at {substitute_dose:.1f} mL "
                        f"(instead of {dose_ml:.1f} mL {material} = ${total_cost:.2f}, saves ~${savings:.2f})"
                    )
                elif substitutes_new:
                    # ⚠️ Not owned - would need to buy
                    substitute_list = " OR ".join(substitutes_new)
                    alternative = (
                        f"⚠️ NO SUBSTITUTE IN INVENTORY: Would need to buy {substitute_list} "
                        f"(or use {dose_ml:.1f} mL {material} = ${total_cost:.2f})"
                    )
                
                if batch_is_large:
                    warnings.append(alternative)
            elif available_owned or substitutes_new:
                # Has substitutes but ratio logic doesn't apply (special materials)
                if available_owned:
                    substitute_list = " OR ".join(available_owned)
                    warnings.append(f"✓ OWNED ALTERNATIVES: {substitute_list}")
                else:
                    substitute_list = " OR ".join(substitutes_new)
                    if "only if" in substitute_list.lower():
                        warnings.append(f"⚠️ CHECK NECESSITY: {substitute_list}")
            
            break
    
    return wasteful, warnings, alternative

def classify_base_type(formula: Dict[str, float]) -> str:
    """
    Classify base type from formula composition.
    
    Returns: "clean", "heavy_oriental", "chypre", "leather", "fougere"
    """
    total_pct = sum(formula.values())
    if total_pct == 0:
        return "unknown"
    
    # Calculate heavy fixative content
    heavy_fixative_pct = sum(
        pct for ing, pct in formula.items() 
        if any(resin in ing.lower() for resin in HEAVY_RESINS) or "vanilla" in ing.lower() or "tonka" in ing.lower()
    )
    
    # Calculate animalic content
    animalic_pct = sum(
        pct for ing, pct in formula.items()
        if any(animal in ing.lower() for animal in ANIMALIC_MATERIALS)
    )
    
    # Calculate mossy/earthy content
    mossy_pct = sum(
        pct for ing, pct in formula.items()
        if "oakmoss" in ing.lower() or "patchouli" in ing.lower()
    )
    
    # Classification logic
    if animalic_pct > 2 or "leather" in str(formula).lower() or "oud" in str(formula).lower():
        return "leather"
    elif heavy_fixative_pct > 10:
        return "heavy_oriental"
    elif mossy_pct > 3:
        return "chypre"
    elif "lavender" in str(formula).lower() and "coumarin" in str(formula).lower():
        return "fougere"
    elif heavy_fixative_pct < 5:
        return "clean"
    else:
        return "moderate"  # Fallback

def get_odt(material_name: str) -> Optional[float]:
    """Get ODT for a material (% in solution)."""
    name_lower = material_name.lower()
    
    # Direct match
    if name_lower in ODT_DATABASE:
        return ODT_DATABASE[name_lower]
    
    # Fuzzy match for common variations
    for key in ODT_DATABASE:
        if key in name_lower or name_lower in key:
            return ODT_DATABASE[key]
    
    return None

def validate_dosage(
    material: str, 
    dose_ml: float, 
    base_ml: float, 
    base_formula: Optional[Dict[str, float]] = None,
    batch_size_ml: Optional[float] = None
) -> DosageValidation:
    """
    Validate a dosage recommendation before suggesting to user.
    
    Args:
        material: Material name
        dose_ml: Amount to add (mL)
        base_ml: Base volume (mL)
        base_formula: Optional dict of {ingredient: percentage} for base type classification
        batch_size_ml: Optional total batch size for cost/waste checking
    
    Returns:
        DosageValidation with safety assessment
    """
    errors = []
    warnings = []
    safe = True
    base_compatible = True
    odor_value = None
    
    material_lower = material.lower()
    total_batch = batch_size_ml if batch_size_ml else base_ml
    batch_is_large = total_batch >= 50
    
    # Step 1: Check material conservation (NEW)
    wasteful, conservation_warnings, alternative = check_material_conservation(
        material, dose_ml, base_ml, batch_is_large
    )
    warnings.extend(conservation_warnings)
    
    # Step 1.5: Inventory prioritization check (warn if material NOT owned)
    if not is_owned(material):
        warnings.append(
            f"⚠️ '{material}' NOT in inventory - check if you already own a substitute before buying"
        )
    
    # Step 1.6: Chemical class identification
    material_classes = get_chemical_classes(material)
    
    # Step 1.7: Base type classification (if formula provided)
    base_type = "unknown"
    if base_formula:
        base_type = classify_base_type(base_formula)
    
    # Step 1.8: Base compatibility check (CRITICAL - INCOMPATIBILITY FAILURES)
    if base_type != "unknown":
        compatibility, compat_warnings = check_base_compatibility(material, base_type)
        warnings.extend(compat_warnings)
        
        if compatibility == "FORBIDDEN":
            errors.append(f"❌ FATAL: {material} FORBIDDEN in {base_type} bases - will fail catastrophically")
            safe = False
            base_compatible = False
        elif compatibility == "POOR":
            warnings.append(f"⚠️ Material will perform poorly in this base type")
    
    # Step 1.9: Degradation risk check
    if base_formula:
        degradation_warnings = check_degradation_risk(material, base_formula)
        warnings.extend(degradation_warnings)
    
    # Step 2: Get ODT
    odt = get_odt(material)
    
    # Step 3: Calculate final concentration %
    final_conc_pct = (dose_ml / base_ml) * 100 if base_ml > 0 else 0
    
    # Step 4: Check commercial usage ranges (NEW)
    abnormal_dose, commercial_warnings = check_commercial_usage(material, final_conc_pct)
    warnings.extend(commercial_warnings)
    if abnormal_dose:
        errors.append(f"❌ DOSE ABNORMALITY: {final_conc_pct:.2f}% far exceeds normal perfume usage")
        safe = False
    
    # Step 5: Calculate Odor Value and apply tier-based thresholds
    if odt:
        odor_value = final_conc_pct / odt
        
        # Determine intensity tier
        tier = get_intensity_tier(odt)
        
        # Get appropriate thresholds for this tier
        if tier == "ultra_potent":
            thresholds = OV_THRESHOLDS["ultra_potent"]
            if odor_value > thresholds["error"]:
                errors.append(
                    f"❌ ULTRA-POTENT OVERDOSE: OV = {odor_value:.0f} (ODT {odt}%) - MUST pre-dilute to 1:1000, add {(dose_ml * 1000):.1f} mL of dilution"
                )
                safe = False
            elif odor_value > thresholds["warn"]:
                warnings.append(f"⚠️ ULTRA-POTENT: OV = {odor_value:.0f} - approaching limit (max OV {thresholds['safe']})")
                
        elif tier == "extremely_potent":
            # Different thresholds for animalics vs. others
            if "animalic" in material_classes:
                thresholds = OV_THRESHOLDS["extremely_potent_animalic"]
                if odor_value > thresholds["error"]:
                    errors.append(
                        f"❌ ANIMALIC OVERDOSE: OV = {odor_value:.0f} - Will smell FECAL/DISGUSTING (max OV {thresholds['error']} for animalics)"
                    )
                    errors.append(
                        f"   Pre-dilute to 0.1-1% and add 1-3 drops only"
                    )
                    safe = False
            else:
                thresholds = OV_THRESHOLDS["extremely_potent_other"]
                if odor_value > thresholds["error"]:
                    errors.append(
                        f"❌ EXTREME OVERDOSE: OV = {odor_value:.0f} (max {thresholds['error']} for this tier)"
                    )
                    safe = False
                    
        elif tier == "high_impact":
            thresholds = OV_THRESHOLDS["high_impact"]
            if odor_value > thresholds["error"]:
                errors.append(f"❌ OVERDOSE: OV = {odor_value:.0f} - overpowering (max {thresholds['error']})")
                safe = False
            elif odor_value > thresholds["warn"]:
                warnings.append(f"⚠️ HIGH: OV = {odor_value:.0f} - may be too strong (recommended <{thresholds['warn']})")
                
        elif tier == "moderate":
            thresholds = OV_THRESHOLDS["moderate"]
            if odor_value > thresholds["error"]:
                errors.append(f"❌ OVERDOSE: OV = {odor_value:.0f} - excessive (max {thresholds['error']})")
                safe = False
            elif odor_value > thresholds["warn"]:
                warnings.append(f"⚠️ High OV = {odor_value:.0f} (recommended <{thresholds['warn']})")
                
        elif tier == "low":
            thresholds = OV_THRESHOLDS["low"]
            if odor_value > thresholds["error"]:
                warnings.append(f"⚠️ VERY HIGH: OV = {odor_value:.0f} - may dominate (typical max {thresholds['error']})")
    else:
        warnings.append(f"⚠️ ODT unknown for '{material}' - cannot validate strength")
    
    # Step 6: Legacy base compatibility check (kept for backward compatibility, but Step 1.8 now handles this comprehensively)
    if any(animalic in material_lower for animalic in ANIMALIC_MATERIALS):
        if base_formula:
            base_type = classify_base_type(base_formula)
        else:
            base_type = "unknown"
        
        if base_type == "clean":
            errors.append(
                f"❌ BASE INCOMPATIBLE: '{material}' is animalic and will smell FECAL in clean/transparent bases"
            )
            errors.append(
                "   Clean bases (like BR540) expose fecal notes. DO NOT USE."
            )
            safe = False
            base_compatible = False
        elif base_type == "heavy_oriental":
            if final_conc_pct > 0.05:
                warnings.append(
                    f"⚠️ Even in heavy oriental base, animalics should be ≤0.05% (currently {final_conc_pct:.3f}%)"
                )
                warnings.append(
                    "   Recommended: Pre-dilute to 1% and add 1-3 drops only"
                )
        elif base_type == "unknown":
            warnings.append(
                f"⚠️ '{material}' is animalic - ENSURE base is heavy oriental/leather/chypre, NOT clean/transparent"
            )
    
    # Step 7: Generate recommendation
    if not safe:
        if not base_compatible:
            recommendation = f"DO NOT USE - Animalics incompatible with this base type. Omit entirely or use clean alternatives (exaltolide, ambroxan, iso E super)"
        else:
            # Calculate safe dose
            if odt and odor_value:
                target_ov = 1000  # Safe upper limit
                safe_conc = odt * target_ov
                safe_dose_ml = (safe_conc / 100) * base_ml
                recommendation = f"REDUCE DOSE: Use maximum {safe_dose_ml:.3f} mL (target OV ≤ 1000)"
            else:
                recommendation = f"REDUCE DOSE: Start with 10× less ({dose_ml/10:.3f} mL) and test"
    else:
        if wasteful and alternative:
            recommendation = alternative + f" | Current dose OK but expensive for large batch"
        elif len(warnings) > 0:
            recommendation = f"CAUTION: Dose is high but may work. Test small batch first."
        else:
            recommendation = f"Safe at {dose_ml:.3f} mL" + (f" (OV = {odor_value:.0f})" if odor_value else "")
    
    return DosageValidation(
        safe=safe,
        odor_value=odor_value,
        base_compatible=base_compatible,
        errors=errors,
        warnings=warnings,
        recommendation=recommendation
    )

def get_compounds():
    global COMPOUNDS
    if COMPOUNDS is None:
        COMPOUNDS = load_compounds()
    return COMPOUNDS


def ifra_check(formula: dict[str, float]) -> list[dict]:
    """Quick IFRA-only validation for a formula.

    Args:
        formula: Dict of {ingredient_name: percentage_in_concentrate}

    Returns:
        List of dicts with keys: ingredient, pct, limit, status
        status is 'ok', 'warning' (>80% of limit), or 'violation'.
    """
    compounds = get_compounds()
    results = []
    for ingredient, pct in formula.items():
        ing_lower = ingredient.lower()
        if ing_lower not in compounds:
            continue
        limit = compounds[ing_lower].get("ifra_limit")
        if limit is None:
            continue
        if pct > limit:
            status = "violation"
        elif pct > limit * 0.8:
            status = "warning"
        else:
            status = "ok"
        results.append({
            "ingredient": ingredient,
            "pct": pct,
            "limit": limit,
            "status": status,
        })
    return results


def validate_formula(formula: dict[str, float], product_type: str = "fine_fragrance") -> ValidationResult:
    """
    Validate a formula against chemistry and perfumery rules.
    
    Args:
        formula: Dict of {ingredient_name: percentage}
        product_type: Application type affecting IFRA limits
    
    Returns:
        ValidationResult with errors and warnings
    """
    errors = []
    warnings = []
    compounds = get_compounds()
    
    total_pct = sum(formula.values())
    note_balance = {"top": 0, "heart": 0, "base": 0}
    allergen_total = 0
    
    for ingredient, pct in formula.items():
        ing_lower = ingredient.lower()
        
        # Check ingredient exists in compounds db
        if ing_lower not in compounds:
            # Fallback: use ingredient_intelligence for note balance tracking
            try:
                from .ingredient_intelligence import get_profile
                profile = get_profile(ingredient)
                if profile:
                    note_balance[profile.note] += pct
                else:
                    warnings.append(f"Unknown ingredient: {ingredient}")
            except (ImportError, Exception):
                warnings.append(f"Unknown ingredient: {ingredient}")
            continue
            
        compound = compounds[ing_lower]
        
        # CHEMISTRY RULE: Concentration limits
        if pct > compound["ifra_limit"]:
            errors.append(
                f"IFRA VIOLATION: {ingredient} at {pct}% exceeds limit of {compound['ifra_limit']}%"
            )
        elif pct > compound["ifra_limit"] * 0.8:
            warnings.append(f"{ingredient} at {pct}% is near IFRA limit ({compound['ifra_limit']}%)")
        
        # CHEMISTRY RULE: Allergen tracking
        if compound["allergen"]:
            allergen_total += pct
        
        # PERFUMERY RULE: Note balance tracking
        note_balance[compound["note"]] += pct
    
    # CHEMISTRY RULE: Total concentration
    if total_pct > 30:
        warnings.append(f"High total concentration ({total_pct}%) - may cause skin sensitivity")
    
    # CHEMISTRY RULE: Allergen declaration threshold
    if allergen_total > 0.001:
        warnings.append(f"Allergen declaration required: {allergen_total:.2f}% total allergens")
    
    # PERFUMERY RULE: Note balance (ideal ~15-25% top, 30-40% heart, 40-55% base)
    if total_pct > 0:
        top_ratio = note_balance["top"] / total_pct * 100
        heart_ratio = note_balance["heart"] / total_pct * 100
        base_ratio = note_balance["base"] / total_pct * 100
        
        if top_ratio < 10:
            warnings.append(f"Low top notes ({top_ratio:.0f}%) - fragrance may lack initial impact")
        if top_ratio > 35:
            warnings.append(f"Heavy top notes ({top_ratio:.0f}%) - fragrance may lack longevity")
        if base_ratio < 30:
            warnings.append(f"Weak base ({base_ratio:.0f}%) - fragrance may not last")
    
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )

def check_compatibility(ingredients: list[str]) -> list[str]:
    """Check chemical compatibility between ingredients."""
    warnings = []
    compounds = get_compounds()
    
    # Check for known problematic combinations
    has_aldehyde = any(
        compounds.get(i.lower(), {}).get("category") == "Aldehyde" 
        for i in ingredients
    )
    has_phenol = any(
        compounds.get(i.lower(), {}).get("category") == "Phenol"
        for i in ingredients
    )
    
    if has_aldehyde and has_phenol:
        warnings.append("Aldehydes + Phenols may cause discoloration over time")
    
    return warnings
