from __future__ import annotations

import json
import socket
from dataclasses import replace
from datetime import date
from hashlib import sha256

import pytest

from engine.research.commercial_references import (
    DEFAULT_REGISTRY_PATH,
    build_commercial_reference_panel,
    load_commercial_reference_registry,
    resolve_documentary_references,
)
from engine.research.request_interpretation import RequestInterpretationInputV1, interpret_request


def test_orchard_panel_is_exact_and_not_a_liking_or_formula_claim():
    result = build_commercial_reference_panel(("pear", "apple", "lychee", "freesia", "amber"), as_of_date="2026-10-06")
    assert result["panel"]["panel_id"] == "global-orchard-floral-2026-v1"
    assert [row["product_id"] for row in result["panel"]["active_members"]] == [
        "ysl-libre-edp", "prada-paradoxe-edp", "guerlain-pera-granita-edt",
        "jomalone-english-pear-freesia-cologne",
    ]
    assert sum(row["market_anchor"] for row in result["panel"]["active_members"]) == 2
    assert sum(row["structural_neighbour"] for row in result["panel"]["active_members"]) == 2
    assert [row["product_id"] for row in result["panel"]["reserve_members"]] == ["pdm-delina-edp"]
    assert result["population_liking_state"] == "POPULATION_LIKING_NOT_ESTABLISHED"
    assert not result["products"]["prada-paradoxe-edp"]["liking_authority"]
    assert "pear" not in result["products"]["prada-paradoxe-edp"]["marketed_facets"]
    assert all(not product["formula_composition_known"] for product in result["products"].values())
    market = next(row for row in result["evidence"] if row["evidence_id"] == "loreal-luxe-2025-paradoxe-line")
    assert market["market_scope"] == "PRODUCT_LINE"
    assert market["market_region"] == "GLOBAL"
    assert market["supplies_liking_label"] is False
    assert result["release_authority"] is result["safety_authority"] is result["compounding_authority"] is False


@pytest.mark.parametrize("tags", [("amber",), ("musk", "vanilla"), ("floral",), ("rose", "woody")])
def test_generic_support_tags_cannot_admit_an_unrelated_family(tags):
    with pytest.raises(ValueError, match="matches"):
        build_commercial_reference_panel(tags, as_of_date="2026-10-06")


def test_explicit_panel_still_requires_identity_and_current_review():
    with pytest.raises(ValueError, match="matches"):
        build_commercial_reference_panel(("pear",), panel_id="global-lavender-amber-2026-v2", as_of_date="2026-10-06")
    registry = load_commercial_reference_registry()
    key = "global-orchard-floral-2026-v1"
    future = replace(registry, panels={key: replace(registry.panels[key], as_of_date="2027-01-01")})
    with pytest.raises(ValueError, match="NOT_YET_REVIEWED"):
        build_commercial_reference_panel(("pear",), as_of_date="2026-10-06", registry=future)
    with pytest.raises(KeyError):
        build_commercial_reference_panel(("pear",), panel_id="invented", as_of_date="2026-10-06")


def test_every_structural_neighbour_requires_its_current_architecture():
    registry = load_commercial_reference_registry()
    key = "global-orchard-floral-2026-v1"
    panel = registry.panels[key]
    panel = replace(panel, evidence_ids=tuple(key for key in panel.evidence_ids if key != "official-architecture-guerlain-pera-granita-edt"))
    changed = replace(registry, panels={panel.panel_id: panel})
    with pytest.raises(ValueError, match="STRUCTURAL_NEIGHBOUR"):
        build_commercial_reference_panel(("pear",), as_of_date="2026-10-06", registry=changed)


def test_auto_selection_skips_expired_match_but_abstains_on_relevance_tie():
    registry = load_commercial_reference_registry()
    panel = registry.panels["global-orchard-floral-2026-v1"]
    expired = replace(panel, panel_id="a-expired", expires_on="2026-10-05")
    current = replace(panel, panel_id="b-current")
    rules = {p.panel_id: {"required_any_tag_groups": [["pear"]]} for p in (expired, current)}
    changed = replace(registry, panels={p.panel_id: p for p in (expired, current)}, selection_rules=rules)
    result = build_commercial_reference_panel(("pear",), as_of_date="2026-10-06", registry=changed)
    assert result["panel"]["panel_id"] == current.panel_id
    second = replace(expired, expires_on="2026-12-31")
    changed = replace(changed, panels={p.panel_id: p for p in (second, current)})
    with pytest.raises(ValueError, match="RELEVANCE_AMBIGUOUS"):
        build_commercial_reference_panel(("pear",), as_of_date="2026-10-06", registry=changed)


