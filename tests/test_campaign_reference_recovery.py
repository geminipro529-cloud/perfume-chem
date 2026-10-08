"""Historical design recovery is not present stock or physical-bottle truth."""

import hashlib
import json
import re
from decimal import Decimal

import pytest

from engine.formulation_intelligence import campaign_reference as recovery
from engine.formulation_intelligence import subtype_research
from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.literature_knowledge import retrieve_formulation_knowledge
from engine.research.subtype_benchmark import _campaign_hold_verified


def test_exact_saved_source_rows_reconcile_without_mass_volume_conversion():
    raw = recovery.MANIFEST_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == recovery.MANIFEST_SHA256
    value = json.loads(raw)
    lines = (recovery.ROOT / recovery.SOURCE_PATHS[0]).read_text(encoding="utf-8").splitlines()
    assert len(value["rows"]) == len({r["material"] for r in value["rows"]}) == 47
    totals = {"uL": Decimal(0), "mg": Decimal(0)}
    for row in value["rows"]:
        source = lines[row["source_line"] - 1]
        cells = [cell.strip() for cell in source.split("|")[1:-1]]
        amount, unit = re.fullmatch(r"([\d,]+) (µL|mg)", cells[2]).groups()
        assert cells[:2] == [row["material"], row["historical_stock_description"]]
        assert row["amount_decimal"] == amount.replace(",", "")
        assert row["amount_unit"] == {"µL": "uL", "mg": "mg"}[unit]
        totals[row["amount_unit"]] += Decimal(row["amount_decimal"])
    assert totals == {"uL": Decimal("5510"), "mg": Decimal("600")}
    assert sum(r["amount_unit"] == "uL" for r in value["rows"]) == 46
    assert value["physical_history"]["final_volume_ml_decimal"] is None
    assert value["physical_history"]["withdrawn_source_line"] == 1719
    assert 1758 in value["physical_history"]["correcting_source_lines"]
    assert not value["historical_design_is_current_bottle"]
    assert not any(value["authority"].values())


@pytest.mark.parametrize("fault", ["manifest", *recovery.SOURCE_PATHS])
def test_drift_or_missing_local_source_cannot_resolve_hold(monkeypatch, tmp_path, fault):
    for relative in recovery.SOURCE_PATHS:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((recovery.ROOT / relative).read_bytes())
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(recovery.MANIFEST_PATH.read_bytes())
    monkeypatch.setattr(recovery, "ROOT", tmp_path)
    monkeypatch.setattr(recovery, "MANIFEST_PATH", manifest)
    assert recovery.recovered_campaign_reference("CHIMIE_LHOMME") is not None
    target = manifest if fault == "manifest" else tmp_path / fault
    target.write_bytes(target.read_bytes() + b" ")
    assert recovery.recovered_campaign_reference("CHIMIE_LHOMME") is None
    target.unlink()
    assert recovery.recovered_campaign_reference("CHIMIE_LHOMME") is None


def test_recovery_is_exact_named_context_not_an_alias_or_new_formula():
    before = subtype_research.SUBTYPE_PATH.read_bytes()
    result = retrieve_formulation_knowledge("CHIMIE L'HOMME")
    hold = result["subtype_context"]["campaign_identity_holds"][0]
    assert hold["state"] == "HOLD_EXACT_BRIEF_OR_FORMULA_REQUIRED"  # compatibility only
    assert "has been recovered" in hold["reason"]
    assert "not recovered" in hold["historical_reason"]
    assert hold["recovered_reference"]["formula_action"] == "NO_CHANGE"
    assert subtype_research.SUBTYPE_PATH.read_bytes() == before
    assert recovery.recovered_campaign_reference("Sport Citrus / Dry Amber") is None
    assert recovery.recovered_campaign_reference("../CHIMIE_LHOMME") is None
    assert not retrieve_formulation_knowledge("Sport Citrus / Dry Amber")["subtype_context"]["campaign_identity_holds"]


def test_studio_reports_recovery_without_bypassing_campaign_binding():
    result = design_formula(formula_name="CHIMIE L'HOMME", idea="More layering",
                            design_mode="DEEP_COMPOSE", max_materials=12, variant_count=3,
                            liquid_concentrate_ul_decimal="6000")
    assert _campaign_hold_verified(result)
    assert "has been recovered" in result["assistant_message"]
    assert "not been recovered" not in result["assistant_message"]
    assert result["recovered_campaign_references"][0]["manifest_sha256"] == recovery.MANIFEST_SHA256
    assert result["optimized_formula"] is None and result["design_variants"] == []
    assert result["formula_modified"] is False and result["inventory_modified"] is False
