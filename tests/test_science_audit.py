import hashlib
import json
from pathlib import Path

from engine.data_spine.loader import load_materials
from engine.inventory_parser import INVENTORY_PATH
from engine.science_audit import (
    _gather_data_coverage,
    build_inventory_oav_coverage_audit,
    build_material_consistency_audit,
    build_science_audit_contract,
)


def test_science_audit_uses_loader_backed_completeness():
    coverage = _gather_data_coverage()
    materials = load_materials()

    assert coverage
    assert coverage["mw"] > 0.0
    assert materials

    supplier_covered = sum(1 for material in materials if material.completeness()["supplier"])
    supplier_pct = 100.0 * supplier_covered / len(materials)
    assert supplier_pct > 75.0


def test_science_audit_reports_unifac_readiness_without_claiming_activation():
    activity = build_science_audit_contract()["activity_model"]

    assert activity["selected_model"] == (
        "hansen_distance_regular_solution_heuristic"
    )
    assert activity["selected_model_authority"] == "HEURISTIC_UNCALIBRATED"
    assert activity["unifac_implemented"] is False
    assert activity["unifac_active"] is False
    assert activity["unifac_ready"] is False
    assert activity["release_authority"] is False
    assert activity["unifac_blockers"]


def test_material_consistency_audit_distinguishes_reconciled_and_unresolved_truth():
    audit = build_material_consistency_audit(
        [
            "Polysantol",
            "Melonal",
            "Spike Lavender EO",
            "Iso E Super",
            "Benzyl Benzoate",
            "Dynascone",
            "Habanolide",
        ]
    )

    assert audit["scope"] == "requested_materials"
    assert audit["release_authority"] is False
    conflicts = {
        (row["material"], row["field"]): row
        for row in audit["conflicts"]
    }
    assert ("Polysantol", "odt_air_ppb") not in conflicts
    assert ("Benzyl Benzoate", "vp_25c_pa") not in conflicts
    assert ("Dynascone", "vp_25c_pa") not in conflicts
    assert ("Habanolide", "vp_25c_pa") not in conflicts
    assert ("Melonal", "vp_25c_pa") not in conflicts
    assert ("Spike Lavender EO", "vp_25c_pa") in conflicts
    assert conflicts[("Spike Lavender EO", "vp_25c_pa")]["status"] == (
        "UNRESOLVED_NATURAL_MIXTURE_PROXY_CONFLICT"
    )


def test_natural_proxy_conflict_reports_composite_runtime_precedence():
    audit = build_material_consistency_audit(["Lime Distilled EO"])
    conflicts = {row["field"]: row for row in audit["conflicts"]}

    assert conflicts["vp_25c_pa"]["evidence_class"] == (
        "NATURAL_MIXTURE_BULK_PROXY"
    )
    assert conflicts["vp_25c_pa"]["composite_oav_coverage"] is True
    assert conflicts["vp_25c_pa"]["runtime_precedence"] == (
        "natural_composite_constituents"
    )


