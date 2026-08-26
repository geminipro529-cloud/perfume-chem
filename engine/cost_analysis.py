"""Cost-of-Goods Reverse Engineering — Price constrains material selection.

Working backwards from retail price to estimate the perfume oil budget,
then checking whether a hypothesized formula fits within that budget.

Industry cost structure (luxury niche):
    Retail Price → Wholesale (50%) → Distribution (30%) → COG (20%)
    COG = raw materials + compounding + packaging
    Raw materials typically 40-60% of COG

This module estimates whether specific expensive naturals (orris, oud,
rose, jasmine) are economically plausible at their hypothesized doses.
"""

from __future__ import annotations

from dataclasses import dataclass

# ── Material Cost Database ──────────────────────────────────────────
# Approximate costs in USD per kg (industry bulk, not retail hobby)
# Sources: Firmenich/Givaudan/IFF catalog ranges, trade publications

MATERIAL_COSTS_PER_KG: dict[str, float] = {
    # Precious naturals
    "orris concrete":           50000.0,
    "orris absolute":           80000.0,
    "alpha irone (natural)":    30000.0,
    "rose absolute":            8000.0,
    "rose otto":                6000.0,
    "jasmine absolute":         10000.0,
    "jasmine sambac absolute":  12000.0,
    "oud oil":                  25000.0,    # Plantation grade
    "oud oil (wild)":           80000.0,    # Wild Aquilaria
    "neroli eo":                4500.0,
    "tuberose absolute":        15000.0,
    "ambergris tincture":       30000.0,
    "civet absolute":           20000.0,

    # Quality naturals
    "bergamot eo":              150.0,
    "bergamot fcf":             180.0,
    "lavender eo":              120.0,
    "lavender eo (bontaux sas)": 180.0,
    "cardamom eo":              350.0,
    "patchouli eo":             100.0,
    "vetiver eo":               200.0,
    "vetiver eo (india)":       280.0,
    "cedarwood eo":             30.0,
    "frankincense eo":          120.0,
    "labdanum":                 250.0,
    "benzoin resinoid":         80.0,
    "myrrh eo":                 300.0,

    # Synthetic workhorses
    "hedione":                  40.0,
    "hedione hc":               120.0,
    "iso e super":              25.0,
    "benzyl salicylate":        15.0,
    "hexyl salicylate":         30.0,
    "galaxolide":               35.0,
    "habanolide":               180.0,      # Firmenich captive
    "ambrox super":             600.0,      # Ambroxide
    "ambrox dl":                400.0,
    "coumarin":                 20.0,
    "vanillin":                 12.0,
    "ethyl vanillin":           25.0,
    "alpha-isomethyl ionone":   60.0,
    "alpha irone (synthetic)":  800.0,
    "alpha ionone":             80.0,
    "beta ionone":              90.0,
    "methyl ionone gamma":      70.0,
    "orivone":                  200.0,
    "hydroxycitronellal":       25.0,
    "linalool":                 20.0,
    "linalyl acetate":          18.0,
    "citronellol":              22.0,
    "geraniol":                 25.0,
    "eugenol":                  15.0,
    "indole":                   120.0,
    "cis-jasmone":              250.0,
    "benzyl acetate":           12.0,
    "jessemal":                200.0,
    "guaiacol":                 30.0,
    "cashmeran":                150.0,
    "d-limonene":               8.0,
    "benzyl benzoate":          10.0,
    "benzyl alcohol":           8.0,
    "farnesol":                 60.0,
    "ibq":                      80.0,
    "suederal":                 200.0,
    "vertofix coeur":           60.0,
    "phenethyl alcohol":        30.0,
    "dihydro beta ionone":      100.0,
    "irotyl":                   150.0,
    "carrot seed eo":           200.0,
    "ultralia":                 120.0,
    "rose oxide":               200.0,
    "maple lactone":            40.0,
    "ethylene brassylate":      50.0,
}


# ── Price Tier Models ───────────────────────────────────────────────

@dataclass
class PriceTier:
    """Industry pricing model for different market segments."""
    name: str
    retail_per_100ml: tuple[float, float]    # Low-high retail USD
    cog_fraction: float                       # COG as fraction of wholesale
    raw_material_fraction: float              # Raw mats as fraction of COG
    concentrate_fraction: float               # Concentrate % (EDP default)