def test_v1_v2_bytes_are_preserved_and_wrong_v3_predecessor_fails(tmp_path):
    expected = {
        "commercial_reference_registry_v1.json": "1d83c920487b69f55c7ca0b439f43beeaac048f5edc6b6d6bfcce00c441510f3",
        "commercial_reference_registry_v2.json": "d6452bfe6c743551a496fc88b5737aa33f163458fc3f72973c626058dd88de5e",
    }
    for name, digest in expected.items():
        assert sha256(DEFAULT_REGISTRY_PATH.with_name(name).read_bytes()).hexdigest() == digest
    raw = json.loads(DEFAULT_REGISTRY_PATH.read_text(encoding="utf-8"))
    raw["predecessor_sha256"] = "0" * 64
    path = tmp_path / "changed.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="PREDECESSOR_DRIFT"):
        load_commercial_reference_registry(path)


@pytest.mark.parametrize("text,expected", [
    ("Compare Prada Paradoxe EDP", "prada-paradoxe-edp"),
    ("Compare English Pear & Freesia Cologne", "jomalone-english-pear-freesia-cologne"),
    ("Compare Delina Eau de Parfum", "pdm-delina-edp"),
])
def test_exact_named_documentary_reference_has_no_sample_binding(text, expected):
    result = resolve_documentary_references(text, as_of_date="2026-10-06")
    assert [p.product_id for p in result["products"]] == [expected]
    assert result["unresolved"] == []
    assert result["sample_identity_bound"] is False


@pytest.mark.parametrize("text", ["Prada Paradoxe EDT", "Paradoxe Intense", "Delina Exclusif", "Paradoxe EDP Intense", "Delina Hair Mist"])
def test_wrong_concentration_or_flanker_cannot_borrow_original(text):
    result = resolve_documentary_references(text, as_of_date="2026-10-06")
    assert result["products"] == []
    assert result["unresolved"]


def test_avoided_reference_and_longer_word_are_not_positive_mentions():
    result = interpret_request(RequestInterpretationInputV1(original_request="Avoid YSL Libre; use pear and freesia", known_references=("YSL Libre",)))
    assert result["reference_scope"]["named_references"] == []
    for text in ("Avoid Paradoxe; keep pear", "Delinately floral", "Paradoxeness"):
        assert resolve_documentary_references(text, as_of_date="2026-10-06")["products"] == []


def test_named_reference_architecture_currency_cannot_be_bypassed():
    registry = load_commercial_reference_registry()
    key = "official-architecture-prada-paradoxe-edp"
    changed = replace(registry, evidence={**registry.evidence, key: replace(registry.evidence[key], expires_on="2026-10-05")})
    result = resolve_documentary_references("Paradoxe EDP", as_of_date="2026-10-06", registry=changed)
    assert result["products"] == []
    assert result["unresolved"][0]["reason"] == "NAMED_REFERENCE_ARCHITECTURE_UNAVAILABLE"


def test_reference_runtime_has_no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("runtime network forbidden")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    result = build_commercial_reference_panel(("pear",), as_of_date="2026-10-06")
    assert result["status"] == "MARKET_SELECTED_REFERENCE_PANEL"


def test_goal_family_comes_from_positive_target_not_support_rows():
    from engine.research.goal_analysis import (
        GoalAnalysisRequestV1,
        GoalFormulaRowV1,
        _commercial_concept_tags,
    )

    request = GoalAnalysisRequestV1(
        formula_id="orchard", formula_name="Pear Orchard", family="fruity floral",
        rows=(GoalFormulaRowV1("support", "Lavender EO", "100", "uL"),),
        goals=("clearer pear; avoid lavender and vanilla",),
        must_avoid=("lavender", "vanilla"),
    )
    assert request.market_evidence_as_of_date == date.today().isoformat()
    tags = _commercial_concept_tags(request)
    assert "pear" in tags
    assert "lavender" not in tags and "vanilla" not in tags
    panel = build_commercial_reference_panel(tags, as_of_date="2026-10-06")
    assert panel["panel"]["panel_id"] == "global-orchard-floral-2026-v1"


def test_planner_active_links_do_not_include_reserve_facets():
    from engine.research.composition_planner import _reference_context

    context = _reference_context("pear apple freesia", appeal_mode="GLOBAL_CROWD_PLEASING", concept=None, rows=())
    assert context["status"] == "MARKET_SELECTED_REFERENCE_PANEL"
    assert "pdm-delina-edp" not in {row["product_id"] for row in context["active_members"]}
    assert "lychee" not in {row["marketed_facet"] for row in context["selected_architecture_links"]}
