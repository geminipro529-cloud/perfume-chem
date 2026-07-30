"""A1 contract tests — gaps identified during Phase A0 audit.

These tests cover the six audit findings (A1.1–A1.6) where existing
test coverage is incomplete.  Each test reproduces the defect or
verifies a required behavior that was not previously tested.

Per the BUILD A plan: "Do not edit the implementation first.
Reproduce each defect with a failing test against the exact current
branch.  If a defect is already fixed, record the evidence and
retain a regression test without rewriting working code."
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ═══════════════════════════════════════════════════════════════════════════
# A1.1  Solvent and Carrier Classification
# ═══════════════════════════════════════════════════════════════════════════


class TestA11SolventCarrierClassification:
    """A1.1 — DPG, DEP, TEC, IPM classify by declared use, not string membership.
    Classification is independent from concentration basis.
    Inactive stock fraction allocated by declared diluent (carrier/solvent/unknown).
    Exact active, carrier, solvent, unallocated, and total mass conservation."""

    # ── category classification (stripped concentration suffix) ────────────

    def test_dep_classified_as_carrier_not_odorant(self):
        from engine.units.concentration import classify_material_category

        assert classify_material_category("DEP") == "carrier"
        assert classify_material_category("Diethyl Phthalate") == "carrier"

    def test_tec_classified_as_carrier_not_odorant(self):
        from engine.units.concentration import classify_material_category

        assert classify_material_category("TEC") == "carrier"
        assert classify_material_category("Triethyl Citrate") == "carrier"

    def test_ipm_classified_as_carrier_not_odorant(self):
        from engine.units.concentration import classify_material_category

        assert classify_material_category("IPM") == "carrier"
        assert classify_material_category("Isopropyl Myristate") == "carrier"

    def test_bht_with_concentration_still_technical(self):
        """Concentration suffix stripped — "BHT 10%" → "technical"."""
        from engine.units.concentration import classify_material_category

        assert classify_material_category("BHT 10%") == "technical"

    def test_classification_independent_from_concentration(self):
        from engine.units.concentration import classify_material_category

        assert classify_material_category("DPG") == "carrier"
        assert classify_material_category("DPG 10%") == "carrier"
        assert classify_material_category("BHT") == "technical"
        assert classify_material_category("BHT 10% in DPG") == "technical"

    # ── diluent inference ──────────────────────────────────────────────────

    def test_diluent_dpg_returns_carrier(self):
        from engine.units.concentration import _infer_diluent_category

        assert _infer_diluent_category("Galaxolide 50% in DPG") == "carrier"

    def test_diluent_tec_returns_carrier(self):
        from engine.units.concentration import _infer_diluent_category

        assert _infer_diluent_category("Musk 10% in TEC") == "carrier"

    def test_diluent_dep_returns_carrier(self):
        from engine.units.concentration import _infer_diluent_category

        assert _infer_diluent_category("Fixative 20% in DEP") == "carrier"

    def test_diluent_ipm_returns_carrier(self):
        from engine.units.concentration import _infer_diluent_category

        assert _infer_diluent_category("Softener 5% in IPM") == "carrier"

    def test_diluent_ethanol_returns_solvent(self):
        from engine.units.concentration import _infer_diluent_category

        assert _infer_diluent_category("Vanillin 10% in Ethanol") == "solvent"

    def test_diluent_water_returns_solvent(self):
        from engine.units.concentration import _infer_diluent_category

        assert _infer_diluent_category("Colorant 1% in Water") == "solvent"

    def test_diluent_unknown_returns_unknown(self):
        from engine.units.concentration import _infer_diluent_category

        assert _infer_diluent_category("Mystery 10% in xylitol") == "unknown"

    def test_diluent_no_match_returns_unknown(self):
        from engine.units.concentration import _infer_diluent_category

        assert _infer_diluent_category("Iso E Super") == "unknown"

    # ── active accounting by diluent ───────────────────────────────────────

    def test_neat_odorant_all_active_no_carrier(self):
        from engine.units.concentration import compute_active_accounting

        m: list[tuple[str, float, float]] = [("Iso E Super", 450.0, 1.0)]
        acct = compute_active_accounting(m)
        assert acct.odorant_active_ul == 450.0
        assert acct.carrier_ul == 0.0
        assert acct.unallocated_ul == 0.0
        assert acct.classified_total == acct.total_raw_ul

    def test_10pct_in_dpg_allocates_inactive_to_carrier(self):
        from engine.units.concentration import compute_active_accounting

        m: list[tuple[str, float, float]] = [("Galaxolide 10% in DPG", 200.0, 0.1)]
        acct = compute_active_accounting(m)
        assert abs(acct.odorant_active_ul - 20.0) < 0.001
        assert abs(acct.carrier_ul - 180.0) < 0.001  # DPG diluent
        assert acct.solvent_ul == 0.0
        assert acct.unallocated_ul == 0.0
        assert acct.classified_total == acct.total_raw_ul

    def test_10pct_in_tec_allocates_inactive_to_carrier(self):
        from engine.units.concentration import compute_active_accounting

        m: list[tuple[str, float, float]] = [("Musk 10% in TEC", 100.0, 0.1)]
        acct = compute_active_accounting(m)
        assert abs(acct.odorant_active_ul - 10.0) < 0.001
        assert abs(acct.carrier_ul - 90.0) < 0.001  # TEC diluent
        assert acct.classified_total == acct.total_raw_ul

    def test_10pct_in_ethanol_allocates_inactive_to_solvent(self):
        from engine.units.concentration import compute_active_accounting

        m: list[tuple[str, float, float]] = [("Vanillin 10% in Ethanol", 100.0, 0.1)]
        acct = compute_active_accounting(m)
        assert abs(acct.odorant_active_ul - 10.0) < 0.001
        assert acct.carrier_ul == 0.0  # NOT misclassified as carrier
        assert abs(acct.solvent_ul - 90.0) < 0.001
        assert acct.classified_total == acct.total_raw_ul

    def test_unknown_diluent_allocates_inactive_to_unallocated(self):
        from engine.units.concentration import compute_active_accounting

        m: list[tuple[str, float, float]] = [("Mystery 10% in xylitol", 100.0, 0.1)]
        acct = compute_active_accounting(m)
        assert abs(acct.odorant_active_ul - 10.0) < 0.001
        assert acct.carrier_ul == 0.0
        assert acct.solvent_ul == 0.0
        assert abs(acct.unallocated_ul - 90.0) < 0.001
        assert acct.classified_total == acct.total_raw_ul

    def test_unspecified_diluent_is_unallocated(self):
        """Material with bare percentage ("Hedione 10%") has no "% in X"
        pattern — diluent is unknown, inactive → unallocated."""
        from engine.units.concentration import compute_active_accounting

        m: list[tuple[str, float, float]] = [("Hedione 10%", 100.0, 0.1)]
        acct = compute_active_accounting(m)
        assert abs(acct.odorant_active_ul - 10.0) < 0.001
        assert acct.carrier_ul == 0.0
        assert abs(acct.unallocated_ul - 90.0) < 0.001
        assert acct.classified_total == acct.total_raw_ul

    def test_mixed_formula_conservation(self):
        """Mixed formula: neat odorant, diluted odorant in DPG, carrier,
        solvent, and technical material — all categories correctly assigned."""
        from engine.units.concentration import compute_active_accounting

        m: list[tuple[str, float, float]] = [
            ("Iso E Super", 450.0, 1.0),
            ("Galaxolide 50% in DPG", 280.0, 0.5),
            ("Vanillin 10% in Ethanol", 100.0, 0.1),
            ("DPG", 100.0, 1.0),
            ("BHT 10% in DPG", 10.0, 0.1),
            ("Ethanol", 50.0, 1.0),
            ("Mystery 5% in xylitol", 20.0, 0.05),
        ]
        acct = compute_active_accounting(m)
        assert acct.total_raw_ul == 1010.0
        assert abs(acct.odorant_active_ul - 601.0) < 0.001
        assert abs(acct.technical_active_ul - 1.0) < 0.001
        assert abs(acct.carrier_ul - 249.0) < 0.001
        assert abs(acct.solvent_ul - 140.0) < 0.001
        assert abs(acct.unallocated_ul - 19.0) < 0.001
        assert acct.classified_total == acct.total_raw_ul

    def test_mass_conservation_active_carrier_solvent_total(self):
        """Full mass conservation: classified_total == total_raw_ul."""
        from engine.units.concentration import compute_active_accounting

        materials: list[tuple[str, float, float]] = [
            ("Iso E Super", 450.0, 1.0),
            ("Galaxolide 50% in DPG", 280.0, 0.5),
            ("DPG", 100.0, 1.0),
            ("BHT 10% in DPG", 10.0, 0.1),
        ]
        acct = compute_active_accounting(materials)
        assert abs(acct.classified_total - acct.total_raw_ul) < 0.001


# ═══════════════════════════════════════════════════════════════════════════
# A1.2  Target Row Preservation
# ═══════════════════════════════════════════════════════════════════════════


class TestA12TargetRowPreservation:
    """A1.2 — All accepted input fields must survive target construction.
    Unknown fields must be rejected or preserved in extension field."""

    def test_provenance_links_preserved(self):
        from engine.target.formula import create_target_from_rows

        rows = [
            {
                "identity": "Hedione",
                "raw_amount": 300.0,
                "concentration": 1.0,
                "concentration_basis": "w/w",
                "carrier": "",
                "functional_roles": ("radiance",),
                "accord_membership": (),
                "time_windows": ("opening",),
                "evidence_links": ("src_001", "src_002", "src_003"),
            }
        ]
        formula = create_target_from_rows(rows)
        tm = formula.target_materials[0]
        assert tm.evidence_links == ("src_001", "src_002", "src_003")

    def test_uncertainty_bounds_preserved(self):
        from engine.target.formula import create_target_from_rows

        rows = [
            {
                "identity": "Ambrox",
                "raw_amount": 90.0,
                "concentration": 0.3,
                "concentration_basis": "w/w",
                "carrier": "",
                "functional_roles": ("base",),
                "accord_membership": (),
                "time_windows": ("drydown",),
                "active_amount_p05": 20.0,
                "active_amount_p95": 35.0,
            }
        ]
        formula = create_target_from_rows(rows)
        tm = formula.target_materials[0]
        assert tm.active_amount_p05 == 20.0
        assert tm.active_amount_p95 == 35.0

    def test_grade_preserved(self):
        from engine.target.formula import create_target_from_rows

        rows = [
            {
                "identity": "Vetiver Haitian",
                "raw_amount": 200.0,
                "concentration": 1.0,
                "concentration_basis": "w/w",
                "carrier": "",
                "functional_roles": ("character",),
                "accord_membership": (),
                "time_windows": ("heart", "drydown"),
                "grade": "HAITIAN_PREMIUM",
            }
        ]
        formula = create_target_from_rows(rows)
        tm = formula.target_materials[0]
        assert tm.grade == "HAITIAN_PREMIUM"

    def test_unit_preserved(self):
        from engine.target.formula import TargetMaterial

        tm = TargetMaterial(identity="Bergamot", active_amount_median=150.0)
        assert tm.active_amount_unit == "uL"


# ═══════════════════════════════════════════════════════════════════════════
# A1.3  Anti-Compression Alignment
# ═══════════════════════════════════════════════════════════════════════════


class TestA13AntiCompression:
    """A1.3 — Three-valued results (MATCH/DIFFER/UNKNOWN).
    Unknown evidence is not proof of equivalence.
    Neat vs dilution = different stock identities."""

    def test_should_merge_returns_false_with_no_checks(self):
        from engine.reconstruction.anti_compression import should_merge

        assert should_merge("A", "B", []) is False

    def test_neat_and_dilution_are_different_stocks(self):
        from engine.reconstruction.anti_compression import audit_formula

        results = audit_formula(["Iso E Super", "Iso E Super 10% in DPG"])
        assert len(results) > 0

    def test_audit_detects_cas_similarity_as_not_mergeable(self):
        from engine.reconstruction.anti_compression import audit_formula

        results = audit_formula(["Hedione", "Hedione HC"])
        assert len(results) > 0

    def test_compression_check_three_valued(self):
        from engine.reconstruction.anti_compression import CompressionCheck

        check = CompressionCheck("texture", True, "ok", "A", "B")
        assert check.passed is True
        check_fail = CompressionCheck("texture", False, "differ", "A", "B")
        assert check_fail.passed is False


# ═══════════════════════════════════════════════════════════════════════════
# A1.4  Chained Correction Replay
# ═══════════════════════════════════════════════════════════════════════════


class TestA14ChainedCorrectionReplay:
    """A1.4 — Reject missing references, cross-batch references.
    Detect cycles. Remain deterministic under repeated replay."""

    def test_missing_correction_ref_is_rejected(self):
        from engine.bottle.events import BottleEvent, compute_replay_state
        from engine.domain_errors import EventStreamError

        event = BottleEvent(
            event_id="e1",
            batch_id="b1",
            event_type="CORRECT_ENTRY",
            timestamp="2026-01-01T00:00:00Z",
            operator="test",
            stock_label="X",
            intended_mass_g=1.0,
            confirmation="COMMITTED",
            correction_ref="nonexistent_event",
        )
        with pytest.raises(EventStreamError, match="missing event"):
            compute_replay_state([event])

    def test_correction_chain_deterministic_replay(self):
        from engine.bottle.events import BottleEvent, compute_replay_state

        events = [
            BottleEvent(
                event_id="e1",
                batch_id="b1",
                event_type="DOSE_STOCK",
                timestamp="2026-01-01T00:00:00Z",
                operator="t",
                stock_label="X",
                intended_mass_g=1.0,
                confirmation="COMMITTED",
            ),
            BottleEvent(
                event_id="e2",
                batch_id="b1",
                event_type="CORRECT_ENTRY",
                timestamp="2026-01-01T00:01:00Z",
                operator="t",
                stock_label="X",
                intended_mass_g=1.5,
                confirmation="COMMITTED",
                correction_ref="e1",
            ),
        ]
        state1 = compute_replay_state(events)
        state2 = compute_replay_state(events)
        assert state1 == state2

    def test_cross_batch_correction_is_rejected(self):
        from engine.bottle.events import BottleEvent, compute_replay_state
        from engine.domain_errors import EventStreamError

        event_in_b1 = BottleEvent(
            event_id="e1",
            batch_id="b1",
            event_type="DOSE_STOCK",
            timestamp="2026-01-01T00:00:00Z",
            operator="t",
            stock_label="X",
            intended_mass_g=1.0,
            confirmation="COMMITTED",
        )
        correction_in_b2 = BottleEvent(
            event_id="e2",
            batch_id="b2",
            event_type="CORRECT_ENTRY",
            timestamp="2026-01-01T00:01:00Z",
            operator="t",
            stock_label="X",
            intended_mass_g=2.0,
            confirmation="COMMITTED",
            correction_ref="e1",
        )
        with pytest.raises(EventStreamError, match="cross-stream"):
            compute_replay_state([event_in_b1, correction_in_b2])


# ═══════════════════════════════════════════════════════════════════════════
# A1.5  Empty Reconstruction Inputs
# ═══════════════════════════════════════════════════════════════════════════


class TestA15EmptyReconstructionInputs:
    """A1.5 — Every public reconstruction entry point must reject an
    empty roster with the stable domain error."""

    def test_empty_roster_map_target_raises_domain_error(self):
        from engine.domain_errors import ReconstructionInputError
        from engine.inventory.stock_model import InventoryLedger, map_target_to_inventory

        with pytest.raises(ReconstructionInputError, match="inventory target"):
            map_target_to_inventory([], InventoryLedger([]))

    def test_empty_audit_formula_raises_domain_error(self):
        from engine.domain_errors import ReconstructionInputError
        from engine.reconstruction.anti_compression import audit_formula

        with pytest.raises(ReconstructionInputError, match="roster"):
            audit_formula([])

    def test_empty_compute_replay_state_raises_domain_error(self):
        from engine.bottle.events import compute_replay_state
        from engine.domain_errors import ReconstructionInputError

        with pytest.raises(ReconstructionInputError, match="ordered bottle event"):
            compute_replay_state([])


# ═══════════════════════════════════════════════════════════════════════════
# A1.6  Identity Resolution vs Stock Availability
# ═══════════════════════════════════════════════════════════════════════════


class TestA16IdentityVsStockAvailability:
    """A1.6 — Identity and inventory authority remain independent.

    Legacy flat status constants remain as compatibility projections, while the
    canonical mapping exposes independent identity and inventory enum fields.
    A resolved material absent from inventory is NOT unknown identity.
    An ambiguous name must NOT be converted to confident canonical."""

    def test_resolved_material_absent_is_not_unknown_identity(self):
        from engine.inventory.stock_model import (
            EXACT_IDENTITY_NOT_IN_STOCK,
            UNKNOWN_IDENTITY,
            InventoryLedger,
            map_target_to_inventory,
        )

        results = map_target_to_inventory(["Iso E Super"], InventoryLedger([]))
        assert results[0].status == EXACT_IDENTITY_NOT_IN_STOCK
        assert results[0].status != UNKNOWN_IDENTITY

    def test_truly_unknown_is_unknown_identity(self):
        from engine.inventory.stock_model import (
            UNKNOWN_IDENTITY,
            InventoryLedger,
            map_target_to_inventory,
        )

        results = map_target_to_inventory(["ZZXQ_NOT_A_REAL_MATERIAL_99999"], InventoryLedger([]))
        assert results[0].status == UNKNOWN_IDENTITY

    def test_resolved_material_in_stock_is_exact(self):
        from engine.inventory.stock_model import (
            EXACT_AVAILABLE,
            InventoryLedger,
            StockItem,
            map_target_to_inventory,
        )

        item = StockItem(
            material_id="id1",
            label="Iso E Super",
            concentration=1.0,
            amount_remaining_ml=100,
        )
        results = map_target_to_inventory(["Iso E Super"], InventoryLedger([item]))
        assert results[0].status == EXACT_AVAILABLE

    def test_identity_resolution_and_stock_availability_are_separate_concerns(self):
        """Legacy compatibility statuses remain distinct and non-ambiguous.

        The authoritative independent enum fields are contracted separately in
        ``tests/test_a1_authoritative_contracts.py``.
        """
        from engine.inventory.stock_model import (
            EXACT_AVAILABLE,
            EXACT_IDENTITY_NOT_IN_STOCK,
            FUNCTIONAL_SUBSTITUTE,
            UNAVAILABLE,
            UNKNOWN_IDENTITY,
        )

        all_statuses = {
            EXACT_AVAILABLE,
            EXACT_IDENTITY_NOT_IN_STOCK,
            FUNCTIONAL_SUBSTITUTE,
            UNKNOWN_IDENTITY,
            UNAVAILABLE,
        }
        for s in all_statuses:
            assert isinstance(s, str)
