"""chemistry_stability asks for the house BHT pre-charge under IFRA 184/186/187.

IFRA Standards 184 (Pinacea derivatives), 186 (Limonene) and 187 (Linalool) say
these materials, and naturals holding substantial amounts of them, should only be
used with peroxides kept low, "for instance by adding antioxidants at the time of
production". The gate looks for an antioxidant row; it makes no shelf-life claim
and does not judge the row's dose.
"""

from __future__ import annotations

import pytest

import engine.pipeline.gates as gates_module
import scripts.formula_release_gate as release_cli
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from scripts.format_pipeline_analysis import build_gate_summary

BHT_ROW = "BHT 5% w/v in ethanol"


def _stock(basis: str, fraction: float = 1.0) -> dict[str, object]:
    return {"fraction": fraction, "fraction_basis": basis, "carrier": "", "declared": True}


def _w_v_state(ingredients: dict[str, float], dilutions: dict[str, float] | None = None):
    dilutions = {name: 1.0 for name in ingredients} | (dilutions or {})
    return build_formula_state(
        ingredients,
        dilutions,
        stock_specs={
            name: _stock("mass_per_volume", dilutions[name]) for name in ingredients
        },
    )


def _chemistry(state, config: ReleaseGateConfig | None = None, **kwargs):
    return gates_module._gate_chemistry_stability(
        state, config or ReleaseGateConfig(audit_enabled=False), **kwargs
    )


CITRUS = {"Bergamot FCF Oil Sicilian": 40.0, "Linalool": 10.0, "Hedione": 30.0, "Iso E Super": 20.0}


def test_in_scope_materials_without_an_antioxidant_row_warn_and_name_the_bht_precharge():
    result = _chemistry(_w_v_state(CITRUS))

    assert result.status == "WARN"
    assert (
        "no antioxidant row: Bergamot FCF Oil Sicilian (limonene 40%, linalool 9%), "
        "Linalool fall under IFRA 186/187 (antioxidants at production); "
        "add BHT 5% w/v in ethanol, 120 uL per 30 mL of finished perfume (4 uL per mL) "
        "as a pre-charge"
    ) in result.detail

    antioxidant = result.data["antioxidant"]
    assert antioxidant["status"] == "ADVISED"
    assert antioxidant["antioxidant_rows"] == []
    rows = {row["material"]: row for row in antioxidant["in_scope_materials"]}
    assert set(rows) == {"Bergamot FCF Oil Sicilian", "Linalool"}

    bergamot = rows["Bergamot FCF Oil Sicilian"]
    assert bergamot["standards"] == ["IFRA_STD_186", "IFRA_STD_187"]
    assert {
        (b["basis"], b["constituent"], b["share_of_material"]) for b in bergamot["bases"]
    } == {
        ("modelled_constituent_share", "limonene", 0.395),
        ("modelled_constituent_share", "linalool", 0.09),
    }
    assert all(b["constituent_profile"] and b["composition_authority"] for b in bergamot["bases"])
    assert bergamot["active_mass_pct"] == pytest.approx(40.0, abs=0.01)
    assert bergamot["active_mg"] == pytest.approx(40.0)

    linalool = rows["Linalool"]
    assert linalool["bases"] == [
        {"standard": "IFRA_STD_187", "basis": "ifra_table", "ifra_entry": "Linalool"}
    ]
    assert linalool["active_mass_pct"] == pytest.approx(10.0, abs=0.01)

    assert antioxidant["recommended_precharge"]["material"] == BHT_ROW
    assert antioxidant["recommended_precharge"]["raw_ul"] == 120.0
    assert antioxidant["recommended_precharge"]["bht_mg"] == 6.0
    assert antioxidant["recommended_precharge"]["operation"] == "PRECHARGE"
    assert antioxidant["recommended_precharge"]["batch_volume_known"] is False
    assert antioxidant["bench_addition"] == (
        "Bench addition: BHT 5% w/v in ethanol, 120 uL pre-charge per 30 mL of finished "
        "perfume, 4 uL per mL (antioxidant, IFRA 186/187)"
    )
    assert antioxidant["dose_threshold"] is None
    assert antioxidant["constituent_screen_fraction"] == 0.05
    assert antioxidant["constituent_screen_basis"].startswith("engine screening value")
    assert "IFRA does not define 'substantial amounts'" in antioxidant["constituent_screen_basis"]

    notes = {note["standard"]: note["quotes"] for note in antioxidant["ifra_notes"]}
    assert set(notes) == {"IFRA_STD_186", "IFRA_STD_187"}
    for quotes in notes.values():
        assert any("adding antioxidants at the time of production" in q for q in quotes)
        assert any("0.1% BHT" in q for q in quotes)


