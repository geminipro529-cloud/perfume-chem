"""Cited note accord specs: coverage, jobs, sources, owned stock, and no duel reads."""

from __future__ import annotations

import builtins
import json
import os
import pathlib
import subprocess
import sys
from dataclasses import replace

import pytest

from engine.formulation_intelligence import note_accord_specs as specs
from engine.inventory_completions import effective_design_ready
from engine.research import composition_planner as planner

LIBRARY_PATH = specs.ROOT / "data/formulation_knowledge/construction_library_v1.json"


def _parts(spec):
    yield spec.lead, spec.lead_stocks
    for helper in spec.helpers:
        yield helper.node, helper.stocks


def _owned():
    return planner._cached_legacy_inventory(planner._inventory_text_sha256(), False)


def _with_helper(facet_id, **changes):
    spec = specs.accord_spec_for(facet_id)
    return replace(spec, helpers=(replace(spec.helpers[0], **changes), *spec.helpers[1:]))


def test_lavender_iris_and_rose_are_covered_and_the_gaps_are_named():
    covered = specs.covered_facets()
    assert {
        "aromatic_lavender", "rose", "iris_violet", "iris_root", "iris_butter",
        "iris_cosmetic", "iris_transparent", "iris_woody", "vetiver_root", "apricot",
    } == covered
    assert set(specs.NOT_COVERED) == {"sandalwood", "pear"}
    assert specs.accord_spec_for("creamy_wood") is None
    assert specs.accord_spec_for("fruit") is None
    assert specs.accord_spec_for("citrus_peel") is None


def test_lavender_lead_prefers_the_neat_bontaux_oil_over_the_one_percent():
    lead = specs.accord_spec_for("aromatic_lavender").lead_stocks[0]
    rows = [row for row in _owned() if row.name == lead.name and row.dilution == lead.fraction]
    assert len(rows) == 1 and "BONTAUX" in rows[0].raw_name
    assert lead.fraction == 1.0 and not lead.grade_differs
    names = [(stock.name, stock.fraction) for stock in specs.accord_spec_for("aromatic_lavender").lead_stocks]
    assert ("Lavender EO", .01) not in names


def test_every_job_is_allowed_and_bridge_is_never_one():
    assert set(specs.JOBS) == {"lift", "round", "fix", "naturalise", "shadow", "contrast", "texture"}
    for spec in specs.SPECS:
        for helper in spec.helpers:
            assert helper.job in specs.JOBS and helper.job != "bridge"


@pytest.mark.parametrize("job", ["bridge", "support", ""])
def test_a_job_outside_the_set_is_rejected(job):
    with pytest.raises(ValueError, match="is not one of"):
        specs.validate_specs((_with_helper("rose", job=job),))


def test_every_lead_and_helper_has_a_producer_text_or_paper_source():
    records, reviews = specs.source_records()
    for spec in specs.SPECS:
        for node, _stocks in _parts(spec):
            assert all(source_id in records and source_id in reviews for source_id in node.source_ids)
            kinds = {specs.source_kind(records[source_id]) for source_id in node.source_ids}
            assert kinds & specs.ADMITTED_SOURCE_KINDS, (spec.note, node)


def test_source_kind_is_read_from_the_record_not_the_id():
    records, _ = specs.source_records()
    for source_id in (
        "houbigant_fougere_royale_extrait", "guerlain_mitsouko_edp_foundation",
        "guerlain_pera_granita_edt", "jomalone_english_pear_freesia_cologne",
    ):
        assert records[source_id]["evidence_class"] == "MANUFACTURER_DESCRIPTION"
        assert specs.source_kind(records[source_id]) == "other"
    assert specs.source_kind(records["iff_orivone"]) == "producer_text"
    assert specs.source_kind(records["bontoux_lavender_products"]) == "producer_text"
    assert specs.source_kind(records["pear_aroma"]) == "paper"  # PMID in its PubMed URL, no DOI
    assert specs.source_citation(records["pear_aroma"]) == "PMID 27935705"
    # The id says nothing: a producer-looking id on a perfume-house page is not a producer text.
    assert specs.source_kind({**records["houbigant_fougere_royale_extrait"], "source_id": "iff_x"}) == "other"
    assert specs.source_kind({**records["iff_orivone"], "url": "https://www.guerlain.com/p/x"}) == "other"


def test_node_function_text_and_sources_match_the_library():
    with LIBRARY_PATH.open(encoding="utf-8") as handle:
        packages = json.load(handle)["packages"]
    nodes = {
        (package["package_id"], node["role_id"]): node
        for package in packages for node in package["functional_graph"]["nodes"]
    }
    for spec in specs.SPECS:
        for node, _stocks in _parts(spec):
            raw = nodes[(node.package_id, node.role_id)]
            assert node.function == raw["function"]
            assert set(node.source_ids) <= set(raw["source_ids"])


def test_a_misquoted_function_is_rejected():
    spec = specs.accord_spec_for("rose")
    node = replace(spec.helpers[0].node, function="transparent petal lift")
    with pytest.raises(ValueError, match="function text"):
        specs.validate_specs((_with_helper("rose", node=node),))


def test_a_helper_the_package_never_pairs_with_the_lead_is_rejected():
    # FL_IRIS pairs the petal alternative with the bridge, never with the root anchor.
    node = specs.NodeRef("FL_IRIS", "alternative_texture", "petal alternative", ("givaudan_dihydro",))
    with pytest.raises(ValueError, match="pairs it with the lead"):
        specs.validate_specs((_with_helper("iris_root", node=node),))


