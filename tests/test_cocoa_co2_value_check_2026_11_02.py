"""Kenny, 2 Nov 2026: "Check cocoa co2 absolute values in engines, make sure that it is not overdosed
or made from a fake source". Findings: /mnt/project-files/reformulation-window/dhi-2011/r6_1/
COCOA_CO2_CHECK_20261102.md. Every value either carries its source or says it has none.
"""

import json
from pathlib import Path

import yaml

from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA, ODT_VERIFICATION

ROOT = Path(__file__).resolve().parents[1]


def test_cocoa_co2_profile_uses_producer_and_tgsc_words():
    profile = get_profile("Cocoa CO2 Extract")
    assert profile.cas == "84649-99-0"
    assert "smoky" not in profile.character  # in no producer text
    assert profile.character["sweetness"] == 8.5 and profile.character["creamy"] == 7.0
    assert profile.odor_description == "Chocolate, cocoa, creamy, milky."
    assert profile.hedonic == 0.0  # no sourced pleasantness; the -0.4 came from the unsourced smoky value
    assert profile.synergies == ["Vanillin", "Acetoin"]


def test_cocoa_co2_placeholders_are_labelled_unsourced():
    entry = next(v for k, v in ODT_DATA.items() if k == "cocoa co2 extract") if "cocoa co2 extract" in ODT_DATA else None
    if entry is not None:
        assert "dark chocolate" not in entry["char"]
    assert ODT_VERIFICATION["cocoa co2 extract"]["vfy"] == "UNVERIFIED"
    rows = {r["name"]: r for r in json.loads((ROOT / "data/knowledge_graph/material_properties.json").read_text())}
    cocoa = rows["Cocoa CO2 Extract"]
    assert cocoa["typical_pct_range"].startswith("0.1–5% of compound (PerfumersWorld 1VT23924")
    assert cocoa["field_evidence"]["odt"]["status"] == "UNSOURCED_MIXTURE_PLACEHOLDER"


def test_cocoa_co2_material_record_flags_density_and_process():
    record = next(r for r in yaml.safe_load((ROOT / "data/materials/C.yaml").read_text()) if r["canonical_name"] == "Cocoa CO2 Extract")
    assert record["provenance"]["density_trust"].startswith("LOW")
    assert "Process unverified" in record["notes"] and "suspension" in record["notes"]
    assert record["character"].startswith("chocolate- and caramel-like")