def test_an_antioxidant_row_passes_and_records_its_dose_next_to_the_house_dose():
    state = _w_v_state(CITRUS | {BHT_ROW: 0.6}, {BHT_ROW: 0.05})

    result = _chemistry(state)

    assert result.status == "PASS"
    assert "antioxidant" not in result.detail
    antioxidant = result.data["antioxidant"]
    assert antioxidant["status"] == "PRESENT"
    assert antioxidant["bench_addition"] is None
    assert antioxidant["recommended_precharge"] is None
    assert antioxidant["dose_adequacy"] == "NOT_ASSESSED"
    assert antioxidant["antioxidant_rows"] == [
        {
            "material": BHT_ROW,
            "source": "formula_row",
            "raw_ul": 0.6,
            "fraction": 0.05,
            "fraction_basis": "mass_per_volume",
            "active_mg": 0.03,
            "house_dose_raw_ul": 120.0,
            "house_dose_bht_mg": 6.0,
        }
    ]
    # The in-scope materials are still listed, so the record shows what the row covers.
    assert {row["material"] for row in antioxidant["in_scope_materials"]} == {
        "Bergamot FCF Oil Sicilian",
        "Linalool",
    }


# The formula-file parser keeps a BHT row out of ingredients_ul and lists it here.
PARSED_PRECHARGE_ROW = {
    "material": BHT_ROW,
    "amount": 120.0,
    "amount_unit": "uL",
    "raw_ul": 120.0,
    "fraction": 0.05,
    "fraction_basis": "mass_per_volume",
    "carrier": "ethanol",
    "declared": True,
    "strength_text": "5% w/v in ethanol",
    "active_mg": 6.0,
    "active_mg_basis": "w/v stock by volume: uL x g/mL = mg",
    "category": "technical",
    "stock_component_role": "technical_active",
    "operation": "PRECHARGE",
    "role": "antioxidant, not an odour row",
    "odour_row": False,
}


def test_a_declared_technical_precharge_row_counts_as_the_antioxidant():
    result = _chemistry(
        _w_v_state(CITRUS), declared_antioxidant_rows=(PARSED_PRECHARGE_ROW,)
    )

    assert result.status == "PASS"
    antioxidant = result.data["antioxidant"]
    assert antioxidant["status"] == "PRESENT"
    assert antioxidant["bench_addition"] is None
    assert antioxidant["antioxidant_rows"] == [
        {
            "material": BHT_ROW,
            "source": "technical_precharge_row",
            "raw_ul": 120.0,
            "fraction": 0.05,
            "fraction_basis": "mass_per_volume",
            "active_mg": 6.0,
            "house_dose_raw_ul": 120.0,
            "house_dose_bht_mg": 6.0,
        }
    ]


def test_gate_formula_reads_parser_and_composer_precharge_rows():
    from engine.pipeline.antioxidant import house_bht_precharge

    base = {
        "number": 1,
        "name": "Antioxidant Citrus",
        "ingredients_ul": {"Bergamot FCF Oil Sicilian": 300.0, "Hedione": 300.0},
        "dilutions": {"Bergamot FCF Oil Sicilian": 1.0, "Hedione": 1.0},
        "stock_specs": {
            name: _stock("mass_per_volume") for name in ("Bergamot FCF Oil Sicilian", "Hedione")
        },
    }
    config = ReleaseGateConfig(expected_concentrate_ul=600.0, brief="generic", audit_enabled=False)

    def chemistry(formula):
        report = gate_formula(formula, config)
        return {g.gate: g for g in report.gates}["chemistry_stability"]

    assert chemistry(base).data["antioxidant"]["status"] == "ADVISED"
    parsed = chemistry({**base, "technical_precharge_rows": [PARSED_PRECHARGE_ROW]})
    composed = chemistry(
        {**base, "technical_rows": [house_bht_precharge(30.0).as_mapping()]}
    )
    for result in (parsed, composed):
        assert result.data["antioxidant"]["status"] == "PRESENT"
        assert "no antioxidant row" not in result.detail
        (row,) = result.data["antioxidant"]["antioxidant_rows"]
        assert row["source"] == "technical_precharge_row"
        assert row["raw_ul"] == 120.0
        assert row["active_mg"] == 6.0


def test_declared_antioxidant_rows_keeps_only_antioxidant_technical_rows():
    formula = {
        "technical_precharge_rows": [PARSED_PRECHARGE_ROW, {"material": "Ethanol", "raw_ul": 5.0}],
        "technical_rows": [{"material": "alpha-Tocopherol", "raw_ul": 3.0}],
    }

    rows = gates_module.declared_antioxidant_rows(formula)

    assert [row["material"] for row in rows] == [BHT_ROW, "alpha-Tocopherol"]
    assert gates_module.declared_antioxidant_rows({"ingredients_ul": {}}) == ()


