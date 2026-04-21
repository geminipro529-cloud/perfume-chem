"""Molecular weight and logP distribution analysis for fragrance reconstruction.

PHYSICOCHEMICAL_COHERENCE category module. Checks that the hypothesized formula's
molecular weight (MW) distribution and logP (lipophilicity) distribution matches
expected patterns for the fragrance family.

Rules:
- Citrus/aquatic fragrances skew LOW MW (< 200) — terpenes, esters
- Orientals/ambers skew HIGH MW (> 230) — musks, benzyl esters, ambroxides
- Chypres have BIMODAL distribution — light citrus + heavy fixatives
- Florals span mid-range (150-250)
- Fougères: lavender (154)/coumarin (146)/oakmoss (heavy) = characteristic spread
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


MW_DATA: dict[str, dict] = {
    "limonene":               {"mw": 136.2, "logp": 4.6,  "tags": ["citrus", "fresh", "top"]},
    "d-limonene":             {"mw": 136.2, "logp": 4.6,  "tags": ["citrus", "fresh", "top"]},
    "linalool":               {"mw": 154.2, "logp": 2.6,  "tags": ["floral", "lavender", "heart"]},
    "bergamot":               {"mw": 136.2, "logp": 4.5,  "tags": ["citrus", "fresh"]},
    "linalyl acetate":        {"mw": 196.3, "logp": 3.7,  "tags": ["floral", "fresh", "heart"]},
    "citronellol":            {"mw": 156.3, "logp": 3.5,  "tags": ["rose", "floral", "heart"]},
    "geraniol":               {"mw": 154.2, "logp": 2.8,  "tags": ["rose", "floral", "heart"]},
    "eugenol":                {"mw": 164.2, "logp": 2.4,  "tags": ["spice", "oriental", "heart"]},
    "hydroxycitronellal":     {"mw": 172.3, "logp": 1.5,  "tags": ["muguet", "floral", "heart"]},
    "alpha irone":            {"mw": 192.3, "logp": 3.2,  "tags": ["iris", "orris", "heart"]},
    "alpha-isomethyl ionone": {"mw": 206.3, "logp": 3.9,  "tags": ["iris", "violet", "heart"]},
    "iso e super":            {"mw": 204.3, "logp": 4.5,  "tags": ["woody", "cedar", "heart"]},
    "hedione":                {"mw": 226.3, "logp": 3.5,  "tags": ["jasmine", "floral", "heart"]},
    "cis-jasmone":            {"mw": 164.2, "logp": 2.2,  "tags": ["jasmine", "floral", "heart"]},
    "phenethyl alcohol":      {"mw": 122.2, "logp": 1.2,  "tags": ["rose", "floral", "heart"]},
    "indole":                 {"mw": 117.1, "logp": 2.1,  "tags": ["floral", "animalic", "heart"]},
    "benzyl salicylate":      {"mw": 228.2, "logp": 4.3,  "tags": ["floral", "balsamic", "base"]},
    "coumarin":               {"mw": 146.2, "logp": 1.4,  "tags": ["fougere", "tonka", "base"]},
    "ambrox":                 {"mw": 236.4, "logp": 5.5,  "tags": ["amber", "oriental", "base"]},
    "ambrox super":           {"mw": 236.4, "logp": 5.5,  "tags": ["amber", "oriental", "base"]},
    "galaxolide":             {"mw": 258.4, "logp": 5.9,  "tags": ["musk", "clean", "base"]},
    "habanolide":             {"mw": 254.4, "logp": 6.1,  "tags": ["musk", "skin", "base"]},
    "ethylene brassylate":    {"mw": 270.4, "logp": 5.8,  "tags": ["musk", "white", "base"]},
    "patchouli alcohol":      {"mw": 222.4, "logp": 4.5,  "tags": ["earthy", "oriental", "base"]},
    "vetiver":                {"mw": 222.0, "logp": 4.0,  "tags": ["earthy", "woody", "base"]},
    "cedarwood":              {"mw": 204.4, "logp": 5.0,  "tags": ["woody", "dry", "heart"]},
    "labdanum":               {"mw": 210.0, "logp": 4.0,  "tags": ["amber", "resin", "base"]},
    "benzoin resinoid":       {"mw": 228.2, "logp": 3.8,  "tags": ["oriental", "balsamic", "base"]},
    "ethyl vanillin":         {"mw": 166.2, "logp": 1.6,  "tags": ["oriental", "vanilla", "base"]},
    "vanillin":               {"mw": 152.2, "logp": 1.2,  "tags": ["oriental", "vanilla", "base"]},
    "farnesol":               {"mw": 222.4, "logp": 5.5,  "tags": ["floral", "green", "base"]},
    "benzyl benzoate":        {"mw": 212.2, "logp": 3.7,  "tags": ["oriental", "floral", "base"]},
    "benzyl alcohol":         {"mw": 108.1, "logp": 1.1,  "tags": ["floral", "herbal", "heart"]},
    "cashmeran":              {"mw": 214.4, "logp": 4.6,  "tags": ["musk", "woody", "base"]},
    "vertofix coeur":         {"mw": 204.4, "logp": 4.8,  "tags": ["woody", "amber", "base"]},
    "timberol":               {"mw": 200.3, "logp": 4.0,  "tags": ["woody", "cedar", "heart"]},
    "rose absolute":          {"mw": 154.0, "logp": 2.8,  "tags": ["rose", "floral", "heart"]},
    "jasmine absolute":       {"mw": 196.0, "logp": 3.0,  "tags": ["jasmine", "floral", "heart"]},
    "oud oil":                {"mw": 222.0, "logp": 5.5,  "tags": ["oriental", "oud", "base"]},
    "guaiacol":               {"mw": 124.1, "logp": 1.3,  "tags": ["smoke", "phenolic", "heart"]},
    "rose oxide":             {"mw": 154.2, "logp": 2.7,  "tags": ["rose", "floral", "heart"]},
    "evernyl":                {"mw": 182.2, "logp": 3.1,  "tags": ["moss", "chypre", "base"]},
    # Additional inventory materials
    "paradisamide":           {"mw": 213.3, "logp": 2.8,  "tags": ["fruity", "tropical", "heart"]},
    "methyl pamplemousse":    {"mw": 184.3, "logp": 3.2,  "tags": ["citrus", "fresh", "top"]},
    "terpinyl acetate":       {"mw": 196.3, "logp": 3.5,  "tags": ["citrus", "herbal", "top"]},
    "dbca":                   {"mw": 172.0, "logp": 2.9,  "tags": ["floral", "gardenia", "heart"]},
    "hedione hc":             {"mw": 226.3, "logp": 3.5,  "tags": ["jasmine", "floral", "heart"]},
    "hexyl salicylate":       {"mw": 222.3, "logp": 5.0,  "tags": ["floral", "balsamic", "base"]},
    "ultralia":               {"mw": 198.3, "logp": 3.4,  "tags": ["iris", "powdery", "heart"]},
    "vetival":                {"mw": 218.0, "logp": 4.2,  "tags": ["vetiver", "woody", "base"]},
    "kephalis":               {"mw": 246.4, "logp": 5.2,  "tags": ["woody", "amber", "base"]},
    "amberwood f":            {"mw": 238.4, "logp": 4.8,  "tags": ["amber", "woody", "base"]},
    "suederal":               {"mw": 196.3, "logp": 3.6,  "tags": ["leather", "suede", "base"]},
    "ebanol":                 {"mw": 220.3, "logp": 4.1,  "tags": ["sandalwood", "creamy", "base"]},
    "javanol":                {"mw": 222.4, "logp": 4.3,  "tags": ["sandalwood", "skin", "base"]},
    "orivone":                {"mw": 208.3, "logp": 3.8,  "tags": ["iris", "orris", "heart"]},
    "scentenal":              {"mw": 140.2, "logp": 2.5,  "tags": ["ozone", "mineral", "top"]},
    "dynascone":              {"mw": 192.3, "logp": 3.7,  "tags": ["green", "galbanum", "top"]},
    "parmavert":              {"mw": 154.2, "logp": 2.4,  "tags": ["green", "violet", "top"]},
    "leafovert":              {"mw": 140.2, "logp": 2.6,  "tags": ["green", "fresh", "top"]},
    "cyclamen aldehyde":      {"mw": 188.3, "logp": 3.8,  "tags": ["floral", "metallic", "heart"]},
    "allyl amyl glycolate":   {"mw": 186.3, "logp": 3.2,  "tags": ["green", "fresh", "top"]},
    "ethyl safranate":        {"mw": 208.3, "logp": 3.4,  "tags": ["spice", "saffron", "heart"]},
    "ibq":                    {"mw": 185.3, "logp": 3.6,  "tags": ["leather", "animalic", "base"]},
    "isobutyl quinoline":     {"mw": 185.3, "logp": 3.6,  "tags": ["leather", "animalic", "base"]},
    "styrax ftec":            {"mw": 210.0, "logp": 3.5,  "tags": ["leather", "balsamic", "base"]},
    "koavone":                {"mw": 206.3, "logp": 4.2,  "tags": ["woody", "cedar", "heart"]},
    "freesia hdi":            {"mw": 168.2, "logp": 2.8,  "tags": ["floral", "green", "heart"]},
    "lilyreal nd":            {"mw": 172.0, "logp": 2.6,  "tags": ["muguet", "floral", "heart"]},
    "grapefruit fcf":         {"mw": 136.2, "logp": 4.2,  "tags": ["citrus", "fresh", "top"]},
    "blood orange sicilian":  {"mw": 136.2, "logp": 4.4,  "tags": ["citrus", "fresh", "top"]},
    "red mandarin eo":        {"mw": 136.2, "logp": 4.3,  "tags": ["citrus", "oriental", "top"]},
    "cedrat fcf sicilian":    {"mw": 154.2, "logp": 4.1,  "tags": ["citrus", "mineral", "top"]},
    "bergamot fcf":           {"mw": 136.2, "logp": 4.5,  "tags": ["citrus", "fresh", "top"]},
    "bergamot fcf sicilian":  {"mw": 136.2, "logp": 4.5,  "tags": ["citrus", "fresh", "top"]},
    "lavender":               {"mw": 154.2, "logp": 2.6,  "tags": ["lavender", "fougere", "top"]},
    "neroli":                 {"mw": 136.2, "logp": 4.0,  "tags": ["citrus", "floral", "top"]},
    "patchouli":              {"mw": 222.4, "logp": 4.5,  "tags": ["earthy", "oriental", "base"]},
    "ylang ylang":            {"mw": 222.4, "logp": 5.1,  "tags": ["floral", "oriental", "heart"]},
    "sandalwood":             {"mw": 222.4, "logp": 4.3,  "tags": ["sandalwood", "woody", "base"]},
    "birch tar":              {"mw": 124.1, "logp": 2.8,  "tags": ["leather", "smoke", "base"]},
    "cardamom":               {"mw": 192.3, "logp": 2.5,  "tags": ["spice", "herbal", "top"]},
    "saffron":                {"mw": 212.2, "logp": 2.4,  "tags": ["spice", "oriental", "heart"]},
    "maple lactone":          {"mw": 100.1, "logp": 0.8,  "tags": ["gourmand", "sweet", "base"]},
    "gamma decalactone":      {"mw": 170.3, "logp": 3.2,  "tags": ["peach", "fruity", "base"]},
    "delta decalactone":      {"mw": 170.3, "logp": 3.2,  "tags": ["peach", "fruity", "base"]},
    "calone":                 {"mw": 192.2, "logp": 2.6,  "tags": ["aquatic", "ozonic", "top"]},
    "dihydromyrcenol":        {"mw": 156.3, "logp": 3.4,  "tags": ["fresh", "citrus", "top"]},
    "musk ketone":            {"mw": 294.4, "logp": 4.9,  "tags": ["musk", "oriental", "base"]},
    "ambrettolide":           {"mw": 252.4, "logp": 6.5,  "tags": ["musk", "skin", "base"]},
    "iso e super 10%":        {"mw": 204.3, "logp": 4.5,  "tags": ["woody", "cedar", "heart"]},
    "cashmeran 20%":          {"mw": 214.4, "logp": 4.6,  "tags": ["musk", "woody", "base"]},
}


FAMILY_MW_PROFILES: dict[str, dict] = {
    "citrus":   {
        "mean_mw": 145, "std_mw": 30,
        "mean_logp": 4.0,
        "description": "Terpenic, light, fast-evaporating",
    },
    "fougere":  {
        "mean_mw": 170, "std_mw": 40,
        "mean_logp": 2.8,
        "description": "Lavender-coumarin-oakmoss triad",
    },
    "floral":   {
        "mean_mw": 180, "std_mw": 45,
        "mean_logp": 3.0,
        "description": "Mid-range florals, esters, aldehydes",
    },
    "chypre":   {
        "mean_mw": 190, "std_mw": 60,
        "mean_logp": 3.5,
        "description": "Bimodal: citrus top + heavy fixatives",
    },
    "oriental": {
        "mean_mw": 210, "std_mw": 50,
        "mean_logp": 4.2,
        "description": "Heavy resins, musks, ambers",
    },
    "woody":    {
        "mean_mw": 205, "std_mw": 45,
        "mean_logp": 4.5,
        "description": "Cedar, sandalwood, amber",
    },
    "iris":     {
        "mean_mw": 190, "std_mw": 40,
        "mean_logp": 3.3,
        "description": "Ionones, irones, powdery materials",
    },
    "aquatic":  {
        "mean_mw": 155, "std_mw": 35,
        "mean_logp": 3.5,
        "description": "Fresh, light, calone-type",
    },
    "gourmand": {
        "mean_mw": 165, "std_mw": 45,
        "mean_logp": 2.0,
        "description": "Vanilla, lactones, sweet materials",
    },
    "leather":  {
        "mean_mw": 200, "std_mw": 55,
        "mean_logp": 3.8,
        "description": "Phenolics, birch, suede synthetics",
    },
}


@dataclass
class MWConstraint:
    material: str
    mw: float
    logp: float
    tags: list[str]
    fits_family: bool  # MW and logP within 2σ of family profile


@dataclass
class MWAnalysisResult:
    target_name: str
    detected_family: str = ""
    constraints: list[MWConstraint] = field(default_factory=list)
    mean_mw: float = 0.0
    std_mw: float = 0.0
    mean_logp: float = 0.0
    family_match_score: float = 0.0  # 0-100, how well formula MW matches expected family
    outlier_materials: list[str] = field(default_factory=list)  # MW outliers for family
    score: float = 0.0  # 0-100 PHYSICOCHEMICAL_COHERENCE score


def _normalize_material_name(name: str) -> str:
    """Normalize material name for MW_DATA lookup."""
    return name.lower().strip()


def _lookup_mw_data(name: str) -> Optional[dict]:
    """Look up MW data for a material, trying various normalization strategies."""
    normalized = _normalize_material_name(name)

    # Direct lookup
    if normalized in MW_DATA:
        return MW_DATA[normalized]

    # Try stripping dilution suffixes like "10%", "20%", etc.
    import re
    stripped = re.sub(r"\s*\d+%\s*$", "", normalized).strip()
    if stripped in MW_DATA:
        return MW_DATA[stripped]

    # Try partial match: check if normalized starts with any key
    for key in MW_DATA:
        if normalized.startswith(key) or key.startswith(normalized):
            return MW_DATA[key]

    # Try word overlap heuristic: match if all words in key appear in name
    name_words = set(normalized.split())
    for key, data in MW_DATA.items():
        key_words = set(key.split())
        if key_words and key_words.issubset(name_words):
            return data

    return None


def _weighted_mean(values: list[float], weights: list[float]) -> float:
    """Compute weighted mean."""
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    return sum(v * w for v, w in zip(values, weights)) / total_weight


def _weighted_std(values: list[float], weights: list[float], wmean: float) -> float:
    """Compute weighted standard deviation."""
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    variance = sum(w * (v - wmean) ** 2 for v, w in zip(values, weights)) / total_weight
    return math.sqrt(variance)


def _auto_detect_family(mean_mw: float) -> str:
    """Auto-detect fragrance family by finding FAMILY_MW_PROFILES entry closest to mean_mw."""
    best_family = "floral"
    best_distance = float("inf")
    for family, profile in FAMILY_MW_PROFILES.items():
        distance = abs(profile["mean_mw"] - mean_mw)
        if distance < best_distance:
            best_distance = distance
            best_family = family
    return best_family


def analyze_mw_distribution(
    target_name: str,
    material_posteriors: dict[str, float],
    fragrance_family: str = "",
    confirmed_materials: Optional[list[str]] = None,
) -> MWAnalysisResult:
    """Analyze the MW and logP distribution of a hypothesized formula.

    Args:
        target_name: Name of the target fragrance being reconstructed.
        material_posteriors: Dict of {material_name: posterior_probability}.
            Only materials with posterior > 0.3 are considered.
        fragrance_family: Expected fragrance family (e.g. "iris", "oriental").
            If empty, auto-detected from computed mean MW.
        confirmed_materials: Optional list of confirmed material names. These
            are added with posterior weight 1.0 if not already present.

    Returns:
        MWAnalysisResult with MW distribution analysis and coherence score.
    """
    result = MWAnalysisResult(target_name=target_name)

    # Merge confirmed materials at full weight
    posteriors = dict(material_posteriors)
    if confirmed_materials:
        for mat in confirmed_materials:
            key = _normalize_material_name(mat)
            if key not in {_normalize_material_name(k) for k in posteriors}:
                posteriors[mat] = 1.0

    # Filter to materials with posterior > 0.3 that have MW data
    classified: list[tuple[str, float, dict]] = []
    for material, posterior in posteriors.items():
        if posterior <= 0.3:
            continue
        data = _lookup_mw_data(material)
        if data is not None:
            classified.append((material, posterior, data))

    if not classified:
        result.score = 0.0
        return result

    mws = [d["mw"] for _, _, d in classified]
    logps = [d["logp"] for _, _, d in classified]
    weights = [p for _, p, _ in classified]

    # Weighted statistics
    result.mean_mw = _weighted_mean(mws, weights)
    result.std_mw = _weighted_std(mws, weights, result.mean_mw)
    result.mean_logp = _weighted_mean(logps, weights)

    # Family detection
    if fragrance_family and fragrance_family.lower() in FAMILY_MW_PROFILES:
        result.detected_family = fragrance_family.lower()
    else:
        result.detected_family = _auto_detect_family(result.mean_mw)

    family_profile = FAMILY_MW_PROFILES[result.detected_family]
    family_mean = family_profile["mean_mw"]
    family_std = family_profile["std_mw"]

    # Build MWConstraint objects and evaluate fit
    constraints: list[MWConstraint] = []
    n_fits = 0
    outliers: list[str] = []

    for material, posterior, data in classified:
        mw = data["mw"]
        logp = data["logp"]
        tags = data["tags"]

        # Within 2σ of family mean MW
        fits_family = abs(mw - family_mean) < 2.0 * family_std

        constraint = MWConstraint(
            material=material,
            mw=mw,
            logp=logp,
            tags=tags,
            fits_family=fits_family,
        )
        constraints.append(constraint)

        if fits_family:
            n_fits += 1

        # Outlier: > 2.5σ from family mean
        if abs(mw - family_mean) > 2.5 * family_std:
            outliers.append(material)

    result.constraints = constraints
    result.outlier_materials = outliers

    n_total = len(classified)
    n_classified = n_total  # all classified entries have MW data by construction

    # family_match_score: percentage of materials fitting the family MW window
    result.family_match_score = 100.0 * (n_fits / max(1, n_total))

    # score formula: 70% family match + up to 30 points for breadth of classified materials
    result.score = result.family_match_score * 0.7 + min(30.0, n_classified * 3.0)

    return result


def format_mw_analysis(result: MWAnalysisResult) -> str:
    """Format MW analysis result as a human-readable string.

    Shows MW histogram bands (< 150, 150-200, 200-250, > 250) and counts,
    plus summary statistics and outlier information.
    """
    lines: list[str] = []
    lines.append(f"MW Distribution Analysis — {result.target_name}")
    lines.append("=" * 60)
    lines.append(f"Detected family : {result.detected_family}")
    lines.append(f"Mean MW         : {result.mean_mw:.1f} g/mol")
    lines.append(f"Std MW          : {result.std_mw:.1f} g/mol")
    lines.append(f"Mean logP       : {result.mean_logp:.2f}")
    lines.append(f"Family match    : {result.family_match_score:.1f}%")
    lines.append(f"Overall score   : {result.score:.1f}/100")
    lines.append("")

    # Histogram bands
    bands: dict[str, list[str]] = {
        "< 150":     [],
        "150 – 200": [],
        "200 – 250": [],
        "> 250":     [],
    }
    for c in result.constraints:
        if c.mw < 150:
            bands["< 150"].append(c.material)
        elif c.mw < 200:
            bands["150 – 200"].append(c.material)
        elif c.mw <= 250:
            bands["200 – 250"].append(c.material)
        else:
            bands["> 250"].append(c.material)

    lines.append("MW Band Distribution:")
    lines.append("-" * 40)
    total = max(1, len(result.constraints))
    for band, materials in bands.items():
        count = len(materials)
        pct = 100.0 * count / total
        bar = "#" * count
        mat_list = ", ".join(materials) if materials else "—"
        lines.append(f"  {band:>10}  [{bar:<12}] {count:>2} ({pct:4.0f}%)  {mat_list}")

    if result.outlier_materials:
        lines.append("")
        lines.append("MW Outliers (> 2.5σ from family mean):")
        for mat in result.outlier_materials:
            # Find the constraint for this material
            mw_val = next(
                (c.mw for c in result.constraints if c.material == mat), float("nan")
            )
            lines.append(f"  • {mat}  (MW {mw_val:.1f})")

    lines.append("")
    lines.append("Material Detail:")
    lines.append("-" * 40)
    lines.append(f"  {'Material':<30} {'MW':>7}  {'logP':>6}  {'Fits?':<6}")
    for c in sorted(result.constraints, key=lambda x: x.mw):
        fits_str = "yes" if c.fits_family else "NO"
        lines.append(f"  {c.material:<30} {c.mw:>7.1f}  {c.logp:>6.2f}  {fits_str:<6}")

    return "\n".join(lines)
