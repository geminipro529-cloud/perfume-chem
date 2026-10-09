from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from engine.research import composition_planner as planner
from engine.research import normal_use_ceilings as ceilings
from engine.research.formula_design import design_inventory_formula

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "normal_use_ceilings_fixture_v1.json"
CHYPRE_IDEA = "a panoramic, exceptionally detailed modern chypre with rose, patchouli and oakmoss"
CHYPRE_NAME = "Panoramic Chypre"
CEILING_KEY = "normal_use_ceiling_pct_of_concentrate"


def _entry(material: str, match: list[str], pct: Any = 1.0) -> dict[str, Any]:
    return {
        "material": material,
        "match": match,
        "max_active_pct_of_concentrate": pct,
        "sources": [{"kind": "test"}],
        "note": "test",
    }


def _payload(*entries: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "normal_use_ceilings_v1",
        "status": "DRAFT_FOR_KENNY_REVIEW",
        "basis": "active material as % of the fragrance concentrate",
        "materials": list(entries),
    }


def _candidate(name: str, dilution: float) -> Any:
    stock = SimpleNamespace(
        name=name,
        identity_name=name,
        raw_name=name,
        physical_form="liquid",
        fraction_basis="neat" if dilution >= 1 else "mass_fraction",
        carrier="" if dilution >= 1 else "DPG",
        dilution=dilution,
    )
    return SimpleNamespace(stock=stock)


@pytest.fixture
def fixture_ceilings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ceilings, "NORMAL_USE_CEILINGS_PATH", FIXTURE)


def test_shipped_data_file_loads_with_no_materials() -> None:
    assert ceilings.NORMAL_USE_CEILINGS_PATH.is_file()
    assert ceilings.load_normal_use_ceilings(ceilings.NORMAL_USE_CEILINGS_PATH) == ()


def _mutate(path: list[Any], value: Any) -> dict[str, Any]:
    payload = copy.deepcopy(_payload(_entry("Alpha Damascone", ["alpha damascone"])))
    target: Any = payload
    for key in path[:-1]:
        target = target[key]
    if value is _DELETE:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return payload


_DELETE = object()


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (["schema_version"], "normal_use_ceilings_v2"),
        (["basis"], "raw stock as % of concentrate"),
        (["status"], ""),
        (["materials"], {"material": "x"}),
        (["materials"], _DELETE),
        (["materials", 0], "Alpha Damascone"),
        (["materials", 0, "material"], ""),
        (["materials", 0, "match"], []),
        (["materials", 0, "match"], ["  -  "]),
        (["materials", 0, "match"], "alpha damascone"),
        (["materials", 0, "max_active_pct_of_concentrate"], 0),
        (["materials", 0, "max_active_pct_of_concentrate"], -0.5),
        (["materials", 0, "max_active_pct_of_concentrate"], 100.01),
        (["materials", 0, "max_active_pct_of_concentrate"], "0.2"),
        (["materials", 0, "max_active_pct_of_concentrate"], True),
        (["materials", 0, "max_active_pct_of_concentrate"], float("nan")),
        (["materials", 0, "max_active_pct_of_concentrate"], _DELETE),
        (["materials", 0, "sources"], []),
        (["materials", 0, "sources"], ["a citation string"]),
        (["materials", 0, "note"], None),
    ],
)
def test_loader_rejects_bad_shapes_and_values(path: list[Any], value: Any) -> None:
    with pytest.raises(ceilings.NormalUseCeilingsError):
        ceilings.parse_normal_use_ceilings(_mutate(path, value))


def test_loader_rejects_non_object_and_ambiguous_phrases(tmp_path: Path) -> None:
    with pytest.raises(ceilings.NormalUseCeilingsError):
        ceilings.parse_normal_use_ceilings([])
    with pytest.raises(ceilings.NormalUseCeilingsError, match="claimed by both"):
        ceilings.parse_normal_use_ceilings(
            _payload(_entry("A", ["Beta-Ionone"]), _entry("B", ["beta ionone"]))
        )
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(ceilings.NormalUseCeilingsError):
        ceilings.load_normal_use_ceilings(broken)


def test_loader_accepts_100_percent_and_keeps_the_number() -> None:
    (parsed,) = ceilings.parse_normal_use_ceilings(_payload(_entry("Hedione", ["hedione"], 100)))
    assert parsed.max_active_pct_of_concentrate == 100
    assert parsed.max_active_fraction == Decimal("1")


SPECIFIC = ceilings.parse_normal_use_ceilings(
    _payload(
        _entry("Alpha Ionone", ["alpha ionone"], 1.0),
        _entry("Alpha Isomethyl Ionone", ["alpha isomethyl ionone"], 2.0),
        _entry("Beta Ionone", ["beta ionone"], 3.0),
        _entry("Dihydro Beta Ionone", ["dihydro beta ionone"], 4.0),
        _entry("Aldehyde C12 MNA", ["aldehyde c12 mna", "methyl nonyl acetaldehyde"], 5.0),
        _entry("Aldehyde C12 Lauric", ["aldehyde c 12 lauric", "dodecanal"], 6.0),
    )
)


