from pathlib import Path

from engine.calibration.hashing import stable_formula_hash
from engine.calibration.models import CalibrationRecord, PanelResult, WearTestObservation
from engine.calibration.store import append_record, load_records, summarize_records
from engine.confidence import ConfidenceScorer
from scripts.record_calibration import main as record_calibration_main


def test_stable_formula_hash_ignores_row_order_but_tracks_dose():
    first = stable_formula_hash(
        "Test Formula",
        {"Hedione": 100.0, "Iso E Super": 50.0},
        {"Hedione": 1.0, "Iso E Super": 1.0},
    )
    reordered = stable_formula_hash(
        "Test Formula",
        {"Iso E Super": 50.0, "Hedione": 100.0},
        {"Iso E Super": 1.0, "Hedione": 1.0},
    )
    changed = stable_formula_hash(
        "Test Formula",
        {"Hedione": 101.0, "Iso E Super": 50.0},
        {"Hedione": 1.0, "Iso E Super": 1.0},
    )

    assert first == reordered
    assert first != changed


def test_jsonl_calibration_roundtrip_and_summary(tmp_path):
    path = tmp_path / "wear_tests.jsonl"
    record = CalibrationRecord(
        formula_name="Test Formula",
        formula_hash="abc123",
        predicted={"intensity_0_10": 6.0, "projection_cm": 50.0},
        observations=(
            WearTestObservation(
                time_minutes=30.0,
                substrate="skin",
                time_window="heart",
                projection_cm=40.0,
                perceived_intensity_0_10=7.0,
                dominant_notes=("lavender", "musk"),
                rejection_flags=("too sweet",),
            ),
        ),
        panel_results=(
            PanelResult(
                panelist_id="p1",
                liking_0_10=8.0,
                descriptors=("clean",),
            ),
        ),
    )

    append_record(record, path)
    rows = load_records(path)
    summary = summarize_records(rows, formula_hash="abc123")

    assert rows[0].observations[0].substrate == "skin"
    assert rows[0].panel_results[0].descriptors == ("clean",)
    assert summary["formula_records"] == 1
    assert summary["wear_observations"] == 1
    assert summary["panel_results"] == 1
    assert summary["mean_intensity_bias_0_10"] == 1.0
    assert summary["mean_projection_bias_cm"] == -10.0


def test_record_calibration_cli_writes_one_record(tmp_path):
    formula_path = tmp_path / "formula.md"
    output_path = tmp_path / "wear_tests.jsonl"
    formula_path.write_text(
        "\n".join([
            "# Test Formula",
            "",
            "| # | Material | Dilution | Amount (uL) | Amount (mL) |",
            "|---:|---|---:|---:|---:|",
            "| 1 | Hedione | neat | 3000 | 3.000 |",
            "| 2 | Iso E Super | neat | 3000 | 3.000 |",
        ]),
        encoding="utf-8",
    )

    code = record_calibration_main([
        "--formula-file",
        str(formula_path),
        "--time-min",
        "30",
        "--substrate",
        "skin",
        "--projection-cm",
        "45",
        "--intensity",
        "6.5",
        "--dominant-note",
        "jasmine",
        "--comment",
        "clean heart",
        "--output",
        str(output_path),
    ])
    rows = load_records(output_path)

    assert code == 0
    assert len(rows) == 1
    assert rows[0].formula_name == "Test Formula"
    assert rows[0].observations[0].dominant_notes == ("jasmine",)


def test_confidence_counts_jsonl_calibration_records(tmp_path, monkeypatch):
    path = tmp_path / "wear_tests.jsonl"
    for idx in range(3):
        append_record(
            CalibrationRecord(
                formula_name=f"Formula {idx}",
                formula_hash=f"hash{idx}",
                observations=(WearTestObservation(time_minutes=idx),),
            ),
            path,
        )

    monkeypatch.setenv("PERFUME_CALIBRATION_PATH", str(path))
    import engine.confidence as confidence_module

    monkeypatch.setattr(confidence_module, "DB_PATH", Path(tmp_path / "missing.sqlite"))
    readiness = ConfidenceScorer().outcome_readiness()

    assert readiness["outcome_count"] == 3
    assert readiness["calibration_ready"] is True
