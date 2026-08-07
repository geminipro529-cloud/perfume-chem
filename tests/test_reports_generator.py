"""Tests for engine.reports.generator."""

from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.reports.generator import (
    ReportConfig,
    generate_full_report,
    render_authority_vector,
    render_batch_report,
    render_evidence_summary,
    render_formula_report,
    render_sensory_report,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────────


def _config(**overrides: object) -> ReportConfig:
    kwargs: dict[str, object] = dict(
        title="Test Report",
        formula_name="Test Formula",
        concentration="EDP",
        batch_volume_ml=30.0,
        date="2026-07-29",
        claim_mode="reconstruction",
        authority="Tier 3 — analytically constrained",
    )
    kwargs.update(overrides)
    return ReportConfig(**kwargs)  # type: ignore[arg-type]


def _formula_rows() -> list[dict[str, object]]:
    return [
        {
            "ingredient": "Bergamot FCF",
            "stock": "neat",
            "raw_ul": 100,
            "active_ul": 100,
            "block": "top",
            "role": "character",
        },
        {
            "ingredient": "Hedione",
            "stock": "neat",
            "raw_ul": 300,
            "active_ul": 300,
            "block": "heart",
            "role": "radiance",
        },
        {
            "ingredient": "Iso E Super",
            "stock": "neat",
            "raw_ul": 450,
            "active_ul": 450,
            "block": "base",
            "role": "structural",
        },
    ]


def _chassis_rows() -> list[dict[str, object]]:
    return [
        {
            "ingredient": "Bergamot FCF",
            "core_raw_ul": 80,
            "module_raw_ul": 20,
            "classification": "core",
        },
        {
            "ingredient": "Hedione",
            "core_raw_ul": 300,
            "module_raw_ul": 0,
            "classification": "core",
        },
        {
            "ingredient": "Iso E Super",
            "core_raw_ul": 200,
            "module_raw_ul": 250,
            "classification": "core",
        },
    ]


def _evidence_claims() -> list[dict[str, object]]:
    return [
        {
            "claim_id": "C001",
            "source": "GC-MS",
            "material": "Bergamot FCF",
            "type": "quantitative",
            "confidence": "high",
            "excerpt": "Limonene detected at 38%",
        },
        {
            "claim_id": "C002",
            "source": "label",
            "material": "Hedione",
            "type": "qualitative",
            "confidence": "medium",
            "excerpt": "Listed as top note",
            "contradiction": "GC-MS shows no Hedione",
            "conflict_group": "G1",
        },
    ]


def _sensory_observations() -> list[dict[str, object]]:
    return [
        {
            "time_seconds": 0,
            "sample_code": "S01",
            "opening": "bright citrus",
            "heart": "floral",
            "drydown": "woody",
            "diffusion": "moderate",
            "longevity": "4h",
            "overall": "balanced",
        },
        {
            "time_seconds": 1800,
            "sample_code": "S01",
            "opening": "faded",
            "heart": "jasmine",
            "drydown": "cedar",
            "diffusion": "low",
            "longevity": "2h remaining",
            "overall": "pleasant",
        },
    ]


def _batch_events() -> list[dict[str, object]]:
    return [
        {
            "timestamp": "2026-07-29T10:00:00Z",
            "event_type": "DOSE_STOCK",
            "material": "Bergamot FCF",
            "mass_g": 0.1,
            "operator": "test",
            "status": "COMMITTED",
        },
        {
            "timestamp": "2026-07-29T10:01:00Z",
            "event_type": "DOSE_STOCK",
            "material": "Hedione",
            "mass_g": 0.3,
            "operator": "test",
            "status": "COMMITTED",
        },
    ]


def _authority_scores() -> dict[str, float]:
    return {
        "identity": 0.9,
        "quantity": 0.75,
        "grade": 0.4,
        "sensory": 0.15,
    }


# ── ReportConfig ──────────────────────────────────────────────────────────────────


class TestReportConfig:
    def test_all_fields(self) -> None:
        cfg = _config()
        assert cfg.title == "Test Report"
        assert cfg.formula_name == "Test Formula"
        assert cfg.concentration == "EDP"
        assert cfg.batch_volume_ml == 30.0
        assert cfg.date == "2026-07-29"
        assert cfg.claim_mode == "reconstruction"
        assert cfg.authority == "Tier 3 — analytically constrained"

    def test_as_dict(self) -> None:
        cfg = _config()
        d = cfg.as_dict()
        assert d["title"] == "Test Report"
        assert d["batch_volume_ml"] == 30.0
        assert d["claim_mode"] == "reconstruction"

    def test_frozen(self) -> None:
        cfg = _config()
        import dataclasses

        assert dataclasses.is_dataclass(cfg)
        assert cfg.__dataclass_params__.frozen  # type: ignore[attr-defined]


# ── render_formula_report ─────────────────────────────────────────────────────────


class TestRenderFormulaReport:
    def test_produces_markdown_with_title_and_table(self) -> None:
        cfg = _config()
        rows = _formula_rows()
        result = render_formula_report(cfg, rows)

        assert result.startswith("# Test Report")
        assert "**Formula:** Test Formula" in result
        assert "**Concentration:** EDP" in result
        assert "**Batch:** 30 mL" in result
        assert "**Date:** 2026-07-29" in result
        assert "**Claim mode:** reconstruction" in result
        assert "**Authority:** Tier 3 — analytically constrained" in result

        # Table header
        assert (
            "| **#** | **Ingredient** | **Stock** | **Raw µL** | **Active µL** | **Role** |"
            in result
        )
        # Data rows
        assert "Bergamot FCF" in result
        assert "Hedione" in result
        assert "Iso E Super" in result
        assert "| 1 |" in result
        assert "| 2 |" in result
        assert "| 3 |" in result

    def test_includes_chassis_partition_when_provided(self) -> None:
        cfg = _config()
        rows = _formula_rows()
        chassis = _chassis_rows()
        result = render_formula_report(cfg, rows, chassis_partition=chassis)

        assert "**Chassis Partition**" in result
        assert "| **Ingredient** | **Core µL** | **Module µL** | **Classification** |" in result
        assert "| Bergamot FCF | 80 | 20 | core |" in result
        assert "| Hedione | 300 | 0 | core |" in result

    def test_omits_chassis_when_none(self) -> None:
        cfg = _config()
        rows = _formula_rows()
        result = render_formula_report(cfg, rows, chassis_partition=None)
        assert "**Chassis Partition**" not in result

    def test_includes_modules_when_provided(self) -> None:
        cfg = _config()
        rows = _formula_rows()
        modules = {
            "Soft Amber": [
                {"ingredient": "Ambermax", "raw_ul": 50, "active_ul": 50, "role": "warmth"},
            ]
        }
        result = render_formula_report(cfg, rows, modules=modules)
        assert "**Flanker Interface**" in result
        assert "**Module:** Soft Amber" in result
        assert "Ambermax" in result

    def test_omits_modules_when_none(self) -> None:
        cfg = _config()
        rows = _formula_rows()
        result = render_formula_report(cfg, rows, modules=None)
        assert "**Flanker Interface**" not in result


# ── render_evidence_summary ───────────────────────────────────────────────────────


class TestRenderEvidenceSummary:
    def test_produces_table_with_claims(self) -> None:
        claims = _evidence_claims()
        result = render_evidence_summary(claims)

        assert "**Evidence Claims**" in result
        assert (
            "| **Claim ID** | **Source** | **Material** | **Type** | **Confidence** | **Excerpt** |"
            in result
        )
        assert (
            "| C001 | GC-MS | Bergamot FCF | quantitative | high | Limonene detected at 38% |"
            in result
        )
        assert "| C002 | label | Hedione | qualitative | medium | Listed as top note |" in result

    def test_includes_contradictions_section(self) -> None:
        claims = _evidence_claims()
        result = render_evidence_summary(claims)

        assert "**Contradictions**" in result
        assert "C002" in result
        assert "group: G1" in result
        assert "GC-MS shows no Hedione" in result

    def test_empty_claims(self) -> None:
        result = render_evidence_summary([])
        assert "**Evidence Claims**" in result
        assert "*No evidence claims recorded.*" in result


# ── render_sensory_report ─────────────────────────────────────────────────────────


class TestRenderSensoryReport:
    def test_produces_time_resolved_table(self) -> None:
        observations = _sensory_observations()
        result = render_sensory_report(observations)

        assert "**Sensory Evaluation**" in result
        assert (
            "| **Time** | **Sample Code** | **Opening** | **Heart** | **Drydown** | **Diffusion** | **Longevity** | **Overall** |"
            in result
        )
        assert "| 0s | S01 | bright citrus | floral | woody | moderate | 4h | balanced |" in result
        assert "| 1800s | S01 | faded | jasmine | cedar | low | 2h remaining | pleasant |" in result

    def test_empty_observations(self) -> None:
        result = render_sensory_report([])
        assert "**Sensory Evaluation**" in result
        assert "*No sensory observations recorded.*" in result


# ── render_batch_report ───────────────────────────────────────────────────────────


class TestRenderBatchReport:
    def test_produces_event_log_and_current_state(self) -> None:
        events = _batch_events()
        result = render_batch_report(events)

        assert "**Batch Event Log**" in result
        assert (
            "| **Timestamp** | **Event Type** | **Material** | **Mass (g)** | **Operator** | **Status** |"
            in result
        )
        assert (
            "| 2026-07-29T10:00:00Z | DOSE_STOCK | Bergamot FCF | 0.10 | test | COMMITTED |"
            in result
        )
        assert "| 2026-07-29T10:01:00Z | DOSE_STOCK | Hedione | 0.30 | test | COMMITTED |" in result

        # Current state summary
        assert "**Current State — Material Masses**" in result
        assert "| **Material** | **Current Mass (g)** |" in result
        assert "| Bergamot FCF | 0.10 |" in result
        assert "| Hedione | 0.30 |" in result

    def test_empty_events(self) -> None:
        result = render_batch_report([])
        assert "**Batch Event Log**" in result
        assert "*No batch events recorded.*" in result


# ── render_authority_vector ───────────────────────────────────────────────────────


class TestRenderAuthorityVector:
    def test_produces_per_dimension_table_with_assessments(self) -> None:
        scores = _authority_scores()
        result = render_authority_vector(scores)

        assert "**Authority Vector**" in result
        assert "| **Dimension** | **Score (0.0–1.0)** | **Assessment** |" in result

        # identity: 0.9 → High
        assert "| grade | 0.40 | Low |" in result
        assert "| identity | 0.90 | High |" in result
        assert "| quantity | 0.75 | Moderate |" in result
        assert "| sensory | 0.15 | Insufficient |" in result

    def test_includes_never_averaged_warning(self) -> None:
        scores = _authority_scores()
        result = render_authority_vector(scores)
        assert "NEVER averaged" in result
        assert "These dimensions are NEVER averaged into a single confidence score." in result

    def test_empty_scores(self) -> None:
        result = render_authority_vector({})
        assert "**Authority Vector**" in result
        assert "*No authority scores recorded.*" in result


# ── generate_full_report ──────────────────────────────────────────────────────────


class TestGenerateFullReport:
    def test_writes_to_output_path_and_returns_text(self, tmp_path: Path) -> None:
        output = tmp_path / "report.md"
        cfg = _config()
        text = generate_full_report(
            str(output),
            cfg,
            target=_formula_rows(),
            evidence=_evidence_claims(),
            sensory=_sensory_observations(),
            batch=_batch_events(),
            authority_vector=_authority_scores(),
        )

        # Returns the rendered text
        assert isinstance(text, str)
        assert text.startswith("# Test Report")

        # Writes to disk
        assert output.exists()
        written = output.read_text(encoding="utf-8")
        assert written == text

    def test_contains_expected_section_headers(self, tmp_path: Path) -> None:
        output = tmp_path / "report.md"
        cfg = _config()
        text = generate_full_report(
            str(output),
            cfg,
            target=_formula_rows(),
            chassis=_chassis_rows(),
            evidence=_evidence_claims(),
            sensory=_sensory_observations(),
            batch=_batch_events(),
            authority_vector=_authority_scores(),
        )

        assert "# Test Report" in text
        assert "**Formula:** Test Formula" in text
        assert "**Formula**" in text or "**Formula**" in text
        assert "**Chassis Partition**" in text
        assert "**Evidence Claims**" in text
        assert "**Sensory Evaluation**" in text
        assert "**Batch Event Log**" in text
        assert "**Authority Vector**" in text
        assert "NEVER averaged" in text

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        nested = tmp_path / "sub" / "deep" / "report.md"
        cfg = _config()
        text = generate_full_report(
            str(nested),
            cfg,
            target=_formula_rows(),
        )
        assert nested.exists()
        assert text.startswith("# Test Report")

    def test_empty_ledgers(self, tmp_path: Path) -> None:
        output = tmp_path / "empty.md"
        cfg = _config()
        text = generate_full_report(str(output), cfg)
        assert text.startswith("# Test Report")
        assert "**Formula**" not in text
        assert "**Evidence Claims**" not in text
        assert "**Sensory Evaluation**" not in text
        assert "**Batch Event Log**" not in text
        assert "**Authority Vector**" not in text
