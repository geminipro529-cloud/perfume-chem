"""The Stock page shows one row per bottle: the checks' own record where they have one.

``materialize_personal_inventory`` joins the gate's stock list with Kenny's hand-kept
inventory.txt. These tests give it small made-up lists of both, so they keep holding as
the real stock list changes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import engine.personal_inventory as personal_inventory
from engine.inventory_parser import CurrentInventoryMaterialization, InventoryMaterial
from engine.personal_inventory import LIVE_TEXT_AUTHORITY, materialize_personal_inventory

V5 = "CURRENT_INVENTORY_MASTER_V5_EXTERNAL_SNAPSHOT"
HIS_WORD = "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20261015"


def _record(stock_id, name, dilution, *, identity, carrier="", basis="unspecified", authority=V5, raw_name=None,
            ready=False):
    return InventoryMaterial(
        name=name, dilution=dilution, category="test", raw_name=raw_name or name, status="owned",
        fraction_basis=basis, carrier=carrier, identity_name=identity, stock_id=stock_id, authority=authority,
        execution_ready=ready,
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


def test_a_bottle_the_workbook_lists_twice_shows_once_with_its_solvent(join):
    with_solvent = _record("v5:costus-a", "Costus 10% in DPG", 0.1, identity="Costus", carrier="dpg",
                           basis="mass_fraction")
    without = _record("v5:costus-b", "Costus 10%", 0.1, identity="Costus")
    line = _line("Costus (10% DPG)", "Costus", 0.1, carrier="dpg", basis="mass_fraction")

    projection = join([with_solvent, without], [line])

    assert [s.stock_id for s in _rows(projection, "Costus")] == ["v5:costus-a"]
    assert projection.merged_text_stock_ids == () and projection.inventory_text_notes == ()


def test_a_record_of_a_strength_his_list_does_not_have_stays_hidden(join):
    # Which strength he has is asked in "What's missing"; the Stock page shows his line.
    record = _record("v5:beta-ionone-1", "Beta Ionone 1%", 0.01, identity="Beta Ionone")
    line = _line("Beta Ionone (10%)", "Beta Ionone", 0.1)

    projection = join([record], [line])

    rows = _rows(projection, "Beta Ionone")
    assert [(s.authority, s.dilution) for s in rows] == [(LIVE_TEXT_AUTHORITY, 0.1)]
    assert projection.merged_text_stock_ids == () and projection.inventory_text_notes == ()
