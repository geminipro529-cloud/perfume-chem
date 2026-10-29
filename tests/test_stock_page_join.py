"""The Stock page shows one row per bottle: the checks' own record where they have one.

``materialize_personal_inventory`` joins the gate's stock list with Kenny's hand-kept
inventory.txt. These tests give it small made-up lists of both, so they keep holding as
the real stock list changes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import engine.personal_inventory as personal_inventory
from engine.inventory_parser import CurrentInventoryMaterialization, InventoryMaterial
from engine.name_utils import normalize_name
from engine.personal_inventory import LIVE_TEXT_AUTHORITY, materialize_personal_inventory
from tests.reheld_overlay import neat_ambrettolide_still_owned  # noqa: F401 (fixture)

V5 = "CURRENT_INVENTORY_MASTER_V5_EXTERNAL_SNAPSHOT"
HIS_WORD = "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20261015"


def _record(stock_id, name, dilution, *, identity, carrier="", basis="unspecified", authority=V5, raw_name=None,
            ready=False, completion=""):
    return InventoryMaterial(
        name=name, dilution=dilution, category="test", raw_name=raw_name or name, status="owned",
        fraction_basis=basis, carrier=carrier, identity_name=identity, stock_id=stock_id, authority=authority,
        execution_ready=ready, completion_event_sha256=completion,
    )


def _line(raw_name, identity, dilution, *, carrier="", basis="unspecified"):
    return InventoryMaterial(
        name=identity, dilution=dilution, category="test", raw_name=raw_name, status="owned",
        fraction_basis=basis, carrier=carrier, identity_name=identity,
    )


@pytest.fixture
def join(tmp_path: Path, monkeypatch):
    """The projection of made-up gate records and inventory.txt lines."""

    def run(records, lines):
        monkeypatch.setattr(personal_inventory, "parse_inventory", lambda **_kwargs: tuple(lines))
        canonical = CurrentInventoryMaterialization(
            stocks=tuple(records), requirements=(), source_workbook_sha256="test", snapshot_sha256="test",
        )
        return materialize_personal_inventory(canonical=canonical, addition_path=tmp_path / "additions.jsonl")

    return run


def _rows(projection, identity):
    return [s for s in projection.stocks if (s.identity_name or s.name) == identity]


def test_a_record_leaving_blank_the_solvent_its_line_names_is_shown_as_that_bottle(join):
    # The workbook has "Geraniol 10%" with no solvent; inventory.txt says 10% in DPG. Before,
    # the line's own row hid the record, so its Stock page form could never be opened.
    record = _record("v5:geraniol-10", "Geraniol 10%", 0.1, identity="Geraniol")
    line = _line("Geraniol (10% DPG)", "Geraniol", 0.1, carrier="dpg", basis="mass_fraction")

    projection = join([record], [line])

    assert [s.stock_id for s in _rows(projection, "Geraniol")] == ["v5:geraniol-10"]
    ((text_id, record_id),) = projection.merged_text_stock_ids
    assert text_id.startswith("inventory:text-design-only:") and record_id == "v5:geraniol-10"
    assert projection.inventory_text_notes == (("v5:geraniol-10", "Your inventory list says 10% w/w in DPG"),)
    # The record is shown as the checks have it; the line's solvent goes to design rows only.
    (shown,) = _rows(projection, "Geraniol")
    assert shown.carrier == "" and shown.fraction_basis == "unspecified"
    assert projection.inventory_text_forms == (("v5:geraniol-10", "dpg", "mass_fraction"),)


def test_lines_naming_two_solvents_for_one_bottle_fill_in_neither(join):
    # inventory.txt lists the same 10% twice, in DPG and in TEC: which one is the bottle is
    # not guessed for the design rows; the Stock page row says both.
    record = _record("v5:geraniol-10", "Geraniol 10%", 0.1, identity="Geraniol")
    lines = [
        _line("Geraniol (10% DPG)", "Geraniol", 0.1, carrier="dpg"),
        _line("Geraniol (10% in TEC)", "Geraniol", 0.1, carrier="tec"),
    ]

    projection = join([record], lines)

    assert [s.stock_id for s in _rows(projection, "Geraniol")] == ["v5:geraniol-10"]
    assert projection.inventory_text_forms == ()
    assert dict(projection.inventory_text_notes)["v5:geraniol-10"] == (
        "Your inventory list says 10% in DPG; Your inventory list says 10% in TEC"
    )


@pytest.mark.usefixtures("neat_ambrettolide_still_owned")
def test_a_record_of_kennys_own_word_is_never_hidden_by_his_inventory_list(join):
    # His dated overlays are newer than the hand-kept list: a line in another solvent, a
    # line at another strength, or a label naming another strength never hides them.
    aurantiol = _record("o:aurantiol-10", "Aurantiol 10%", 0.1, identity="Aurantiol", carrier="dpg",
                        basis="mass_fraction", authority=HIS_WORD, ready=True)
    ambrettolide = _record("o:ambrettolide", "Ambrettolide", 1.0, identity="Ambrettolide", basis="neat",
                           authority=HIS_WORD, ready=True)
    benzoin = _record("o:benzoin", "Benzoin tincture", 0.4, identity="Benzoin tincture", carrier="ethanol",
                      basis="mass_fraction", authority=HIS_WORD, raw_name="Benzoin tincture 20%", ready=True)
    lines = [
        _line("Aurantiol (10% in ethanol)", "Aurantiol", 0.1, carrier="ethanol", basis="mass_fraction"),
        _line("Ambrettolide (10%)", "Ambrettolide", 0.1),
    ]

    projection = join([aurantiol, ambrettolide, benzoin], lines)

    # One Aurantiol bottle, his record, with what the list says beside it.
    assert [s.stock_id for s in _rows(projection, "Aurantiol")] == ["o:aurantiol-10"]
    assert dict(projection.inventory_text_notes)["o:aurantiol-10"] == "Your inventory list says 10% w/w in ethanol"
    # Neat Ambrettolide is shown; the 10% line is another bottle and keeps its own row.
    ambrettolide_rows = _rows(projection, "Ambrettolide")
    assert {s.stock_id for s in ambrettolide_rows if s.authority != LIVE_TEXT_AUTHORITY} == {"o:ambrettolide"}
    assert [s.dilution for s in ambrettolide_rows if s.authority == LIVE_TEXT_AUTHORITY] == [0.1]
    assert "o:ambrettolide" not in dict(projection.inventory_text_notes)
    assert [s.stock_id for s in _rows(projection, "Benzoin tincture")] == ["o:benzoin"]
    # His record names its own solvent: nothing from the list fills it in.
    assert projection.inventory_text_forms == ()


def test_a_bottle_the_workbook_lists_twice_shows_once_with_its_solvent(join):
    with_solvent = _record("v5:costus-a", "Costus 10% in DPG", 0.1, identity="Costus", carrier="dpg",
                           basis="mass_fraction")
    without = _record("v5:costus-b", "Costus 10%", 0.1, identity="Costus")
    line = _line("Costus (10% DPG)", "Costus", 0.1, carrier="dpg", basis="mass_fraction")

    projection = join([with_solvent, without], [line])

    assert [s.stock_id for s in _rows(projection, "Costus")] == ["v5:costus-a"]
    assert [record_id for _text_id, record_id in projection.merged_text_stock_ids] == ["v5:costus-a"]
    assert projection.inventory_text_notes == ()


@pytest.mark.parametrize("order", [1, -1])
def test_the_fuller_record_of_a_bottle_listed_twice_wins_in_either_order(join, order):
    # The line names a basis neither record has, so neither matches it exactly; the record
    # that names the solvent is the bottle, whichever the workbook lists first.
    with_solvent = _record("v5:jasmine-a", "Jasmine Sambac 10% in DPG", 0.1, identity="Jasmine Sambac",
                           carrier="dpg")
    without = _record("v5:jasmine-b", "Jasmine Sambac 10%", 0.1, identity="Jasmine Sambac")
    line = _line("Jasmine Sambac (10% w/w in DPG)", "Jasmine Sambac", 0.1, carrier="dpg", basis="mass_fraction")

    projection = join([without, with_solvent][::order], [line])

    assert [s.stock_id for s in _rows(projection, "Jasmine Sambac")] == ["v5:jasmine-a"]
    assert [record_id for _text_id, record_id in projection.merged_text_stock_ids] == ["v5:jasmine-a"]


def test_a_record_kenny_completed_on_the_stock_page_stays_shown_when_his_list_says_otherwise(join):
    # He opened the newly shown record and saved the solvent the bottle really has (TEC), not
    # the DPG his list says: the record stays, the line gets no row, and the row says both.
    completed = _record("v5:geraniol-10", "Geraniol 10%", 0.1, identity="Geraniol", carrier="tec",
                        basis="mass_fraction", completion="sha-of-his-entry")
    line = _line("Geraniol (10% DPG)", "Geraniol", 0.1, carrier="dpg")

    projection = join([completed], [line])

    assert [s.stock_id for s in _rows(projection, "Geraniol")] == ["v5:geraniol-10"]
    assert [record_id for _text_id, record_id in projection.merged_text_stock_ids] == ["v5:geraniol-10"]
    assert projection.inventory_text_notes == (("v5:geraniol-10", "Your inventory list says 10% in DPG"),)


def test_a_line_that_had_its_own_row_keeps_finding_its_bottle_once_the_record_matches_it(join):
    # Before Kenny completed it, the record had no solvent and the line was merged into it;
    # once he saves DPG the two match exactly, and a row saved against the line still maps.
    blank = _record("v5:geraniol-10", "Geraniol 10%", 0.1, identity="Geraniol")
    completed = _record("v5:geraniol-10", "Geraniol 10%", 0.1, identity="Geraniol", carrier="dpg",
                        completion="sha-of-his-entry")
    line = _line("Geraniol (10% DPG)", "Geraniol", 0.1, carrier="dpg")

    before = join([blank], [line])
    after = join([completed], [line])

    assert before.merged_text_stock_ids == after.merged_text_stock_ids
    assert [record_id for _text_id, record_id in after.merged_text_stock_ids] == ["v5:geraniol-10"]


def test_a_record_of_a_strength_his_list_does_not_have_stays_hidden(join):
    # Which strength he has is asked in "What's missing"; the Stock page shows his line.
    record = _record("v5:beta-ionone-1", "Beta Ionone 1%", 0.01, identity="Beta Ionone")
    line = _line("Beta Ionone (10%)", "Beta Ionone", 0.1)

    projection = join([record], [line])

    rows = _rows(projection, "Beta Ionone")
    assert [(s.authority, s.dilution) for s in rows] == [(LIVE_TEXT_AUTHORITY, 0.1)]
    assert projection.merged_text_stock_ids == () and projection.inventory_text_notes == ()


def test_a_line_naming_a_bottle_kenny_says_he_does_not_own_gets_no_row(join, monkeypatch):
    # 15 Oct, his dated word: no neat Neroli, only the 10% in jojoba. His list still has a
    # neat line, so the composer must not be offered neat Neroli.
    from engine import stock_matching

    monkeypatch.setattr(stock_matching, "not_owned_names", lambda directory=None: frozenset({
        normalize_name("Neroli EO (neat)"), normalize_name("Neroli EO neat"),
    }))
    jojoba = _record("o:neroli-10", "Neroli EO 10%", 0.1, identity="Neroli EO", carrier="jojoba",
                     authority=HIS_WORD, ready=True)
    lines = [
        _line("Neroli EO (neat)  # retained owned stock", "Neroli EO", 1.0),
        _line("Neroli EO (10% v/v in ethanol)", "Neroli EO", 0.1, carrier="ethanol", basis="volume_fraction"),
    ]

    projection = join([jojoba], lines)

    assert [s.stock_id for s in _rows(projection, "Neroli EO")] == ["o:neroli-10"]
    assert dict(projection.inventory_text_notes)["o:neroli-10"] == "Your inventory list says 10% v/v in ethanol"


def test_a_not_owned_name_does_not_hide_a_bottle_the_checks_hold_at_that_strength(join, monkeypatch):
    from engine import stock_matching

    monkeypatch.setattr(stock_matching, "not_owned_names", lambda directory=None: frozenset({"romandolide"}))
    record = _record("v5:romandolide", "Romandolide", 1.0, identity="Romandolide", basis="neat", ready=True)

    projection = join([record], [_line("Romandolide", "Romandolide", 1.0), _line("Romandolide (10%)", "Romandolide", 0.1)])

    # The neat line is the checks' bottle and still maps to it; the 10% line has no owned
    # record, so it is left out.
    assert [s.stock_id for s in _rows(projection, "Romandolide")] == ["v5:romandolide"]
    assert [record_id for _text_id, record_id in projection.merged_text_stock_ids] == ["v5:romandolide"]


def test_his_latest_overlay_word_on_a_name_decides_whether_he_owns_it(tmp_path: Path):
    from engine import stock_matching

    def overlay(name, records):
        (tmp_path / f"inventory_user_authority_overlay_{name}.json").write_text(
            json.dumps({"records": records}), encoding="utf-8"
        )

    overlay("20260908_romandolide", [{"canonical_name": "Romandolide", "state": "NOT_OWNED"}])
    overlay("20260910_romandolide_restocked", [{"canonical_name": "Romandolide", "state": "OWNED"}])
    overlay("20261014_neroli", [{"canonical_name": "Neroli EO (neat)", "aliases": ["Neroli EO neat"],
                                 "state": "NOT_OWNED"}])

    assert stock_matching.not_owned_names(tmp_path) == {
        normalize_name("Neroli EO (neat)"), normalize_name("Neroli EO neat"),
    }


PREPARED = "LAB_STOCK_PAGE_PREPARED_DILUTION"


def _prepared(stock_id, name, dilution, *, identity, carrier):
    # A dilution Kenny made on the Stock page: a new bottle, never on inventory.txt.
    return _record(stock_id, name, dilution, identity=identity, carrier=carrier, basis="mass_fraction",
                   authority=PREPARED, ready=True, completion="a" * 64)


def test_a_dilution_made_on_the_stock_page_never_takes_an_inventory_list_line(join):
    # Kenny made a 10% in ethanol on the Stock page; inventory.txt lists his older 10% in
    # DPG. Those are two bottles: the line keeps its own row and is not mapped to the new one.
    prepared = _prepared("p:iso-10-eth", "Iso E Super 10%", 0.1, identity="Iso E Super", carrier="ethanol")
    line = _line("Iso E Super (10% DPG)", "Iso E Super", 0.1, carrier="dpg", basis="mass_fraction")

    projection = join([prepared], [line])

    rows = _rows(projection, "Iso E Super")
    assert {s.stock_id for s in rows if s.authority != LIVE_TEXT_AUTHORITY} == {"p:iso-10-eth"}
    assert [s.raw_name for s in rows if s.authority == LIVE_TEXT_AUTHORITY] == [line.raw_name]
    assert projection.merged_text_stock_ids == ()
    assert projection.inventory_text_notes == ()


def test_a_dilution_made_on_the_stock_page_does_not_hide_the_workbook_bottle(join):
    # The workbook's 10% leaves its solvent blank; inventory.txt says it is in DPG. A 10% in
    # ethanol Kenny made on the Stock page is another bottle, so the workbook bottle stays
    # shown and the line is still its bottle.
    record = _record("v5:iso-10", "Iso E Super 10%", 0.1, identity="Iso E Super")
    prepared = _prepared("p:iso-10-eth", "Iso E Super 10%", 0.1, identity="Iso E Super", carrier="ethanol")
    line = _line("Iso E Super (10% DPG)", "Iso E Super", 0.1, carrier="dpg", basis="mass_fraction")

    projection = join([record, prepared], [line])

    assert {s.stock_id for s in _rows(projection, "Iso E Super")} == {"v5:iso-10", "p:iso-10-eth"}
    assert [record_id for _text_id, record_id in projection.merged_text_stock_ids] == ["v5:iso-10"]
    assert projection.inventory_text_forms == (("v5:iso-10", "dpg", "mass_fraction"),)