def test_pinaceae_comes_from_the_ifra_table_and_not_from_a_pinene_share():
    result = _chemistry(_w_v_state({"Pine EO": 10.0, "Juniper Berry EO": 10.0, "Hedione": 80.0}))

    rows = {row["material"]: row for row in result.data["antioxidant"]["in_scope_materials"]}
    assert rows["Pine EO"]["standards"] == ["IFRA_STD_184"]
    assert rows["Pine EO"]["bases"][0]["basis"] == "ifra_table"
    # Juniper is not a Pinaceae oil: only its modelled limonene brings it in, under 186.
    assert rows["Juniper Berry EO"]["standards"] == ["IFRA_STD_186"]
    assert "IFRA 184/186" in result.detail


@pytest.mark.parametrize(("share", "in_scope"), [(0.0499, False), (0.05, True)])
def test_a_natural_counts_from_the_five_percent_screening_share(monkeypatch, share, in_scope):
    def constituents(name):
        if "lavender" in name.lower():
            return [("linalool", share, 154.25), ("linalyl acetate", 0.4, 196.29)]
        return None

    monkeypatch.setattr(gates_module, "get_constituents", constituents)
    result = _chemistry(_w_v_state({"Lavender EO": 20.0, "Hedione": 80.0}))

    materials = [row["material"] for row in result.data["antioxidant"]["in_scope_materials"]]
    assert materials == (["Lavender EO"] if in_scope else [])
    assert ("no antioxidant row" in result.detail) is in_scope


def test_stereo_named_constituents_count_as_limonene_and_linalool(monkeypatch):
    monkeypatch.setattr(
        gates_module,
        "get_constituents",
        lambda name: [("(R)-(+)-Limonene", 0.3, 136.2), ("l-Linalool", 0.1, 154.2)]
        if "orange" in name.lower()
        else None,
    )
    result = _chemistry(_w_v_state({"Orange Sweet Oil": 20.0, "Hedione": 80.0}))

    row = result.data["antioxidant"]["in_scope_materials"][0]
    assert row["standards"] == ["IFRA_STD_186", "IFRA_STD_187"]
    assert "Orange Sweet Oil (limonene 30%, linalool 10%) falls under IFRA 186/187" in (
        result.detail
    )


@pytest.mark.parametrize(
    ("volume_ml", "source", "detail_dose", "bench"),
    [
        (
            50.0,
            "formula_title",
            "add BHT 5% w/v in ethanol, 200 uL as a pre-charge",
            "Bench addition: BHT 5% w/v in ethanol, 200 uL pre-charge "
            "(antioxidant, IFRA 186/187; 10 mg BHT for the 50 mL batch)",
        ),
        (
            30.0,
            "cli",
            "add BHT 5% w/v in ethanol, 120 uL as a pre-charge",
            "Bench addition: BHT 5% w/v in ethanol, 120 uL pre-charge "
            "(antioxidant, IFRA 186/187; 6 mg BHT for the 30 mL batch)",
        ),
        (
            7.5,
            "mass_card_concentrate_only",
            "add BHT 5% w/v in ethanol, 120 uL per 30 mL of finished perfume (4 uL per mL)",
            "Bench addition: BHT 5% w/v in ethanol, 120 uL pre-charge per 30 mL of finished "
            "perfume, 4 uL per mL (antioxidant, IFRA 186/187)",
        ),
    ],
)
def test_the_precharge_follows_the_finished_batch_volume_when_the_gate_knows_it(
    volume_ml, source, detail_dose, bench
):
    config = ReleaseGateConfig(
        audit_enabled=False, batch_volume_ml=volume_ml, batch_volume_source=source
    )

    result = _chemistry(_w_v_state(CITRUS), config)

    assert detail_dose in result.detail
    assert result.data["antioxidant"]["bench_addition"] == bench


def test_hold_path_keeps_hold_and_carries_the_antioxidant_advice():
    # D-Limonene is a w/w stock with no stock-solution density, Hedione's basis is
    # undeclared: neither has an authoritative active mass.
    state = build_formula_state(
        {"D-Limonene": 75.0, "Hedione": 25.0},
        {"D-Limonene": 0.25, "Hedione": 0.25},
        stock_specs={
            "D-Limonene": _stock("mass_fraction", 0.25),
            "Hedione": _stock("unspecified", 0.25),
        },
    )

    result = _chemistry(state)

    assert result.status == "HOLD"
    assert result.data["assessment"] == "UNKNOWN"
    assert "authoritative active mass is unavailable" in result.detail
    assert (
        "no antioxidant row: D-Limonene falls under IFRA 186 (antioxidants at production); "
        "add BHT 5% w/v in ethanol, 120 uL per 30 mL"
    ) in result.detail
    antioxidant = result.data["antioxidant"]
    assert antioxidant["status"] == "ADVISED"
    assert antioxidant["in_scope_materials"][0]["material"] == "D-Limonene"
    assert antioxidant["in_scope_materials"][0]["active_mass_pct"] is None
    assert antioxidant["bench_addition"].startswith(
        "Bench addition: BHT 5% w/v in ethanol, 120 uL pre-charge"
    )


