"""Cross-reference competitor brands against project inventory and generate analysis.

Analyzes MITH Bangkok and Vibeslab competitor data, cross-references
materials against the project's inventory + odor database, and produces
comparison reports for gap analysis and formula development.

Usage:
    python scripts/competitor_analysis.py                          # default: compare both brands
    python scripts/competitor_analysis.py --brand mith              # MITH only
    python scripts/competitor_analysis.py --brand vibeslab          # Vibeslab only
    python scripts/competitor_analysis.py --json                    # JSON output to stdout
    python scripts/competitor_analysis.py --json --output results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.ingredient_intelligence import _PROFILES
from engine.inventory_parser import parse_inventory
from engine.odor_thresholds import ODT_DATA

# ---------------------------------------------------------------------------
# Data — extracted from competitor research
# ---------------------------------------------------------------------------

VibeslabBrand = "Vibeslab"
MITHBrand = "MITH Bangkok"


@dataclass
class CompetitorScent:
    name: str
    brand: str
    category: str
    price_50ml_thb: Optional[int] = None
    price_100ml_thb: Optional[int] = None
    notes: List[str] = field(default_factory=list)
    key_materials: List[str] = field(default_factory=list)
    perfumer: Optional[str] = None
    concentration: Optional[str] = "EDP"

    @property
    def price_per_ml_50(self) -> Optional[float]:
        if self.price_50ml_thb:
            return self.price_50ml_thb / 50.0
        return None

    @property
    def price_per_ml_100(self) -> Optional[float]:
        if self.price_100ml_thb:
            return self.price_100ml_thb / 100.0
        return None


COMPETITOR_SCENTS: List[CompetitorScent] = [
    # ---- MITH Bangkok ----
    CompetitorScent("Nude", MITHBrand, "Musky", 699, 2859,
                    notes=["Bergamot", "Pear", "Peach", "Violet Leaves", "Peony", "Lily-of-the-Valley",
                           "Vetiver", "Tonka Bean", "Moss", "Musk"],
                    key_materials=["Bergamot", "Pear", "Peach", "Violet leaf", "Peony", "Muguet",
                                   "Vetiver", "Tonka bean", "Oakmoss", "Musk"],
                    perfumer="Quentin Bisch"),
    CompetitorScent("Legend", MITHBrand, "Woody", 699, 2059,
                    notes=["Apple", "Galbanum", "Lemon", "Pepper", "Geranium", "Lily-of-the-Valley",
                           "Floral notes", "Cedarwood", "Incense", "Patchouli", "Benzoin", "Leather"],
                    key_materials=["Apple", "Galbanum", "Lemon", "Black pepper", "Geranium", "Muguet",
                                   "Cedarwood", "Incense", "Patchouli", "Benzoin", "Leather"],
                    perfumer="Alberto Morillas"),
    CompetitorScent("Fierce", MITHBrand, "Woody", 699, 2059,
                    notes=["Saffron", "Pepper", "Black Currant", "Raspberry",
                           "Rose", "Iris", "Violet", "Cedarwood", "Musk", "Leather"],
                    key_materials=["Saffron", "Black pepper", "Blackcurrant", "Raspberry",
                                   "Rose", "Iris", "Violet", "Cedarwood", "Musk", "Leather"]),
    CompetitorScent("Mantra", MITHBrand, "Musky", 699, 2059,
                    notes=["Pink Pepper", "Violet", "Orris", "Musk", "Amber"],
                    key_materials=["Pink pepper", "Violet", "Orris", "Musk", "Amber"],
                    perfumer="Elodie Durande"),
    CompetitorScent("Golden Rice", MITHBrand, "Gourmand", 699, 2059,
                    notes=["Roasted Almond", "Rice", "Rose", "Lily-of-the-Valley",
                           "Praline", "Musk", "Sandalwood", "Vanilla"],
                    key_materials=["Almond", "Rice", "Rose", "Muguet",
                                   "Praline", "Musk", "Sandalwood", "Vanilla"],
                    perfumer="Fabrice Pellegrin"),
    CompetitorScent("Memory of the Wind", MITHBrand, "Floral", 599, 1859,
                    notes=["Bergamot", "Apple", "Pimento Berry", "Violet", "Rose", "Freesia",
                           "Anise", "Oakmoss", "Cypress", "Musk", "Vetiver"],
                    key_materials=["Bergamot", "Apple", "Pimento berry", "Violet", "Rose", "Freesia",
                                   "Anise", "Oakmoss", "Cypress", "Musk", "Vetiver"],
                    perfumer="Quentin Bisch"),
    CompetitorScent("Golden Hour", MITHBrand, "Floral", 699, 2059, perfumer=None),
    CompetitorScent("Amethyst's Pollen", MITHBrand, "Floral", 599, 1859),
    CompetitorScent("Crystal Flower", MITHBrand, "Floral", None, None),
    CompetitorScent("Love", MITHBrand, "Floral", None, None),
    CompetitorScent("Philosophy of Zen", MITHBrand, "Floral", 599, 1859),
    CompetitorScent("Green Sandalwood", MITHBrand, "Woody", 599, 2659),
    CompetitorScent("Black Alcantara", MITHBrand, "Woody", 699, 2059),
    CompetitorScent("Philosophy of Tao", MITHBrand, "Woody", 599, 1859),
    CompetitorScent("Blue Wood (Elixir)", MITHBrand, "Woody", 599, 1859),
    CompetitorScent("The Odyssey", MITHBrand, "Woody", 599, 1859),
    CompetitorScent("Step on Earth", MITHBrand, "Woody", 599, 1859),
    CompetitorScent("Into the Forest", MITHBrand, "Woody", None, None),
    CompetitorScent("Blue Wood", MITHBrand, "Woody", 599, 2659),
    CompetitorScent("Velvet Amber", MITHBrand, "Woody", None, None),
    CompetitorScent("Cozy Musk", MITHBrand, "Musky", 599, 2659),
    CompetitorScent("Pistachio & Vetiver", MITHBrand, "Gourmand", 599, 1859),
    CompetitorScent("Mystery for Her", MITHBrand, "Gourmand", 699, 2059),
    CompetitorScent("Chocolate Cafe", MITHBrand, "Gourmand", 599, 1859),
    CompetitorScent("Velvet Vanilla", MITHBrand, "Gourmand", None, None),
    CompetitorScent("Mellow Musks", MITHBrand, "Gourmand", 599, 1859),
    # OFD line
    CompetitorScent("Mango Sticky Rice", MITHBrand, "One Fine Day", 399, 1159),
    CompetitorScent("Thai Tea (OFD)", MITHBrand, "One Fine Day", 399, 1159),
    CompetitorScent("Jasmine Garland", MITHBrand, "One Fine Day", 399, 1159),
    CompetitorScent("Thai Pomelo", MITHBrand, "One Fine Day", 399, 1159),
    CompetitorScent("Lemon Ice Tea", MITHBrand, "One Fine Day", 399, 1159),
    CompetitorScent("Signature", MITHBrand, "One Fine Day", 399, 1159),
    CompetitorScent("Red", MITHBrand, "One Fine Day", 399, 1159),
    CompetitorScent("Unknown", MITHBrand, "One Fine Day", 399, 1159),
    # Citrus
    CompetitorScent("Italian Bergamot", MITHBrand, "Citrus", None, None),
    CompetitorScent("Aqua Blue", MITHBrand, "Citrus", 599, 1859),
    CompetitorScent("Ruby Bouquet", MITHBrand, "Citrus", None, None),
    CompetitorScent("Candy Candy", MITHBrand, "Citrus", None, None),
    CompetitorScent("Horizon", MITHBrand, "Citrus", None, None),
    CompetitorScent("Golden Sparkle", MITHBrand, "Citrus", None, None),
    CompetitorScent("Silver Sparkle", MITHBrand, "Citrus", None, None),
    CompetitorScent("Beach Breeze", MITHBrand, "Citrus", 1500, None),
    CompetitorScent("Florida Orange", MITHBrand, "Citrus", None, None),
    CompetitorScent("Twilight", MITHBrand, "Citrus", None, None),
    CompetitorScent("Mystery for Him", MITHBrand, "Citrus", None, None),
    # Tea
    CompetitorScent("Another tea", MITHBrand, "Tea", 1859, 2659),
    CompetitorScent("Tea in The Morning", MITHBrand, "Tea", None, None),
    # Oud
    CompetitorScent("Heritage Oud", MITHBrand, "Oud", None, None),
    CompetitorScent("Oud & Black Tea", MITHBrand, "Oud", None, None),
    CompetitorScent("Contemporary Oud", MITHBrand, "Oud", None, None),
    CompetitorScent("Royal Oud", MITHBrand, "Oud", None, None),

    # ---- Vibeslab ----
    CompetitorScent("Skins", VibeslabBrand, "Oriental/Gourmand", 2900, 4900,
                    notes=["Vanilla", "Civettone", "Cashmeran"],
                    key_materials=["Vanilla", "Civettone", "Cashmeran"]),
    CompetitorScent("Swim", VibeslabBrand, "Citrus Fresh", 2900, 4900,
                    notes=["Bergamot", "Petit Grain", "Musk"],
                    key_materials=["Bergamot", "Petitgrain", "Musk"]),
    CompetitorScent("Amalfi Soleil", VibeslabBrand, "Citrus Fresh", 2900, 4900),
    CompetitorScent("Burning Jazz Bar", VibeslabBrand, "Oriental/Tobacco", 2900, 4900,
                    notes=["Tobacco", "Labdanum", "Soap"],
                    key_materials=["Tobacco", "Labdanum", "Soap"]),
    CompetitorScent("Grand Hotel Ginza", VibeslabBrand, "Citrus Fresh", 2900, 4900,
                    notes=["Yuzu", "Green Tea Leaves", "Ambroxan"],
                    key_materials=["Yuzu", "Green tea", "Ambroxan"]),
    CompetitorScent("Money", VibeslabBrand, "Oriental/Woody", 2900, 4900,
                    notes=["Neroli", "Iso E Super", "Vetiver"],
                    key_materials=["Neroli", "Iso E Super", "Vetiver"]),
    CompetitorScent("Afternoon Tea", VibeslabBrand, "Gourmand", 2900, 4900),
    CompetitorScent("Pencil", VibeslabBrand, "Woody", 2900, 4900),
    CompetitorScent("Aged Oakmoss", VibeslabBrand, "Mossy/Woody", 2900, 4900),
    CompetitorScent("Gasoline", VibeslabBrand, "Novelty", 2900, 4900),
    CompetitorScent("Oud Elevator", VibeslabBrand, "Woody/Oud", 2900, 4900),
    CompetitorScent("New Car", VibeslabBrand, "Novelty", 2900, 4900),
    CompetitorScent("Smells Like Heaven", VibeslabBrand, "Floral", 2900, 4900),
]


# ---------------------------------------------------------------------------
# Material resolution helpers
# ---------------------------------------------------------------------------

def _normalize(name: str) -> str:
    return name.strip().lower()


def _resolve_material(name: str, profiles: dict, odt_data: dict) -> Optional[dict]:
    """Try to match a competitor note to a project material."""
    n = _normalize(name)

    # Direct match in profiles
    for pname in profiles:
        if _normalize(pname) == n:
            return {"project_name": pname, "odt": odt_data.get(pname), "in_inventory": True}

    # Partial match
    for pname in profiles:
        if n in _normalize(pname) or _normalize(pname) in n:
            return {"project_name": pname, "odt": odt_data.get(pname), "in_inventory": True}

    # Check ODT_DATA
    for oname in odt_data:
        if _normalize(oname) == n:
            return {"project_name": oname, "odt": odt_data.get(oname), "in_inventory": False}

    return None


def _categorize_note_tier(vp_pa: Optional[float]) -> str:
    if vp_pa is None:
        return "unknown"
    if vp_pa > 2.0:
        return "top"
    elif vp_pa >= 0.1:
        return "heart"
    else:
        return "base"


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------


def analyze_material_coverage(scents: List[CompetitorScent],
                               profiles: dict,
                               odt_data: dict) -> dict:
    """Cross-reference competitor note materials against project inventory."""
    all_notes: Set[str] = set()
    matched: Dict[str, dict] = {}
    unmatched: List[str] = []

    for scent in scents:
        for mat in scent.key_materials + scent.notes:
            n = _normalize(mat)
            if not mat or n in all_notes:
                continue
            all_notes.add(n)
            result = _resolve_material(mat, profiles, odt_data)
            if result:
                matched[mat] = result
            else:
                unmatched.append(mat)

    inventory_matched = [m for m in matched.values() if m["in_inventory"]]
    return {
        "total_notes_sourced": len(all_notes),
        "resolved_to_project": len(matched),
        "in_inventory": len(inventory_matched),
        "unresolved": len(unmatched),
        "unmatched_materials": sorted(set(unmatched)),
        "inventory_coverage_pct": round(len(inventory_matched) / max(len(all_notes), 1) * 100, 1),
    }


def analyze_price_corridor(scents: List[CompetitorScent]) -> dict:
    """Price corridor analysis per brand."""
    by_brand: Dict[str, List[float]] = {}
    for s in scents:
        by_brand.setdefault(s.brand, [])
        if s.price_per_ml_50:
            by_brand[s.brand].append(s.price_per_ml_50)

    result = {}
    for brand, prices in by_brand.items():
        if prices:
            result[brand] = {
                "min_per_ml": min(prices),
                "max_per_ml": max(prices),
                "avg_per_ml": round(sum(prices) / len(prices), 1),
                "n_products": len(prices),
            }
    return result


def analyze_category_overlap(scents: List[CompetitorScent]) -> dict:
    """Which olfactive categories each brand covers."""
    by_brand: Dict[str, Set[str]] = {}
    for s in scents:
        by_brand.setdefault(s.brand, set()).add(s.category)

    all_cats = sorted(set.union(*by_brand.values()) if by_brand else set())
    overlap = []
    mith_only = []
    vibes_only = []
    for cat in all_cats:
        in_mith = cat in by_brand.get(MITHBrand, set())
        in_vibes = cat in by_brand.get(VibeslabBrand, set())
        if in_mith and in_vibes:
            overlap.append(cat)
        elif in_mith:
            mith_only.append(cat)
        elif in_vibes:
            vibes_only.append(cat)

    return {
        "overlap_categories": sorted(overlap),
        "mith_only_categories": sorted(mith_only),
        "vibeslab_only_categories": sorted(vibes_only),
        "mith_category_count": len(by_brand.get(MITHBrand, set())),
        "vibeslab_category_count": len(by_brand.get(VibeslabBrand, set())),
    }


def generate_summary_report(profiles: dict, odt_data: dict) -> dict:
    """Full comparative analysis with framework-based scoring."""
    mith_scents = [s for s in COMPETITOR_SCENTS if s.brand == MITHBrand]
    vibes_scents = [s for s in COMPETITOR_SCENTS if s.brand == VibeslabBrand]

    mith_count = len(mith_scents)
    vibes_count = len(vibes_scents)
    mith_categories = sorted(set(s.category for s in mith_scents))
    vibes_categories = sorted(set(s.category for s in vibes_scents))
    set(mith_categories) & set(vibes_categories)
    set(mith_categories) - set(vibes_categories)
    set(vibes_categories) - set(mith_categories)

    return {
        "brand_summary": {
            MITHBrand: {
                "total_products": mith_count,
                "avg_price_per_ml_50": round(
                    sum(s.price_per_ml_50 for s in mith_scents if s.price_per_ml_50) /
                    max(sum(1 for s in mith_scents if s.price_per_ml_50), 1), 1
                ),
                "categories": mith_categories,
                "has_b2b": False,
                "has_body_care": True,
                "vrio_advantages": [
                    "Thai-cultural scent IP (first-mover association)",
                    "Perfumer relationships (Bisch, Morillas, Pellegrin)",
                    "Physical mall booths (Central World, Central Ladprao)"
                ],
                "vrio_sustainability": "Moderate — IP is authentic but perfumers can leave",
                "porter_threats": [
                    "HIGH: Grey market Dior/Chanel at comparable prices",
                    "HIGH: Low entry barrier for new Thai indie brands"
                ],
                "blue_ocean_opportunity": "1,500-2,500 THB gap — no brand occupies this price corridor",
            },
            VibeslabBrand: {
                "total_products": vibes_count,
                "avg_price_per_ml_50": round(
                    sum(s.price_per_ml_50 for s in vibes_scents if s.price_per_ml_50) /
                    max(sum(1 for s in vibes_scents if s.price_per_ml_50), 1), 1
                ),
                "categories": vibes_categories,
                "has_b2b": True,
                "has_body_care": False,
                "vrio_advantages": [
                    "B2B client network (Porsche, Owndays, Centara, 12+ years)",
                    "Novelty scent IP (Money, Gasoline — zero competition)",
                    "Curation discipline (13 SKUs, no dilution)"
                ],
                "vrio_sustainability": "High — 12-year B2B network is irreplicable",
                "porter_threats": [
                    "MODERATE: Niche ceiling — 13 SKUs cap addressable market",
                    "MODERATE: Supply bottleneck (100ml sold out)"
                ],
                "blue_ocean_opportunity": "Body care line in top scents (Money, Skins, Grand Hotel Ginza)",
            },
        },
        "material_coverage_mith": analyze_material_coverage(mith_scents, profiles, odt_data),
        "material_coverage_vibeslab": analyze_material_coverage(vibes_scents, profiles, odt_data),
        "price_corridor": analyze_price_corridor(COMPETITOR_SCENTS),
        "category_overlap": analyze_category_overlap(COMPETITOR_SCENTS),
        "strategic_group_map": {
            "mith_quadrant": "Low-moderate price + moderate uniqueness (broad appeal)",
            "vibeslab_quadrant": "High price + high uniqueness (differentiation)",
            "collision_zone": "2,000-3,000 THB band — MITH's 100ml at 2,859 vs Vibeslab's 50ml at 2,900",
            "uncontested_gap": "1,500-2,500 THB — neither brand occupies this price corridor",
            "blue_ocean_note": "A premium OFD-style sub-line (MITH) or 30ml travel size (Vibeslab) could capture this"
        },
        "revenue_model_estimate": {
            MITHBrand: {
                "avg_unit_price": 800,
                "est_monthly_units": "2,000-5,000",
                "revenue_edp": "1.6M-4M THB",
                "revenue_body_care": "0.4M-1M THB",
                "revenue_b2b": 0,
                "est_monthly_total": "2M-5M THB",
            },
            VibeslabBrand: {
                "avg_unit_price": 3500,
                "est_monthly_units": "300-800",
                "revenue_edp": "1.0M-2.8M THB",
                "revenue_body_care": 0,
                "revenue_b2b": "1M-3M THB",
                "est_monthly_total": "2M-6M THB",
            }
        },
        "competitor_ecosystem": {
            "known_thai_indie_brands": [
                "Exclusive One INC", "artepole", "LAB PARFUMO",
                "Butterfly Thai Perfume", "LAB PARFUMO", "MITH Bangkok", "Vibeslab"
            ],
            "pantip_mentions_mith": 6,
            "pantip_mentions_vibeslab": 5,
            "earliest_vibeslab_mention": "2014-07 (Pantip thread 32372020)",
            "confirmed_b2b_clients": [
                "Porsche/AAS (luxury automotive, 2024)",
                "Owndays (eyewear retail, 2018)",
                "Lebua (hotel)",
                "Centara (hotel)",
                "Rakxa (wellness resort)",
                "Anan (hotel)",
                "Tim (hotel)",
                "AP Thailand (real estate)"
            ],
            "mith_retail_presence": "Central World 3F booth, Central Ladprao booth, Shopee"
        }
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Cross-reference competitor brands against project inventory"
    )
    parser.add_argument("--brand", choices=["mith", "vibeslab", "all"], default="all",
                        help="Which brand to analyze (default: all)")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--output", type=str,
                        help="Write JSON output to file")
    args = parser.parse_args()

    inv_path = ROOT / "inventory.txt"
    if inv_path.exists():
        list(parse_inventory(inv_path))

    profiles = _PROFILES
    odt_data = ODT_DATA

    report = generate_summary_report(profiles, odt_data)

    if args.brand == "mith":
        report["brand_summary"].pop(VibeslabBrand, None)
        report.pop("material_coverage_vibeslab", None)
    elif args.brand == "vibeslab":
        report["brand_summary"].pop(MITHBrand, None)
        report.pop("material_coverage_mith", None)

    if args.json or args.output:
        output = json.dumps(report, indent=2, default=str)
        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"Report written to {args.output}")
        else:
            print(output)
        return

    # Human-readable report
    print("=" * 60)
    print("  COMPETITOR ANALYSIS REPORT")
    print("  MITH Bangkok vs Vibeslab")
    print("=" * 60)

    for brand, summary in report["brand_summary"].items():
        print(f"\n{'-' * 60}")
        print(f"  [{brand}]")
        print(f"{'-' * 60}")
        print(f"  Products analyzed:  {summary['total_products']}")
        print(f"  Avg price/mL (50ml): {summary['avg_price_per_ml_50']} THB")
        print(f"  Categories:          {', '.join(summary['categories'][:8])}")
        if len(summary['categories']) > 8:
            print(f"                       ... and {len(summary['categories']) - 8} more")
        print(f"  Has B2B:            {'YES' if summary['has_b2b'] else 'NO'}")
        print(f"  Has body care:      {'YES' if summary['has_body_care'] else 'NO'}")

    print(f"\n{'-' * 60}")
    print("  MATERIAL COVERAGE vs PROJECT INVENTORY")
    print(f"{'-' * 60}")
    for key in ["material_coverage_mith", "material_coverage_vibeslab"]:
        if key not in report:
            continue
        mc = report[key]
        brand_label = "MITH Bangkok" if "mith" in key else "Vibeslab"
        print(f"\n  {brand_label}:")
        print(f"    Unique notes sourced:  {mc['total_notes_sourced']}")
        print(f"    Resolved to project:   {mc['resolved_to_project']}")
        print(f"    In inventory:          {mc['in_inventory']}")
        print(f"    Unresolved:            {mc['unresolved']}")
        print(f"    Inventory coverage:    {mc['inventory_coverage_pct']}%")
        if mc['unmatched_materials']:
            print(f"    Missing from project:  {', '.join(mc['unmatched_materials'][:10])}")
            if len(mc['unmatched_materials']) > 10:
                print(f"                           ... and {len(mc['unmatched_materials']) - 10} more")

    print(f"\n{'-' * 60}")
    print("  PRICE CORRIDOR (THB/mL)")
    print(f"{'-' * 60}")
    for brand, pc in report.get("price_corridor", {}).items():
        print(f"  {brand}: {pc['min_per_ml']}-{pc['max_per_ml']} THB/mL  (avg {pc['avg_per_ml']})")

    report.get("category_overlap", {})
    print(f"\n{'-' * 60}")
    print("  STRATEGIC GROUP MAP")
    print(f"{'-' * 60}")
    sgm = report.get("strategic_group_map", {})
    print(f"  MITH:                {sgm.get('mith_quadrant', 'N/A')}")
    print(f"  Vibeslab:            {sgm.get('vibeslab_quadrant', 'N/A')}")
    print(f"  Collision zone:      {sgm.get('collision_zone', 'N/A')}")
    print(f"  Blue ocean gap:      {sgm.get('uncontested_gap', 'N/A')}")
    print(f"  Capture strategy:    {sgm.get('blue_ocean_note', 'N/A')}")

    print(f"\n{'-' * 60}")
    print("  VRIO ADVANTAGES")
    print(f"{'-' * 60}")
    for brand, summary in report["brand_summary"].items():
        advantages = summary.get("vrio_advantages", [])
        print(f"  {brand}:")
        for adv in advantages:
            print(f"    - {adv}")
        print(f"    Sustainability: {summary.get('vrio_sustainability', 'N/A')}")

    print(f"\n{'-' * 60}")
    print("  PORTER THREATS")
    print(f"{'-' * 60}")
    for brand, summary in report["brand_summary"].items():
        print(f"  {brand}:")
        for t in summary.get("porter_threats", []):
            print(f"    - {t}")

    print(f"\n{'-' * 60}")
    print("  ESTIMATED REVENUE MODEL (monthly)")
    print(f"{'-' * 60}")
    for brand, rev in report.get("revenue_model_estimate", {}).items():
        print(f"  {brand}:")
        print(f"    EDP revenue:       {rev.get('revenue_edp', 'N/A')}")
        print(f"    Body care:         {rev.get('revenue_body_care', 0)}")
        print(f"    B2B:               {rev.get('revenue_b2b', 0)}")
        print(f"    Total est.:        {rev.get('est_monthly_total', 'N/A')}")

    print(f"\n{'-' * 60}")
    print("  COMPETITOR ECOSYSTEM (Pantip + retail)")
    print(f"{'-' * 60}")
    eco = report.get("competitor_ecosystem", {})
    print(f"  Known Thai indie brands: {', '.join(eco.get('known_thai_indie_brands', []))}")
    print(f"  Pantip mentions: MITH={eco.get('pantip_mentions_mith', 0)}, Vibeslab={eco.get('pantip_mentions_vibeslab', 0)}")
    print(f"  Earliest Vibeslab mention: {eco.get('earliest_vibeslab_mention', 'N/A')}")
    print(f"  Confirmed B2B clients: {', '.join(eco.get('confirmed_b2b_clients', [])[:5])}...")
    print(f"  MITH retail: {eco.get('mith_retail_presence', 'N/A')}")

    print(f"\n{'-' * 60}")
    print("  BLUE OCEAN / WHITESPACE")
    print(f"{'-' * 60}")
    for brand, summary in report["brand_summary"].items():
        print(f"  {brand}: {summary.get('blue_ocean_opportunity', 'N/A')}")

    print(f"\n{'-' * 60}")
    print("  STRATEGIC RECOMMENDATIONS")
    print(f"{'-' * 60}")
    print("  MITH:")
    print("    1. Launch B2B scent branding division (hotel/spa packages)")
    print("    2. Prune 45 SKUs to 25 hero SKUs + 5 'Bangkok Stories' concept scents")
    print("    3. Add discovery set (8x2ml at 399 THB)")
    print("  Vibeslab:")
    print("    1. Fix 100ml supply (~2M THB/month latent demand)")
    print("    2. Launch 30ml at 1,900 THB to capture price-sensitive niche")
    print("    3. Body care line in top 3 scents (Money, Skins, Ginza)")
    print("  Both:")
    print("    1. 1,500-2,500 THB gap is a Blue Ocean for either brand")
    print("\n  Full analysis: data/competitor_analysis_mith_vs_vibeslab.md (9 frameworks)")
    print(f"\n{'=' * 60}\n")


if __name__ == "__main__":
    main()
