"""Tests for engine.supplier_offers.pw_prices (PerfumersWorld YAML prices)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from engine.supplier_offers.pw_prices import (
    SOURCE_MATERIALS_YAML,
    cost_per_bottle_thb,
    latest_pw_price,
    neat_thb_per_g,
    pw_price_index,
    pw_product_url,
    upfront_usd,
)

RATE = Decimal("33.55")


def _record(name: str, supplier: str, other: str = "    other: {}\n") -> str:
    return (
        f"- canonical_name: {name}\n"
        "  aliases: []\n"
        "  cas: null\n"
        "  user_in_inventory: false\n"
        "  supplier:\n"
        f"{supplier}"
        f"{other}"
        "  families: []\n"
    )


def _alternates(*entries: tuple[str, str, str | None]) -> str:
    lines = ["    other:\n", "      pw_alternate_forms:\n"]
    for sku, price, form in entries:
        lines.append(f"      - sku: {sku}\n")
        lines.append(f"        price_usd_per_g: {price}\n")
        if form is not None:
            lines.append(f"        form: {form}\n")
    return "".join(lines)


def _supplier(sku: str, price: str | None, form: str | None, day: str | None) -> str:
    lines = [f"    perfumersworld_sku: {sku}\n"]
    if price is not None:
        lines.append(f"    perfumersworld_price_usd_per_g: {price}\n")
    if form is not None:
        lines.append(f"    perfumersworld_form: {form}\n")
    if day is not None:
        lines.append(f"    perfumersworld_snapshot_date: {day}\n")
    return "".join(lines)


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    a_records = [
        _record("Alpha Neat", _supplier("7AA00001", "7.3", "neat", "'2026-04-11'")),
        _record("Alpha Ten DPG", _supplier("4AA00002", "0.45", "10.0% in DPG", "'2026-04-11'")),
        _record("Alpha One DPG", _supplier("4AA00003", "0.12", "1.0% in DPG", "'2026-04-11'")),
        _record("Alpha Ten Short", _supplier("4AA00004", "0.6", "10% in DPG", "'2026-04-11'")),
    ]
    b_records = [
        _record("Beta Prefix Five", _supplier("5BB00005", "0.55", "neat", "'2026-04-11'")),
        _record("Beta No Date", _supplier("4BB00006", "1.2", "neat", None)),
        _record("Beta Bad Date", _supplier("4BB00009", "1.2", "neat", "'sometime'")),
        _record("Beta No Form", _supplier("4BB00007", "1.2", None, "'2026-04-11'")),
        _record(
            "Beta Free Text",
            _supplier(
                "4BB00008", "2.5", "'viscous resinoid; about 30% benzyl benzoate'", "'2026-04-11'"
            ),
        ),
        _record("Beta Zero Price", _supplier("4BB00010", "0", "neat", "'2026-04-11'")),
        _record("Beta No Price", _supplier("4BB00011", None, "neat", "'2026-04-11'")),
        _record(
            "Beta Orris Parent",
            _supplier("8BB00020", "21.5", "neat", "'2026-04-11'"),
            _alternates(
                ("5BB00021", "2.2", "10.0% in DPG"),
                ("5BB00022", "3.0", "neat"),
                ("4BB00023", "4.0", None),
            ),
        ),
        _record(
            "Beta Undated Parent",
            _supplier("4BB00024", "1.0", "neat", None),
            _alternates(("4BB00025", "0.5", "10.0% in DPG")),
        ),
    ]
    (tmp_path / "A.yaml").write_text("".join(a_records), encoding="utf-8")
    (tmp_path / "B.yaml").write_text("".join(b_records), encoding="utf-8")
    return tmp_path


def test_neat_price_fields(data_dir: Path) -> None:
    p = latest_pw_price("7AA00001", data_dir=data_dir)
    assert p is not None
    assert p.sku == "7AA00001"
    assert p.material_name == "Alpha Neat"
    assert p.usd_per_g == Decimal("7.3")
    assert str(p.usd_per_g) == "7.3"
    assert p.form == "neat"
    assert p.strength == Decimal(1)
    assert p.solvent is None
    assert p.usd_per_active_g == Decimal("7.3")
    assert p.observed_on == date(2026, 4, 11)
    assert p.source == SOURCE_MATERIALS_YAML == "materials_yaml"
    assert p.in_stock == "UNKNOWN"


def test_ten_percent_dpg(data_dir: Path) -> None:
    p = latest_pw_price("4AA00002", data_dir=data_dir)
    assert p is not None
    assert p.form == "10.0% in DPG"
    assert p.strength == Decimal("0.1")
    assert p.solvent == "DPG"
    assert p.usd_per_active_g == Decimal("0.45") / Decimal("0.1") == Decimal("4.5")
    assert neat_thb_per_g(p, RATE) == Decimal("0.45") * RATE / Decimal("0.1")
    assert neat_thb_per_g(p, RATE) == Decimal("150.975")


def test_one_percent_dpg(data_dir: Path) -> None:
    p = latest_pw_price("4AA00003", data_dir=data_dir)
    assert p is not None
    assert p.strength == Decimal("0.01")
    assert p.solvent == "DPG"
    assert p.usd_per_active_g == Decimal("12")


def test_ten_percent_without_decimal(data_dir: Path) -> None:
    p = latest_pw_price("4AA00004", data_dir=data_dir)
    assert p is not None
    assert p.form == "10% in DPG"
    assert p.strength == Decimal("0.1")
    assert p.usd_per_active_g == Decimal("6")


def test_prefix_five_marked_neat_shows_pack_price_only(data_dir: Path) -> None:
    p = latest_pw_price("5BB00005", data_dir=data_dir)
    assert p is not None
    assert p.form == "neat"
    assert p.strength is None
    assert p.usd_per_active_g is None
    assert neat_thb_per_g(p, RATE) is None
    assert cost_per_bottle_thb(p, RATE, Decimal("0.01")) is None
    assert upfront_usd(p) == Decimal("5") * Decimal("0.55") + Decimal("0.90")


@pytest.mark.parametrize(
    "sku",
    ["4BB00006", "4BB00009", "4BB00007", "4BB00010", "4BB00011", "NOPE123"],
    ids=["missing-date", "bad-date", "missing-form", "zero-price", "missing-price", "unknown"],
)
def test_unusable_records_return_none(data_dir: Path, sku: str) -> None:
    assert latest_pw_price(sku, data_dir=data_dir) is None
    assert sku not in pw_price_index(data_dir=data_dir)


def test_free_text_form_keeps_pack_price(data_dir: Path) -> None:
    p = latest_pw_price("4BB00008", data_dir=data_dir)
    assert p is not None
    assert p.form == "viscous resinoid; about 30% benzyl benzoate"
    assert p.strength is None
    assert p.solvent is None
    assert p.usd_per_active_g is None
    assert cost_per_bottle_thb(p, RATE, Decimal("0.01")) is None
    assert upfront_usd(p, Decimal("10")) == Decimal("25.90")


def test_lookup_strips_whitespace(data_dir: Path) -> None:
    p = latest_pw_price("  7AA00001\n", data_dir=data_dir)
    assert p is not None and p.sku == "7AA00001"


def test_upfront_default_five_grams(data_dir: Path) -> None:
    p = latest_pw_price("7AA00001", data_dir=data_dir)
    assert p is not None
    assert upfront_usd(p) == Decimal("37.40")


def test_cost_per_bottle_neat(data_dir: Path) -> None:
    p = latest_pw_price("7AA00001", data_dir=data_dir)
    assert p is not None
    cost = cost_per_bottle_thb(p, RATE, Decimal("0.01"))
    assert cost == Decimal("7.30") * RATE * Decimal("0.01") * Decimal("6")
    assert cost == Decimal("14.6949")


def test_index_contents_and_read_only(data_dir: Path) -> None:
    index = pw_price_index(data_dir=data_dir)
    assert set(index) == {
        "7AA00001",
        "4AA00002",
        "4AA00003",
        "4AA00004",
        "5BB00005",
        "4BB00008",
        "8BB00020",
        "5BB00021",
        "5BB00022",
    }
    with pytest.raises(TypeError):
        index["X"] = index["7AA00001"]  # type: ignore[index]


def test_index_refreshes_when_yaml_changes(data_dir: Path) -> None:
    assert latest_pw_price("4CC00012", data_dir=data_dir) is None
    (data_dir / "C.yaml").write_text(
        _record("Gamma New", _supplier("4CC00012", "3.1", "10.0% in PG", "'2026-05-01'")),
        encoding="utf-8",
    )
    p = latest_pw_price("4CC00012", data_dir=data_dir)
    assert p is not None
    assert p.solvent == "PG"
    assert p.observed_on == date(2026, 5, 1)


def test_to_json(data_dir: Path) -> None:
    p = latest_pw_price("4AA00002", data_dir=data_dir)
    assert p is not None
    assert p.to_json() == {
        "sku": "4AA00002",
        "material_name": "Alpha Ten DPG",
        "usd_per_g": "0.45",
        "form": "10.0% in DPG",
        "strength": "0.1",
        "solvent": "DPG",
        "usd_per_active_g": "4.5",
        "observed_on": "2026-04-11",
        "source": "materials_yaml",
        "in_stock": "UNKNOWN",
        "parent_sku": None,
        "product_url": "https://www.perfumersworld.com/view.php?pro_id=4AA00002",
    }
    prefix_five = latest_pw_price("5BB00005", data_dir=data_dir)
    assert prefix_five is not None
    assert prefix_five.to_json()["strength"] is None
    assert prefix_five.to_json()["usd_per_active_g"] is None


def test_main_sku_has_no_parent(data_dir: Path) -> None:
    p = latest_pw_price("8BB00020", data_dir=data_dir)
    assert p is not None
    assert p.parent_sku is None
    assert p.usd_per_g == Decimal("21.5")
    assert p.strength == Decimal(1)


def test_alternate_form_is_its_own_price(data_dir: Path) -> None:
    p = latest_pw_price("5BB00021", data_dir=data_dir)
    assert p is not None
    assert p.sku == "5BB00021"
    assert p.parent_sku == "8BB00020"
    assert p.material_name == "Beta Orris Parent"
    assert p.form == "10.0% in DPG"
    assert p.usd_per_g == Decimal("2.2")
    assert p.strength == Decimal("0.1")
    assert p.solvent == "DPG"
    assert p.usd_per_active_g == Decimal("22")
    assert p.observed_on == date(2026, 4, 11)
    assert p.source == "materials_yaml"
    assert p.in_stock == "UNKNOWN"
    assert p.to_json()["parent_sku"] == "8BB00020"
    assert p.to_json()["product_url"].endswith("pro_id=5BB00021")


def test_alternate_prefix_five_marked_neat_has_no_strength(data_dir: Path) -> None:
    p = latest_pw_price("5BB00022", data_dir=data_dir)
    assert p is not None
    assert p.parent_sku == "8BB00020"
    assert p.strength is None
    assert cost_per_bottle_thb(p, RATE, Decimal("0.01")) is None
    assert upfront_usd(p) == Decimal("15.90")


@pytest.mark.parametrize(
    "sku", ["4BB00023", "4BB00025"], ids=["alternate-missing-form", "parent-missing-date"]
)
def test_unusable_alternates_return_none(data_dir: Path, sku: str) -> None:
    assert latest_pw_price(sku, data_dir=data_dir) is None


def test_product_url() -> None:
    assert pw_product_url("7WX21054") == "https://www.perfumersworld.com/view.php?pro_id=7WX21054"


def test_real_repo_sku_7wx21054() -> None:
    p = latest_pw_price("7WX21054")
    assert p is not None
    assert p.usd_per_g == Decimal("7.3")
    assert p.form == "neat"
    assert p.strength == Decimal(1)
    assert p.observed_on == date(2026, 4, 11)
    assert p.source == "materials_yaml"
    assert p.in_stock == "UNKNOWN"
    assert upfront_usd(p) == Decimal("37.40")


def test_real_repo_alternate_5ia07847() -> None:
    p = latest_pw_price("5IA07847")
    assert p is not None
    assert p.parent_sku == "8IA00344"
    assert p.usd_per_g == Decimal("2.2")
    assert p.strength == Decimal("0.1")
    assert p.solvent == "DPG"
    assert p.observed_on == date(2026, 4, 11)