PRICE_TIERS: dict[str, PriceTier] = {
    "mass_market": PriceTier(
        name="Mass Market (Designer)",
        retail_per_100ml=(50.0, 150.0),
        cog_fraction=0.25,
        raw_material_fraction=0.40,
        concentrate_fraction=0.15,
    ),
    "premium_designer": PriceTier(
        name="Premium Designer",
        retail_per_100ml=(100.0, 250.0),
        cog_fraction=0.22,
        raw_material_fraction=0.45,
        concentrate_fraction=0.20,
    ),
    "luxury_niche": PriceTier(
        name="Luxury Niche",
        retail_per_100ml=(200.0, 500.0),
        cog_fraction=0.20,
        raw_material_fraction=0.50,
        concentrate_fraction=0.25,
    ),
    "ultra_luxury": PriceTier(
        name="Ultra Luxury / Bespoke",
        retail_per_100ml=(400.0, 2000.0),
        cog_fraction=0.18,
        raw_material_fraction=0.55,
        concentrate_fraction=0.25,
    ),
}


@dataclass
class MaterialCostEstimate:
    """Cost analysis for a single material in the formula."""
    material: str
    concentration_pct: float    # % of concentrate
    cost_per_kg: float
    cost_per_bottle: float      # USD per 100 mL bottle
    fraction_of_budget: float   # What fraction of raw material budget this uses
    plausible: bool             # Does this fit the budget?


@dataclass
class COGAnalysisResult:
    """Complete cost-of-goods analysis for a fragrance."""
    target_name: str
    retail_price: float
    tier: str
    wholesale_price: float
    cog_estimate: float
    raw_material_budget: float       # USD per 100 mL for raw materials
    concentrate_volume_ml: float     # mL of concentrate per 100 mL bottle
    material_costs: list[MaterialCostEstimate]
    total_formula_cost: float        # Estimated total raw material cost
    budget_utilization: float        # total / budget (should be ≤ 1.0)
    implausible_materials: list[str] # Materials that break the budget
    score: float                     # 0–100: economic plausibility


def analyze_cost_of_goods(
    target_name: str,
    retail_price_100ml: float,
    materials_pct: dict[str, float],
    tier: str = "luxury_niche",
    concentrate_pct: float = 25.0,
) -> COGAnalysisResult:
    """Analyze whether a hypothesized formula is economically plausible.

    Args:
        target_name: Fragrance name.
        retail_price_100ml: Retail price per 100 mL in USD.
        materials_pct: Material → % of concentrate.
        tier: Pricing tier key from PRICE_TIERS.
        concentrate_pct: EDP concentration (default 25%).

    Returns:
        COGAnalysisResult with per-material costs and plausibility score.
    """
    price_model = PRICE_TIERS.get(tier, PRICE_TIERS["luxury_niche"])

    wholesale = retail_price_100ml * 0.50
    cog = wholesale * price_model.cog_fraction
    raw_budget = cog * price_model.raw_material_fraction
    conc_ml = 100.0 * (concentrate_pct / 100.0)  # mL of concentrate per bottle
    conc_g = conc_ml  # Assume density ≈ 1.0 g/mL

    costs: list[MaterialCostEstimate] = []
    total_cost = 0.0
    implausible: list[str] = []

    for mat, pct in sorted(materials_pct.items()):
        mat_key = mat.lower().strip()
        cost_kg = MATERIAL_COSTS_PER_KG.get(mat_key, 50.0)  # default $50/kg

        # Grams of this material per 100 mL bottle
        grams = conc_g * (pct / 100.0)
        cost_per_bottle = grams * (cost_kg / 1000.0)
        fraction = cost_per_bottle / raw_budget if raw_budget > 0 else 0.0

        is_plausible = cost_per_bottle <= raw_budget * 0.5  # No single material > 50% of budget

        if not is_plausible:
            implausible.append(mat)

        costs.append(MaterialCostEstimate(
            material=mat,
            concentration_pct=pct,
            cost_per_kg=cost_kg,
            cost_per_bottle=cost_per_bottle,
            fraction_of_budget=fraction,
            plausible=is_plausible,
        ))
        total_cost += cost_per_bottle

    utilization = total_cost / raw_budget if raw_budget > 0 else 0.0

    # Score: 100 if formula fits budget perfectly, 0 if wildly over
    if utilization <= 1.0:
        score = 90.0 + (10.0 * (1.0 - utilization))  # Under budget = good
    elif utilization <= 1.5:
        score = 90.0 - ((utilization - 1.0) * 120.0)  # Slightly over
    elif utilization <= 2.0:
        score = max(20.0, 30.0 - ((utilization - 1.5) * 60.0))
    else:
        score = max(0.0, 20.0 - ((utilization - 2.0) * 20.0))

    return COGAnalysisResult(
        target_name=target_name,
        retail_price=retail_price_100ml,
        tier=tier,
        wholesale_price=wholesale,
        cog_estimate=cog,
        raw_material_budget=raw_budget,
        concentrate_volume_ml=conc_ml,
        material_costs=costs,
        total_formula_cost=total_cost,
        budget_utilization=utilization,
        implausible_materials=implausible,
        score=score,
    )
