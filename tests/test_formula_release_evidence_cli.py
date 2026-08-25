from __future__ import annotations

import json
from types import SimpleNamespace

from scripts.formula_release_gate import main

FORMULA = """# Evidence CLI Probe

| # | Material | Dilution | Amount (uL) | Amount (mL) |
|---:|---|---:|---:|---:|
| 1 | Cedrat FCF oil Sicilian | neat | 1200 | 1.200 |
| 2 | Lavender EO (BONTAUX SAS) | neat | 700 | 0.700 |
| 3 | Linalyl Acetate | neat | 600 | 0.600 |
| 4 | Hedione | neat | 900 | 0.900 |
| 5 | Coumarin | 30% | 300 | 0.300 |
| 6 | Evernyl | 20% | 10 | 0.010 |
| 7 | Iso E Super | neat | 1500 | 1.500 |
| 8 | Cedarwood oil Virginia | neat | 300 | 0.300 |
| 9 | Zenolide | neat | 490 | 0.490 |
"""


def _argv(path, *extra: str) -> list[str]:
    return [
        "--formula-file",
        str(path),
        "--brief",
        "aromatic_fougere",
        "--commercial-trial",
        "--json",
        "--no-audit",
        "--no-append-analysis",
        *extra,
    ]


def test_default_cli_uses_v2_without_evaluating_legacy_scores(
    tmp_path, monkeypatch, capsys
) -> None:
    path = tmp_path / "probe.md"
    path.write_text(FORMULA, encoding="utf-8")

    def forbidden(*args, **kwargs):
        raise AssertionError("legacy OAV/scoring evaluated by default")

    monkeypatch.setattr("scripts.formula_release_gate.analyze_oav_authority", forbidden)
    monkeypatch.setattr(
        "scripts.formula_release_gate.compute_unified_release_scores", forbidden
    )
    main(_argv(path))
    payload = json.loads(capsys.readouterr().out)
    report = payload["formulas"][0]

    assert report["release_evidence"]["schema_version"] == "release_evidence_v2"
    assert report["release_evidence"]["release_authority"] is False
    assert "scores" not in report
    assert "industry_10" not in report
    assert "oav_authority" not in report
    assert "compatibility" not in report
    axes = {
        axis["axis_id"]: axis["state"]
        for axis in report["release_evidence"]["axes"]
    }
    assert axes["oav_evidence"] in {"MODELED_SCREEN", "PARTIAL", "HOLD"}
    assert axes["hedonic_evidence"] == "NOT_TESTED"
    assert report["release_evidence"]["status"] == "HOLD"


def test_legacy_diagnostics_are_opt_in_and_noncontrolling(
    tmp_path, monkeypatch, capsys
) -> None:
    path = tmp_path / "probe.md"
    path.write_text(FORMULA, encoding="utf-8")
    fake = SimpleNamespace(
        as_dict=lambda: {
            "scores": {"total": 100.0, "hedonic": 100.0},
            "industry_10": {"impact": 100.0},
            "provenance": {"classification": "LEGACY_TEST_DOUBLE"},
            "science_penalty": 0.0,
        }
    )
    monkeypatch.setattr(
        "scripts.formula_release_gate.compute_unified_release_scores",
        lambda *args, **kwargs: fake,
    )
    main(_argv(path, "--include-legacy-diagnostics"))
    payload = json.loads(capsys.readouterr().out)
    report = payload["formulas"][0]

    assert report["release_evidence"]["status"] == "HOLD"
    legacy = report["compatibility"]["legacy_unified_scores_v1"]
    assert legacy["scores"]["total"] == 100.0
    assert legacy["scores"]["hedonic"] == 100.0
    assert report["release_evidence"]["release_authority"] is False
    assert "scores" not in report


def test_json_contains_no_top_level_numeric_hedonic_or_rank_score(
    tmp_path, capsys
) -> None:
    path = tmp_path / "probe.md"
    path.write_text(FORMULA, encoding="utf-8")
    main(_argv(path))
    payload = json.loads(capsys.readouterr().out)
    report = payload["formulas"][0]
    assert "hedonic" not in report
    assert "rank_score" not in report
    assert report["release_evidence"]["release_authority"] is False