def test_every_stock_is_owned_and_design_ready():
    owned = _owned()
    for spec in specs.SPECS:
        for _node, stocks in _parts(spec):
            for stock in stocks:
                rows = [row for row in owned if row.name == stock.name and abs(row.dilution - stock.fraction) < 1e-9]
                assert len(rows) == 1 and effective_design_ready(rows[0]), stock
                assert not stock.grade_differs or stock.note.strip()


@pytest.mark.parametrize("stock", [
    specs.StockRef("Methyl Ionone Gamma Coeur", 1.0),  # depleted
    specs.StockRef("Javanol Super", 1.0),  # not owned
    specs.StockRef("Lavender EO", .01),  # owned, not design-ready
    specs.StockRef("Hedione", .1),  # owned name, wrong strength
])
def test_a_stock_that_is_not_one_owned_design_ready_bottle_is_rejected(stock):
    with pytest.raises(ValueError, match="not one owned, design-ready stock"):
        specs.validate_specs((_with_helper("rose", stocks=(stock,)),))


def test_a_grade_difference_needs_a_note():
    stock = specs.StockRef("Hedione", 1.0, grade_differs=True)
    with pytest.raises(ValueError, match="no note"):
        specs.validate_specs((_with_helper("rose", stocks=(stock,)),))


def test_unowned_helpers_are_left_out_and_recorded():
    used = {stock.name for spec in specs.SPECS for _node, stocks in _parts(spec) for stock in stocks}
    assert not used & {"Methyl Ionone Gamma Coeur", "Javanol", "Sandalwood Base 3X", "Alpha Isomethyl Ionone"}
    materials = " ".join(row["material"] for row in specs.EXCLUDED)
    for material in ("Gamma Coeur", "Javanol Super", "Davana", "Houbigant", "Pera Granita"):
        assert material in materials
    assert all(row["reason"].strip() for row in specs.EXCLUDED)


def test_helpers_stay_clearly_below_the_lead():
    for spec in specs.SPECS:
        assert all(0 < helper.share_of_lead <= .5 for helper in spec.helpers)
        assert sum(helper.share_of_lead for helper in spec.helpers) < 1
    with pytest.raises(ValueError, match="clearly below the lead"):
        specs.validate_specs((_with_helper("rose", share_of_lead=.8),))


def test_a_node_with_only_marketed_perfume_sources_is_rejected():
    spec = specs.accord_spec_for("aromatic_lavender")
    marketed = specs.Helper(
        "texture",
        specs.NodeRef("AR_LAVENDER", "bridge", "dry aromatic continuity", ("houbigant_fougere_royale_extrait",)),
        (specs.StockRef("Hedione", 1.0),),
        specs.SECOND_HELPER_SHARE,
    )
    with pytest.raises(ValueError, match="no producer text or paper"):
        specs.validate_specs((replace(spec, helpers=(*spec.helpers, marketed)),))


def _is_duel_path(path) -> bool:
    return "opus" in os.fspath(path).casefold()  # data/benchmarks/opus_duel_v1.json and its cards


def test_loader_never_opens_the_duel_file(monkeypatch):
    opened: list[str] = []
    real_open, real_path_open = builtins.open, pathlib.Path.open

    def guarded_open(file, *args, **kwargs):
        opened.append(os.fspath(file) if not isinstance(file, int) else "")
        if not isinstance(file, int) and _is_duel_path(file):
            raise AssertionError(f"opened {file}")
        return real_open(file, *args, **kwargs)

    def guarded_path_open(self, *args, **kwargs):
        opened.append(os.fspath(self))
        if _is_duel_path(self):
            raise AssertionError(f"opened {self}")
        return real_path_open(self, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(pathlib.Path, "open", guarded_path_open)
    for cached in (specs._validated, specs.source_records, planner._cached_legacy_inventory):
        cached.cache_clear()
    assert specs.accord_spec_for("aromatic_lavender") is not None
    assert specs.covered_facets()
    assert any(path.endswith("literature_v1.json") for path in opened)  # the guard saw the loader's reads
    assert not [path for path in opened if _is_duel_path(path)]


_FRESH_PROCESS = """
import builtins, json, os, pathlib, sys
opened = []
real_open, real_path_open = builtins.open, pathlib.Path.open
def note(file):
    if not isinstance(file, int):
        opened.append(os.fspath(file))
def guarded_open(file, *a, **k):
    note(file)
    return real_open(file, *a, **k)
def guarded_path_open(self, *a, **k):
    note(self)
    return real_path_open(self, *a, **k)
builtins.open, pathlib.Path.open = guarded_open, guarded_path_open
from engine.formulation_intelligence import note_accord_specs
note_accord_specs.covered_facets()
sys.stdout.write(json.dumps(opened))
"""


def test_import_and_first_call_in_a_fresh_process_never_open_the_duel_file():
    """Covers import-time reads too, which an in-process test misses once modules are cached."""
    result = subprocess.run(
        [sys.executable, "-c", _FRESH_PROCESS], cwd=specs.ROOT, capture_output=True, text=True,
        timeout=300, check=True,
    )
    opened = json.loads(result.stdout.strip().splitlines()[-1])
    assert any(path.endswith("construction_library_v1.json") for path in opened)
    assert not [path for path in opened if _is_duel_path(path)]
