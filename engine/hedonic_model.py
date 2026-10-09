"""Hedonic valence modelling — intrinsic pleasantness prediction.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm, ODT in ppm/ppb, OAV = C/ODT (dimensionless).
- Every perceptibility claim must be backed by OAV.

Odorant molecules have measurable hedonic valence (pleasantness)
that is partially universal across cultures. Khan et al. (2007)
demonstrated that molecular features (compact, high MW, fewer
functional groups = pleasant; small, polar, with S/N = unpleasant)
predict hedonic ratings with R² ≈ 0.55.

This module scores each material's hedonic contribution and the
formula's overall hedonic harmony — whether materials work together
to create a pleasant impression or clash hedonically.

Hedonic contrast (juxtaposing pleasant/unpleasant elements) is a
legitimate creative tool — Muscs Koublaï Khän (Lutens), Secretions
Magnifiques (ELDO) — but must be intentional, not accidental.

Sources:
  Khan et al. (2007) J Neurosci, 27(37), 10015-10023 — predicting odor pleasantness from structure
  Zarzo (2011) Sensors, 11(5), 5296-5322 — molecular descriptors and pleasantness
  Dravnieks (1985) Atlas of Odor Character Profiles — 146 odorant profiles
  Keller et al. (2007) Nature, 449(7161), 468-472 — OR7D4 individual variation
  Yeshurun & Sobel (2010) Annual Review Psych — perception of smell
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# ═══════════════════════════════════════════════════════════════════════════════
# Hedonic Valence Data
# Scale: -1.0 (maximally unpleasant) to +1.0 (maximally pleasant)
# Based on Khan (2007) PNAS model outputs, Dravnieks (1985) atlas values,
# and Arctander (1969) subjective descriptors cross-referenced
# ═══════════════════════════════════════════════════════════════════════════════

HEDONIC_VALENCE: dict[str, float] = {
    # ── Universally pleasant (vanillic, floral, fruity) ──
    "Vanillin":               0.90,
    "Ethyl Vanillin":         0.88,
    "Heliotropal": 0.85,  # neat piperonal
    "Linalool":               0.82,
    "Linalyl Acetate":        0.80,
    "Hedione":                0.78,
    "Phenethyl Alcohol":      0.82,
    "Benzyl Acetate":         0.75,
    "Jessemal":              0.45,
    "Coumarin":               0.80,
    "Maple Lactone":          0.85,
    "Gamma Decalactone":      0.83,
    "Gamma Undecalactone":    0.80,
    "Delta Decalactone":      0.78,
    "Raspberry Ketone":       0.80,
    # ── Pleasant florals ──
    "DBCA":                   0.75,
    "Lilyreal ND":            0.70,
    "Bourgeonal":             0.68,
    "Hydroxycitronellal":     0.72,
    "Nympheal":               0.70,
    "Florol":                 0.72,
    "Freesia HDI":            0.70,
    "Orivone":                0.65,
    "Ultralia":               0.60,
    "Methyl Ionone Pure":     0.72,
    "Alpha Ionone":           0.68,
    "Beta Ionone":            0.70,
    "Alpha Irone":            0.65,
    "Cis Jasmone":            0.65,
    # ── Pleasant woody/amber ──
    "Iso E Super":            0.55,
    "Javanol":                0.72,
    "Ebanol":                 0.68,
    "Ambrox Super":           0.60,
    "Cashmeran":              0.65,
    "Vertofix Coeur":         0.55,
    "Amberwood F":            0.60,
    "Timberol":               0.50,
    "Kephalis":               0.45,  # powerful, but less intrinsically pleasant
    "Koavone":                0.55,
    "Cedroxyde":              0.50,
    # ── Pleasant musks ──
    "Galaxolide":             0.70,
    "Habanolide":             0.72,
    "Ethylene Brassylate":    0.70,
    "Exaltolide":             0.75,
    "Musk Ketone":            0.65,
    "Ambretone":              0.68,
    # ── Pleasant citrus ──
    "D-Limonene":             0.75,
    "Bergamot FCF":           0.78,
    "Bergamot FCF Sicilian":  0.80,
    "Cedrat FCF Sicilian":    0.72,
    "Blood Orange Sicilian":  0.80,
    "Grapefruit FCF":         0.73,
    "Red Mandarin EO":        0.82,
    "Methyl Pamplemousse":    0.68,
    "Neroli EO":              0.80,
    "Petitgrain EO":          0.72,
    "Aldehyde C10":           0.40,  # pleasant in context, raw = waxy
    "Aldehyde C11":           0.38,
    "Aldehyde C11 Undecylenic": 0.35,
    "Aldehyde C12 MNA":       0.42,
    "Cyclamen Aldehyde":      0.45,
    "Scentenal":              0.30,  # metallic — polarizing
    "Calone":                 0.35,  # marine — polarizing
    "Floralozone":            0.40,
    "Dihydromyrcenol":        0.55,
    # ── Green (fresh but sharp) ──
    "cis-3-Hexenol":          0.50,
    "Parmavert":              0.55,
    "Leafovert":              0.45,
    "Dynascone":              0.30,  # powerful green bomb, unpleasant neat
    "Allyl Amyl Glycolate":   0.50,
    # ── Spice (context-dependent) ──
    "Eugenol":                0.45,
    "Ethyl Safranate":        0.55,
        "Cardamom EO":            0.65,  # natural EO, more aromatic complexity than FTEC
    "Terpinyl Acetate":       0.55,
    # ── Leather / smoke (acquired taste) ──
    "Suederal":               0.30,
    "Evernyl":                0.35,
    "Birch Tar Rectified":    0.10,  # smoky — divisive
    "Guaiacol":               0.15,  # medicinal neat, beautiful in traces
    "Isobutyl Quinoline":     0.05,  # dirty leather — negative neat
    "Styrax FTEC":            0.25,
    # ── Animalic (negative neat, positive in traces) ──
    "Indole":                -0.20,  # fecal neat, jasmine in traces
    # ── Balsamic ──
    "Benzoin Resinoid":       0.70,
    "Labdanum Absolute":      0.50,
    "Olibanum Resinoid":      0.55,
    "Myrrh EO":               0.45,
    # ── EOs ──
    "Lavender EO":            0.75,
    "Lavender EO (BONTAUX SAS)": 0.78,  # premium French angustifolia, less camphoraceous
    "Clary Sage EO":          0.50,
    "Rosemary EO (French Rosmarinus Officinalis leaf oil)": 0.55,
    "Vetiver EO":             0.45,
    "Vetiver EO (India)":     0.50,  # deeper, richer ruh khus character
    "Patchouli EO":           0.42,
    "Cedarwood EO":           0.55,
    "Champaca Flower EO":     0.60,
    "Ylang Comoros Complete EO": 0.65,
    "Ylang Comoros III EO":   0.68,
    "Carrot Seed EO":         0.30,
    # ── Fruity ──
    "Paradisamide":           0.65,
    # ── Misc ──
    "Hexyl Salicylate":       0.60,
    "Benzyl Salicylate":      0.55,
    "Vetival":                0.40,
    "Salicylate FTEC":        0.55,
    # ── Coverage additions (Perfume A materials) ──
    "Romandolide":            0.68,  # clean woody-musk, pleasant
    "Benzyl Benzoate":        0.35,  # near-odorless fixative, faint balsamic
    "Hedione HC":             0.78,  # same hedonic as Hedione, high-cis variant
    "Dihydro Beta Ionone":    0.62,  # soft woody-violet, pleasant
    "Sandalore":              0.70,  # fresh-creamy sandalwood
    "Clearwood":              0.50,  # clean patchouli replacement, earthy
    "Zenolide":               0.65,  # clean citrusy-fresh musk
    "Vertofix":               0.55,  # woody-musky, amber-cedarwood fixative
    "Bacdanol":               0.70,  # milky round sandalwood
    "Dihydrojasmone":         0.60,  # creamy jasmine-fruity
    "Methyl Nonyl Ketone":    0.30,  # waxy, green-fatty
    "Helional":               0.62,  # green-floral aquatic, heliotrope facet
    "Norlimbanol Dextro":     0.50,  # powerful transparent woody
    "Ambrofix":               0.60,  # smooth ambergris-amber
    "Ambermax":               0.65,  # warm rounded amber
    "Aurantiol":              0.72,  # orange-blossom hydroxycitronellal type
    "Anisaldehyde":           0.60,  # sweet aniseed-hawthorn
    "Macrolide":              0.65,  # soft clean musk
    "Ylang III":              0.65,  # heavy floral, balsamic ylang
    "Ethyl Maltol":           0.85,  # sweet cotton-candy caramel
    "Rose Oxide":             0.72,  # rose-lychee, pleasant floral
    "Damascenone":            0.75,  # rose-ketone, powerful pleasant
}


# ═══════════════════════════════════════════════════════════════════════════════
# Scoring
# ═══════════════════════════════════════════════════════════════════════════════

def evaluate_targeted_hedonics(
    ingredients_ul: dict[str, float], *, target: dict,
    evidence: dict[str, dict] | None = None,
    concentrations_ppm: dict[str, float] | None = None,
    context: str | None = None,
) -> dict:
    """Separate composition constraints, experimental liking and coverage.

    Exact names denote resolved stimulus identities. Context must bind matrix,
    temperature, time, concentration basis and cohort. No aliasing, invented
    ppm, or imputation from HEDONIC_VALENCE occurs here. Raw uL serve only the
    caller's design constraints, never perceived contribution.
    The optional binary estimate uses intensity-weighted intermediacy:
    Lapid et al. 2008, doi:10.1093/chemse/bjn026. Coverage is not validation.
    """
    amounts = {k: float(v) for k, v in ingredients_ul.items()}
    if (not amounts or any(not math.isfinite(v) or v < 0 for v in amounts.values())
            or sum(amounts.values()) <= 0):
        raise ValueError("Formula needs finite nonnegative amounts and positive total")
    allowed = {"required", "minimum_ul", "maximum_ratios"}
    if not target or set(target) - allowed:
        raise ValueError("Explicit target required; unsupported target fields")
    violations = []
    checks = 0
    for name in target.get("required", []):
        checks += 1
        if amounts.get(name, 0.) <= 0:
            violations.append({"kind": "required_anchor_missing", "material": name})
    for name, minimum in target.get("minimum_ul", {}).items():
        minimum = float(minimum)
        if not math.isfinite(minimum) or minimum <= 0:
            raise ValueError("Minimum amount must be finite and positive")
        checks += 1
        if amounts.get(name, 0.) < minimum:
            violations.append({"kind": "anchor_below_design_floor", "material": name,
                               "minimum_ul": minimum, "actual_ul": amounts.get(name, 0.)})
    for constraint in target.get("maximum_ratios", []):
        numerator, denominator = constraint["numerator"], constraint["denominator"]
        maximum = float(constraint["maximum"])
        if numerator == denominator or not math.isfinite(maximum) or maximum < 0:
            raise ValueError("Invalid ratio constraint")
        checks += 1
        den = amounts.get(denominator, 0.)
        ratio = amounts.get(numerator, 0.) / den if den > 0 else None
        if ratio is None or ratio > maximum:
            violations.append({"kind": "accent_ratio_exceeded", "numerator": numerator,
                               "denominator": denominator, "maximum": maximum,
                               "actual": ratio})
    if not checks:
        raise ValueError("At least one explicit target constraint is required")

    active_names = [name for name, value in amounts.items() if value > 0]
    evidence = evidence or {}
    concentrations_ppm = concentrations_ppm or {}
    matched, unmatched = {}, {}
    for name in active_names:
        row = evidence.get(name)
        reason = None
        if not row:
            reason = "missing_evidence"
        elif not isinstance(row.get("source"), str) or not row["source"].strip():
            reason = "missing_provenance"
        elif not context or row.get("context") != context:
            reason = "context_mismatch"
        elif name not in concentrations_ppm:
            reason = "missing_concentration"
        else:
            try:
                observed_ppm = float(row["concentration_ppm"])
                requested_ppm = float(concentrations_ppm[name])
                intensity = float(row["intensity"])
                pleasantness = float(row["pleasantness"])
                if (not all(math.isfinite(x) for x in
                            (observed_ppm, requested_ppm, intensity, pleasantness))
                        or observed_ppm <= 0 or requested_ppm <= 0
                        or intensity < 0 or not 0 <= pleasantness <= 100):
                    reason = "invalid_observation"
                elif not math.isclose(observed_ppm, requested_ppm, rel_tol=1e-9, abs_tol=0.):
                    reason = "concentration_mismatch"
                else:
                    matched[name] = {"intensity": intensity, "pleasantness": pleasantness,
                                     "source": row["source"]}
            except (KeyError, TypeError, ValueError):
                reason = "invalid_observation"
        if reason:
            unmatched[name] = reason

    liking = {"status": "EVIDENCE_UNAVAILABLE", "score": None,
              "model": "intensity_weighted_binary_intermediacy",
              "source": "https://doi.org/10.1093/chemse/bjn026",
              "context": context, "sensory_validated": False}
    if not unmatched:
        if len(active_names) != 2:
            liking["status"] = "OUT_OF_MODEL_SCOPE"
        else:
            intensity_sum = sum(row["intensity"] for row in matched.values())
            if intensity_sum > 0:
                liking.update(status="EXPERIMENTAL_ESTIMATE", score=sum(
                    row["intensity"] * row["pleasantness"] for row in matched.values()
                ) / intensity_sum)
            else:
                liking["status"] = "NO_POSITIVE_INTENSITY"
    return {
        "target_identity": {
            "status": "FAIL_DESIGN_CONSTRAINTS" if violations else "PASS_DESIGN_CONSTRAINTS",
            "basis": "CALLER_DECLARED_COMPOSITION_CONSTRAINTS_NOT_PERCEPTUAL_THRESHOLDS",
            "perceptual_fit": "NOT_ESTABLISHED", "violations": violations,
        },
        "predicted_liking": liking,
        "confidence": {
            "matched_material_fraction": len(matched) / len(active_names),
            "matched_material_count": len(matched), "material_count": len(active_names),
            "unmatched": unmatched, "sources": sorted({row["source"] for row in matched.values()}),
            "model_validation": "NOT_VALIDATED_FOR_THIS_FORMULA",
            "population_to_individual_transfer": "NOT_ESTABLISHED",
        },
        "optimization_eligible": False,
        "requires_premix_trial": False,
        "claim_scope": "COMPUTATIONAL_DESIGN_ONLY",
    }


def expand_natural_scenario(
    candidate: dict[str, float], structures: dict[str, str],
    natural_profiles: dict[str, list[dict]], nominal_volume_ul: float,
    multipliers: dict[str, float] | None = None,
) -> dict:
    """Expand a nominal constituent scenario without inventing missing coverage.

    Input fractions are composition proxies, not lot assays, density-corrected
    mass fractions, or vapor concentrations. Molecular entries are canonicalized
    and combined across stocks before model feature extraction. Unknown stocks,
    missing structures, and unreported profile residual remain unresolved.
    """
    from collections.abc import Mapping

    from rdkit import Chem

    def number(value, *, positive=False):
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0 or (positive and value == 0)):
            raise ValueError("Finite nonnegative values, or positive scales/volume, required")
        return float(value)

    if (not isinstance(candidate, Mapping) or not isinstance(structures, Mapping)
            or not isinstance(natural_profiles, Mapping)
            or set(structures) & set(natural_profiles)):
        raise ValueError("Distinct direct and natural stock mappings required")
    if any(not isinstance(n, str) or not n.strip() for n in candidate):
        raise ValueError("Nonempty stock names required")
    scales = {} if multipliers is None else multipliers
    if not isinstance(scales, Mapping):
        raise ValueError("Constituent multiplier mapping required")
    for name, value in scales.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Nonempty constituent names required")
        number(value, positive=True)
    constituent_names = {
        row.get("name") for profile in natural_profiles.values()
        if isinstance(profile, (list, tuple)) for row in profile
        if isinstance(row, Mapping) and isinstance(row.get("name"), str)
    }
    if set(scales) - constituent_names:
        raise ValueError("Unknown constituent multiplier: "
                         + ", ".join(sorted(set(scales) - constituent_names)))
    volume = number(nominal_volume_ul, positive=True)
    amounts = {n: number(v) for n, v in candidate.items()}
    total = math.fsum(amounts.values())
    if not math.isfinite(total) or total > volume:
        raise ValueError("Stock total exceeds nominal finished volume")
    molecular_amounts, coverage = {}, {}

    def add(smiles, amount):
        if not isinstance(smiles, str) or not smiles.strip():
            raise ValueError("Nonempty molecular SMILES required")
        molecule = Chem.MolFromSmiles(smiles.strip())
        if molecule is None or molecule.GetNumHeavyAtoms() == 0:
            raise ValueError("Invalid constituent molecular structure")
        canonical = Chem.MolToSmiles(molecule, isomericSmiles=True)
        molecular_amounts.setdefault(canonical, []).append(amount)

    for stock in sorted(amounts):
        amount = amounts[stock]
        if amount == 0:
            continue
        modeled_fraction, reported_fraction = 0., 0.
        if stock in structures:
            add(structures[stock], amount)
            modeled_fraction = reported_fraction = 1.
        elif stock in natural_profiles:
            profile = natural_profiles[stock]
            if not isinstance(profile, (list, tuple)):
                raise ValueError("Natural profile must be a constituent list")
            entries = []
            for entry in profile:
                if (not isinstance(entry, Mapping) or not isinstance(entry.get("name"), str)
                        or not entry["name"].strip()):
                    raise ValueError("Named natural constituents required")
                fraction = number(entry.get("fraction")) * scales.get(entry["name"], 1.)
                if not math.isfinite(fraction):
                    raise ValueError("Nonfinite perturbed fraction")
                entries.append((entry.get("smiles"), fraction))
            reported_fraction = math.fsum(fraction for _, fraction in entries)
            if reported_fraction > 1.:
                raise ValueError("Perturbed natural composition exceeds unity")
            known = []
            for smiles, fraction in entries:
                if fraction > 0 and smiles is not None:
                    add(smiles, amount * fraction)
                    known.append(fraction)
            modeled_fraction = math.fsum(known)
        coverage[stock] = {
            "raw_ul": amount, "modeled_fraction": modeled_fraction,
            "reported_fraction": reported_fraction,
            "unresolved_fraction": 1. - modeled_fraction,
            "modeled_raw_equivalent_ul": amount * modeled_fraction,
            "unresolved_raw_equivalent_ul": amount * (1. - modeled_fraction),
        }
    modeled = math.fsum(row["modeled_raw_equivalent_ul"] for row in coverage.values())
    unresolved = math.fsum(row["unresolved_raw_equivalent_ul"] for row in coverage.values())
    return {
        "components": [{"smiles": smiles,
                        "nominal_fraction": math.fsum(parts) / volume}
                       for smiles, parts in sorted(molecular_amounts.items())],
        "modeled_raw_equivalent_ul": modeled,
        "unresolved_raw_equivalent_ul": unresolved,
        "per_stock_coverage": coverage, "nominal_volume_ul": volume,
        "basis": "NOMINAL_COMPOSITION_PROXY_NOT_EXACT_MASS",
        "unresolved_residual_renormalized": False,
    }


def pareto_minimize(records: list[dict], vector_key: str = "loss_vector") -> list[dict]:
    """Keep original nondominated records; every finite vector axis is minimized.

    Ties survive in input order. This arithmetic ordering neither estimates
    uncertainty nor supplies sensory, formulation, or release authority.
    """
    from collections.abc import Mapping

    vectors = []
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("Records with a consistent loss vector required")
        vector = record.get(vector_key)
        if (not isinstance(vector, (list, tuple)) or not vector
                or (vectors and len(vector) != len(vectors[0]))
                or any(isinstance(v, bool) or not isinstance(v, (int, float))
                       or not math.isfinite(v) for v in vector)):
            raise ValueError("Finite nonempty loss vectors of equal dimension required")
        vectors.append(tuple(float(v) for v in vector))
    return [record for i, record in enumerate(records) if not any(
        all(a <= b for a, b in zip(other, vectors[i]))
        and any(a < b for a, b in zip(other, vectors[i]))
        for other in vectors)]


def evaluate_design_roles(
    ingredients_ul: dict[str, float], *, baseline: dict[str, float],
    profiles: dict[str, dict], context: str,
) -> dict:
    """Trace changed stock amounts to sourced roles, without a liking model.

    Role labels describe materials, not predicted mixture contributions. Their
    presence is not an intensity weight, pairwise synergy or dose response.
    Raw amounts describe changes only; no mass, ppm or OAV is imputed here.
    """
    amounts = {k: float(v) for k, v in ingredients_ul.items()}
    parent = {k: float(v) for k, v in baseline.items()}
    if (not context or not amounts or set(amounts) != set(parent)
            or any(not math.isfinite(v) or v < 0 for v in (*amounts.values(), *parent.values()))
            or not math.isclose(sum(amounts.values()), sum(parent.values()), abs_tol=1e-9)
            or sum(parent.values()) <= 0):
        raise ValueError("Same finite stock set and constant positive raw total required")
    increased, decreased, missing, sources = {}, {}, [], set()
    for name in sorted(amounts):
        profile = profiles.get(name, {})
        roles, refs = profile.get("roles"), profile.get("sources")
        valid = (isinstance(roles, list) and bool(roles)
                 and isinstance(refs, list) and bool(refs)
                 and all(isinstance(x, str) and x.strip() for x in (*roles, *refs)))
        if not valid:
            missing.append(name)
            continue
        sources.update(refs)
        if amounts[name] > parent[name]:
            increased[name] = list(roles)
        elif amounts[name] < parent[name]:
            decreased[name] = list(roles)
    return {
        "basis": "qualitative_hypothesis", "context": context,
        "sources": sorted(sources), "loss_intervals": None,
        "increased_material_roles": increased, "decreased_material_roles": decreased,
        "missing_profiles": missing, "dose_ranking_authorized": False,
        "predicted_liking": None, "perceived_richness": None, "perceived_layering": None,
        "claim_scope": "MATERIAL_ROLE_HYPOTHESIS_NOT_MIXTURE_PREDICTION",
    }


def structural_design_losses(report: dict, objectives: dict[str, float]) -> dict[str, float]:
    """Opt into caller-defined structural proxies without inventing liking.

    Constraints remain hard; missing liking is independent of design search.
    Objective definitions, scales and provenance belong to the frozen evaluator.
    These losses do not establish perceived body, temporal behavior or preference.
    """
    identity = report["target_identity"]
    if identity["status"] != "PASS_DESIGN_CONSTRAINTS" or identity["violations"]:
        raise ValueError("Hard target constraints violated")
    values = {name: float(value) for name, value in objectives.items()}
    if not values or any(not math.isfinite(v) or v < 0 for v in values.values()):
        raise ValueError("Explicit finite nonnegative structural objectives required")
    return values


def targeted_hedonic_losses(report: dict, *, allow_experimental: bool = False) -> dict[str, float]:
    """Expose experimental losses only by explicit opt-in, never impute gaps.

    The search result remains a computational hypothesis. Opt-in does not
    establish model validation, sensory preference, or full-perfume coverage.
    """
    liking = report["predicted_liking"]
    score = liking.get("score")
    if (allow_experimental and liking["status"] == "EXPERIMENTAL_ESTIMATE"
            and isinstance(score, (int, float)) and math.isfinite(score)
            and 0 <= score <= 100):
        return {"identity": float(len(report["target_identity"]["violations"])),
                "liking": 100. - score}
    raise ValueError("Targeted liking evaluator not admitted for optimization: "
                     + str(liking["status"]))


@dataclass
class HedonicReport:
    """Legacy fixed-valence diagnostic for a formula.

    ``score`` and ``pleasantness_class`` are retained for backwards
    compatibility.  They describe only the exact-name materials represented
    in :data:`HEDONIC_VALENCE`; they are not measured full-formula
    pleasantness or liking endpoints.  The coverage and authority fields make
    that ceiling explicit for every caller, including zero- and partial-table
    coverage.
    """
    score: float                      # 0-100 hedonic score
    weighted_valence: float           # -1.0 to 1.0 weighted mean
    pleasantness_class: str           # "highly_pleasant", "pleasant", etc.
    hedonic_contrast: float           # 0-1 how much contrast between materials
    pleasant_fraction: float          # 0-1 fraction of rated active mass that is pleasant
    unpleasant_materials: list[dict]  # materials with negative valence
    most_pleasant: list[dict]         # top 5 by hedonic contribution
    diagnostics: list[str]
    rated_active_fraction: float = 0.0
    unrated_active_fraction: float = 0.0
    rated_materials: list[str] = field(default_factory=list)
    unrated_materials: list[str] = field(default_factory=list)
    coverage_status: str = "ZERO_TABLE_COVERAGE"
    classification: str = "HEURISTIC_DIAGNOSTIC_INDEX"
    ranking_status: str = "WITHHELD"
    formula_optimization_authority: bool = False
    sensory_validation_status: str = "NOT_ESTABLISHED"
    full_formula_pleasantness_status: str = "NOT_ESTABLISHED"
    pleasantness_class_scope: str = "FIXED_VALENCE_TABLE_SUBSET_ONLY"


def score_hedonic(
    ingredients: dict[str, float],
    dilutions: dict[str, float] | None = None,
) -> HedonicReport:
    """Compute the legacy fixed-valence diagnostic for a formula.

    High score = rated table labels converge on pleasant valence.
    Low score  = rated negative-valence labels OR high table contrast.

    Moderate hedonic contrast is artistically valid (chypre, leather,
    animalic accords) but reduces the hedonic score.
    """
    dilutions = dilutions or {}
    total_active = 0.0
    rated_active = 0.0
    weighted_sum = 0.0
    valence_list: list[float] = []
    weight_list: list[float] = []
    pleasant_mass = 0.0
    unpleasant_mats: list[dict] = []
    material_scores: list[dict] = []
    diagnostics: list[str] = []
    rated_materials: list[str] = []
    unrated_materials: list[str] = []

    for name, amount in ingredients.items():
        dil = dilutions.get(name, 1.0)
        active = amount * dil
        total_active += active

        valence = HEDONIC_VALENCE.get(name)
        if valence is None:
            if active > 0:
                unrated_materials.append(name)
            continue

        if active > 0:
            rated_materials.append(name)
        rated_active += active
        weighted_sum += valence * active
        valence_list.append(valence)
        weight_list.append(active)

        material_scores.append({
            "material": name,
            "valence": valence,
            "amount_uL": round(active, 1),
            "hedonic_contribution": round(valence * active, 1),
        })

        if valence >= 0.3:
            pleasant_mass += active
        elif valence < 0.0:
            unpleasant_mats.append({
                "material": name,
                "valence": valence,
                "amount_uL": round(active, 1),
            })

    rated_active_fraction = rated_active / total_active if total_active > 0 else 0.0
    unrated_active_fraction = (
        (total_active - rated_active) / total_active if total_active > 0 else 0.0
    )
    if total_active <= 0:
        coverage_status = "NO_ACTIVE_MATERIALS"
    elif rated_active <= 0:
        coverage_status = "ZERO_TABLE_COVERAGE"
    elif math.isclose(rated_active, total_active, rel_tol=1e-12, abs_tol=1e-12):
        coverage_status = "FULL_TABLE_COVERAGE"
    else:
        coverage_status = "PARTIAL_TABLE_COVERAGE"

    if total_active <= 0 or rated_active <= 0:
        missing = ", ".join(unrated_materials) if unrated_materials else "none"
        return HedonicReport(
            score=50, weighted_valence=0, pleasantness_class="unknown",
            hedonic_contrast=0, pleasant_fraction=0,
            unpleasant_materials=[], most_pleasant=[],
            diagnostics=[
                "No hedonic data",
                f"Hedonic table coverage: {coverage_status}; unrated labels: {missing}",
                "HEURISTIC_DIAGNOSTIC_INDEX only: the legacy score=50 fallback is not measured full-formula pleasantness or liking.",
            ],
            rated_active_fraction=rated_active_fraction,
            unrated_active_fraction=unrated_active_fraction,
            rated_materials=rated_materials,
            unrated_materials=unrated_materials,
            coverage_status=coverage_status,
        )

    # Weighted mean valence (over rated materials only — unrated are excluded,
    # not penalised as valence=0)
    mean_valence = weighted_sum / rated_active

    # Hedonic contrast: weighted standard deviation
    var_sum = sum(w * (v - mean_valence) ** 2
                  for v, w in zip(valence_list, weight_list))
    contrast = math.sqrt(var_sum / rated_active)

    # Pleasant fraction (of rated mass)
    pleas_frac = pleasant_mass / rated_active

    # Classification
    if mean_valence > 0.7:
        pclass = "highly_pleasant"
    elif mean_valence > 0.5:
        pclass = "pleasant"
    elif mean_valence > 0.3:
        pclass = "moderately_pleasant"
    elif mean_valence > 0.0:
        pclass = "neutral"
    elif mean_valence > -0.2:
        pclass = "challenging"
    else:
        pclass = "discordant"

    # Score: map mean_valence from [-1, 1] to [0, 100]
    # With bonus for coherence and penalty for contrast
    base = (mean_valence + 1.0) / 2.0 * 80  # 0-80 from valence
    coherence_bonus = max(0, (1.0 - contrast) * 20)  # 0-20 from low contrast
    score = base + coherence_bonus
    score = max(0, min(100, score))

    # Sort for top 5
    material_scores.sort(key=lambda x: x["hedonic_contribution"], reverse=True)

    # Diagnostics
    diagnostics.append(f"Hedonic class: {pclass} (mean valence {mean_valence:+.2f})")
    if contrast > 0.3:
        diagnostics.append(
            f"⚠ High hedonic contrast ({contrast:.2f}) — "
            "pleasant/unpleasant elements in tension"
        )
    if unpleasant_mats:
        names = [f"{m['material']} ({m['valence']:+.2f})" for m in unpleasant_mats]
        diagnostics.append(f"Hedonically negative: {', '.join(names)}")
    if pleas_frac > 0.8:
        diagnostics.append("✓ >80% of rated active mass has positive table valence")
    if coverage_status == "PARTIAL_TABLE_COVERAGE":
        diagnostics.append(
            "Hedonic table coverage is partial: score, class, and pleasant fraction apply only to rated labels; full-formula pleasantness is NOT_ESTABLISHED."
        )
    diagnostics.append(
        "HEURISTIC_DIAGNOSTIC_INDEX only: fixed material valences are not measured full-formula pleasantness or liking."
    )

    return HedonicReport(
        score=round(score, 1),
        weighted_valence=round(mean_valence, 3),
        pleasantness_class=pclass,
        hedonic_contrast=round(contrast, 3),
        pleasant_fraction=round(pleas_frac, 3),
        unpleasant_materials=unpleasant_mats,
        most_pleasant=material_scores[:5],
        diagnostics=diagnostics,
        rated_active_fraction=rated_active_fraction,
        unrated_active_fraction=unrated_active_fraction,
        rated_materials=rated_materials,
        unrated_materials=unrated_materials,
        coverage_status=coverage_status,
    )