def test_fail_stays_fail_and_also_carries_the_antioxidant_advice():
    state = _w_v_state({"Aldehyde C10": 60.0, "Indole": 20.0, "Linalool": 20.0})

    result = _chemistry(state)

    assert result.status == "FAIL"
    assert result.detail.startswith("Schiff-base risk")
    assert "no antioxidant row: Linalool falls under IFRA 187" in result.detail
    assert result.data["antioxidant"]["status"] == "ADVISED"


def test_formula_with_nothing_in_scope_gets_no_antioxidant_advice():
    result = _chemistry(_w_v_state({"Hedione": 50.0, "Iso E Super": 40.0, "Habanolide": 10.0}))

    assert result.status == "PASS"
    antioxidant = result.data["antioxidant"]
    assert antioxidant["status"] == "NOT_IN_SCOPE"
    assert antioxidant["in_scope_materials"] == []
    assert antioxidant["bench_addition"] is None
    assert antioxidant["ifra_notes"] == []


def test_antioxidant_check_makes_no_shelf_life_or_aging_claim():
    result = _chemistry(_w_v_state(CITRUS))

    assert "shelf_life_days" not in result.data
    assert result.data["aging_claim"]["claim_authorized"] is False
    message = result.data["antioxidant"]["message"].lower()
    for word in ("shelf", "aging", "ageing", "maturation", "keeps", "months", "weeks"):
        assert word not in message


def test_gate_summary_prints_the_bench_addition_line():
    report = gate_formula(
        {
            "number": 1,
            "name": "Antioxidant Citrus",
            "ingredients_ul": {"Bergamot FCF Oil Sicilian": 300.0, "Hedione": 300.0},
            "dilutions": {"Bergamot FCF Oil Sicilian": 1.0, "Hedione": 1.0},
            "stock_specs": {
                name: _stock("mass_per_volume") for name in ("Bergamot FCF Oil Sicilian", "Hedione")
            },
        },
        ReleaseGateConfig(expected_concentrate_ul=600.0, brief="generic", audit_enabled=False),
    )

    text = "\n".join(build_gate_summary(report.as_dict()))

    assert "chemistry_stability: no antioxidant row: Bergamot FCF Oil Sicilian" in text
    assert (
        "  Bench addition: BHT 5% w/v in ethanol, 120 uL pre-charge per 30 mL of finished "
        "perfume, 4 uL per mL (antioxidant, IFRA 186/187)"
    ) in text


def test_gate_summary_has_no_bench_line_when_nothing_is_advised():
    gates = [
        {
            "gate": "chemistry_stability",
            "status": "PASS",
            "detail": "",
            "data": {"antioxidant": {"status": "PRESENT", "bench_addition": None}},
        }
    ]

    assert not any("Bench addition" in line for line in build_gate_summary({"gates": gates}))


def test_release_cli_prints_the_bench_addition_for_the_bottle_size(tmp_path, capsys):
    path = tmp_path / "citrus.md"
    path.write_text(
        "# CLI Citrus 50 mL\n\n"
        "| Material | Dilution | uL |\n"
        "|---|---|---:|\n"
        "| Bergamot FCF Oil Sicilian | neat | 100 |\n"
        "| Hedione | neat | 100 |\n",
        encoding="utf-8",
    )

    release_cli.main(
        [
            "--formula-file",
            str(path),
            "--expected-concentrate-ul",
            "200",
            "--brief",
            "generic",
            "--no-audit",
            "--print-analysis",
        ]
    )
    out = capsys.readouterr().out

    bench = (
        "Bench addition: BHT 5% w/v in ethanol, 200 uL pre-charge "
        "(antioxidant, IFRA 186/187; 10 mg BHT for the 50 mL batch)"
    )
    # Once in the gate lines and once in the analysis Gate Summary.
    assert out.count(bench) == 2


def test_a_long_scope_names_the_four_biggest_rows_and_counts_the_rest():
    many = {
        "Bergamot FCF Oil Sicilian": 50.0,
        "Linalool": 40.0,
        "Lavender EO": 30.0,
        "Coriander Seed EO": 20.0,
        "Grapefruit FCF": 10.0,
        "Hedione": 30.0,
    }
    result = _chemistry(_w_v_state(many))

    assert result.status == "WARN"
    assert "Grapefruit FCF" not in result.detail
    assert "Coriander Seed EO" in result.detail
    assert "and 1 more fall under IFRA" in result.detail
    in_scope = result.data["antioxidant"]["in_scope_materials"]
    assert "Grapefruit FCF" in {row["material"] for row in in_scope}