@pytest.mark.parametrize(
    ("probe", "expected"),
    [
        ("alpha ionone alpha ionone neat as supplied neat", "Alpha Ionone"),
        (
            "alpha isomethyl ionone alpha isomethyl ionone neat as supplied as supplied oily liquid neat",
            "Alpha Isomethyl Ionone",
        ),
        ("beta ionone beta ionone neat as supplied neat", "Beta Ionone"),
        ("dihydro beta ionone dihydro beta ionone neat as supplied neat", "Dihydro Beta Ionone"),
        ("aldehyde c12 mna neat aldehyde c12 mna neat as supplied neat", "Aldehyde C12 MNA"),
        ("aldehyde c 12 lauric dodecanal neat as supplied neat", "Aldehyde C12 Lauric"),
        ("Aldehyde C-12 MNA (1% in ethanol)", "Aldehyde C12 MNA"),
        ("aldehyde c11 undecylenic neat", None),
        ("allyl ionone ketone v neat", None),
        ("betaionone neat", None),
    ],
)
def test_matching_is_whole_word_and_longest_phrase_wins(probe: str, expected: str | None) -> None:
    matched = ceilings.match_normal_use_ceiling(probe, SPECIFIC)
    assert (matched.material if matched else None) == expected


def test_profile_and_synergy_words_cannot_select_a_ceiling(fixture_ceilings: None) -> None:
    candidate = _candidate("Rose Absolute", 1.0)
    candidate.profile = SimpleNamespace(synergies=("alpha damascone",), texture="alpha damascone")
    candidate.stock.category = "Alpha Damascone accords"
    assert planner._normal_use_ceiling(candidate) is None
    assert planner._normal_use_ceiling_cap_ul(candidate, 6000) is None


def test_cap_arithmetic_for_neat_and_ten_percent_stock(fixture_ceilings: None) -> None:
    # 0.2% active of 6000 uL = 12 uL active.
    assert planner._normal_use_ceiling_cap_ul(_candidate("Alpha Damascone", 1.0), 6000) == 12
    assert planner._normal_use_ceiling_cap_ul(_candidate("Alpha Damascone (10%)", 0.1), 6000) == 120
    # Floored, never below 1 uL.
    assert planner._normal_use_ceiling_cap_ul(_candidate("Alpha Damascone", 1.0), 1999) == 3
    assert planner._normal_use_ceiling_cap_ul(_candidate("Alpha Damascone", 1.0), 100) == 1


def _choice(candidate: Any, *, function: str = "character", max_raw_share: float | None = None) -> Any:
    role = planner.RoleSpec("r", "Role", "heart", function, 0.1, (), max_raw_share=max_raw_share)
    return planner.Choice(role, candidate, 1.0, ())


def test_design_cap_is_minimum_of_hard_ceiling_and_role_caps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "ceilings.json"
    path.write_text(
        json.dumps(
            _payload(
                _entry("Alpha Damascone", ["alpha damascone"], 0.2),
                _entry("Rose Oxide", ["rose oxide"], 50),
                _entry("Indole", ["indole"], 0.01),
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ceilings, "NORMAL_USE_CEILINGS_PATH", path)
    # Ceiling below the 30% role cap.
    assert planner._design_cap_ul(_choice(_candidate("Alpha Damascone", 1.0)), 6000) == 12
    # Hard cap (rose oxide 0.1% active) below a loose ceiling: hard cap stands.
    assert planner._design_cap_ul(_choice(_candidate("Rose Oxide", 1.0)), 6000) == 6
    # Ceiling below the hard cap (indole 0.05% active): ceiling wins.
    assert planner._design_cap_ul(_choice(_candidate("Indole", 1.0)), 6000) == 1
    # Without a ceiling, the role cap is unchanged.
    assert planner._design_cap_ul(_choice(_candidate("Hedione", 1.0)), 6000) == 1800


def _rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    return list(result["optimized_formula"]["rows"])


def test_chypre_alpha_damascone_respects_fixture_ceiling(fixture_ceilings: None) -> None:
    result = design_inventory_formula(idea=CHYPRE_IDEA, formula_name=CHYPRE_NAME)
    formula = result["optimized_formula"]
    liquid_total = Decimal(formula["separate_totals"]["liquid_total_ul"])
    assert liquid_total == 6000
    rows = _rows(result)
    assert sum(Decimal(row["amount_decimal"]) for row in rows if row["amount_unit"] == "uL") == 6000
    damascone = [row for row in rows if row["material"].casefold() == "alpha damascone"]
    assert damascone, [row["material"] for row in rows]
    for row in damascone:
        active = Decimal(row["amount_decimal"]) * Decimal(row["stock_fraction_decimal"])
        assert active <= Decimal("0.002") * liquid_total
        assert row[CEILING_KEY] == 0.2
    assert all(CEILING_KEY not in row for row in rows if row not in damascone)


def test_empty_shipped_file_leaves_chypre_rows_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    with_feature = _rows(design_inventory_formula(idea=CHYPRE_IDEA, formula_name=CHYPRE_NAME))
    assert all(CEILING_KEY not in row for row in with_feature)
    monkeypatch.setattr(planner, "match_normal_use_ceiling", lambda *_args, **_kwargs: None)
    without_feature = _rows(design_inventory_formula(idea=CHYPRE_IDEA, formula_name=CHYPRE_NAME))
    assert with_feature == without_feature