def test_live_inventory_oav_audit_separates_supported_opaque_and_unresolved() -> None:
    audit = build_inventory_oav_coverage_audit()
    categories = audit["categories"]

    assert audit["scope"] == "live_owned_non_solvent_inventory"
    assert audit["release_authority"] is False
    assert audit["oav_available_count"] + audit["oav_unknown_count"] == audit[
        "material_count"
    ]
    # Exact counts bind this view (not physical stock lots) to the reviewed
    # received-stock successor. Ownership does not supply missing OAV evidence.
    receipt_path = (
        Path(__file__).resolve().parents[1]
        / "data/inventory_receipts/perfumersworld_261004-055451ce1_received_20261007.json"
    )
    receipt_bytes = receipt_path.read_bytes()
    assert hashlib.sha256(receipt_bytes).hexdigest() == (
        "089c930e044b55e434c0e0438ee7b2c20f48d871f00a219a7237a932419fbc9a"
    )
    receipt = json.loads(receipt_bytes)
    assert hashlib.sha256(INVENTORY_PATH.read_bytes()).hexdigest() == receipt[
        "inventory_after_sha256"
    ]
    assert audit["material_count"] == 290
    # 2026-10-08 data PR: cited air ODTs made Aldehyde C-8 Octanal, Aldehyde
    # C-9 Nonanal and Butyl Butyrate OAV-available (226 -> 229). The spelling
    # alias "Ambrox Super Crystals" -> Ambrox Super made it resolve (229 -> 230).
    # The ISO 8896 caraway profile (partial input coverage) took Caraway Seed
    # Oil out of naturals_missing_composite_evidence (230 -> 231).
    # Labelled proxy profiles for Ambrette Seed Absolute, Lavandin Absolute,
    # Orris Concrete Orris Butter and Cinnamon Bark EO (Telvada) made them
    # OAV-available (231 -> 235).
    # Name links put Aldehyde C-12 Lauric Dodecanal, Aldehyde C-18 and Phenyl
    # Acetaldehyde on thresholds held under another name (235 -> 238), and
    # labelled proxy profiles for Magnolia EO, Champaca Flower EO, Peru Balsam
    # Resinoid, Tagetes EO, Helichrysum EO and Guaiacwood EO made them
    # OAV-available (238 -> 244). Rose Otto Bulgarian, Haitian Vetiver EO and
    # Hay Absolute proxy profiles and the IFF vapour pressure for
    # Cis-3-Hexenyl Salicylate followed (244 -> 248). The 2026-10-10 vapour
    # pressures (RIFM measured at 20 C, converted to 25 C; supplier sheet for
    # Helvetolide) made Ambrocenide and Helvetolide OAV-available (248 -> 250).
    # 2026-10-14 gap search: a labelled EPI vapour-pressure estimate made Maltol
    # OAV-available, and the PerfumersWorld spelling "Saffranal" now resolves to
    # Safranal. Both air thresholds are still tagged UNVERIFIED in
    # ODT_VERIFICATION. Costus Olifac lost its placeholder MW and VP (an IFF base
    # with no CAS) and became OAV-unknown (250 -> 251).
    # 2026-10-25 physics batch 1: a labelled partial profile from PerfumersWorld's
    # declared levels made Frangipani Absolute OAV-available (251 -> 252).
    # 2026-10-25 physics batch 2: a labelled citral estimate (BP terpeneless grade)
    # made Lemon Terpeneless Oil Sicilian OAV-available (252 -> 253).
    # 2026-10-25 fruit batch: Givaudan US 12,340,876 air thresholds made Cis-3 Hexenyl
    # Acetate and Manzanate OAV-available (253 -> 255).
    # 2026-10-25 literature batch: producer air thresholds made Berry Hexanoate
    # (BerryFlor), Magnolan and Methyl Diantilis OAV-available (255 -> 258).
    # 2026-10-25 naturals batch: labelled partial profiles made Cabreuva EO, Pine EO,
    # Sandalwood EO and Tuberlia Base OAV-available (258 -> 262).
    # 2026-10-28: a labelled UNVERIFIED analogue air threshold (Kenny's card choice) made
    # Cedryl Acetate OAV-available (262 -> 263). Group 2 the same day did the same for
    # Caryophyllene Acetate (263 -> 264). Group 3 made Acetoin and Ethyl Linalyl Acetate
    # OAV-available (264 -> 266). Group 4 gave Methyl Laitone Givaudan's SDS air threshold
    # (266 -> 267). Group 5 shared Leafovert's Symrise air threshold with Liffarome, the same
    # molecule (267 -> 268).
    assert audit["oav_available_count"] == 268
    assert audit["oav_unknown_count"] == 22
    assert audit["oav_coverage_pct"] == 92.414
    assert "Costus Olifac" in categories["other_oav_unknowns"]
    assert not {"Maltol", "Saffranal"} & set(categories["other_oav_unknowns"])
    assert audit["status"] == "FAIL_CLOSED_GAPS"
    # Manzanate left this set on 2026-10-25 (Givaudan air threshold); Fructone B is still unknown.
    assert {"Fructone B"} <= set(categories["other_oav_unknowns"])
    assert "Manzanate" not in categories["other_oav_unknowns"]
    assert not {"Helvetolide", "Ambrocenide"} & set(categories["other_oav_unknowns"])
    assert "Frangipani Absolute" not in categories["naturals_missing_composite_evidence"]
    assert "Lemon Terpeneless Oil Sicilian" not in categories["naturals_missing_composite_evidence"]
    assert "Leather FO" in categories[
        "opaque_preblends_without_disclosed_composition"
    ]
    assert "Jasmine FO" not in categories[
        "opaque_preblends_without_disclosed_composition"
    ]
    assert "Cade Oil Rectified" in categories[
        "naturals_missing_composite_evidence"
    ]
    assert "Red Mandarin EO" not in categories[
        "naturals_missing_composite_evidence"
    ]
    assert "Eucalyptus Essential Oil" not in categories[
        "naturals_missing_composite_evidence"
    ]
    assert "Clary Sage EO" not in categories[
        "naturals_missing_composite_evidence"
    ]
    assert "Kenyan Myrrh resin ethanol tincture" not in categories[
        "unknown_material_identities"
    ]
    assert "Oman Frankincense resin ethanol tincture" not in categories[
        "unknown_material_identities"
    ]
    assert "Turkish Storax Liquidambar orientalis resin ethanol tincture" not in categories[
        "naturals_missing_composite_evidence"
    ]
    assert "Vietnamese Benzoin Styrax tonkinensis resin ethanol tincture" not in categories[
        "naturals_missing_composite_evidence"
    ]
