import json
import subprocess
import sys
from types import SimpleNamespace

from scripts import pipeline_audit


def test_import_does_not_load_command_specific_dependency_stacks():
    probe = (
        "import sys; import scripts.pipeline_audit; "
        "targets = ('engine.pipeline.gates', 'scripts.formula_release_gate', "
        "'scripts.verify_formula_workflow', "
        "'engine.perception.complexity_benchmark', 'engine.pipeline.audit_log'); "
        "print([name for name in targets if name in sys.modules])"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=pipeline_audit.PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "[]"


def test_matching_formula_paths_excludes_scratch_by_default(tmp_path, monkeypatch):
    formulas_dir = tmp_path / "formulas"
    formulas_dir.mkdir()
    shipped = formulas_dir / "White_Suede.md"
    scratch = formulas_dir / "_temp_check.md"
    shipped.write_text("# shipped\n", encoding="utf-8")
    scratch.write_text("# scratch\n", encoding="utf-8")

    monkeypatch.setattr(pipeline_audit, "PROJECT_ROOT", tmp_path)

    selected = pipeline_audit._matching_formula_paths("formulas/*.md")

    assert [path.name for path in selected] == ["White_Suede.md"]


def test_pipeline_audit_verify_json_runs_for_small_sample(capsys):
    rc = pipeline_audit.main(["verify", "--glob", "formulas/complete/*.md", "--sample-limit", "1", "--json", "--no-audit"])
    captured = capsys.readouterr().out
    assert rc == 0
    assert "evidence_posture" in captured
    assert "schema_validation" in captured
    assert "literature_rule_contract" in captured
    assert "knowledge_rule_quality" in captured
    assert "data_authority_coverage" in captured
    assert "disconnected_module_status" in captured


def test_verify_reuses_science_audit_contract(monkeypatch, capsys):
    calls = 0

    def build_science_contract():
        nonlocal calls
        calls += 1
        return {"data_coverage_pct": {"total": 100.0}}

    monkeypatch.setattr(
        pipeline_audit,
        "SchemaValidator",
        lambda: SimpleNamespace(
            validate_all=lambda: SimpleNamespace(summary=lambda: {})
        ),
    )
    monkeypatch.setattr(
        pipeline_audit,
        "build_literature_rule_contract",
        lambda: SimpleNamespace(as_dict=lambda: {}),
    )
    monkeypatch.setattr(
        pipeline_audit,
        "build_knowledge_rule_quality_contract",
        lambda: SimpleNamespace(as_dict=lambda: {}),
    )
    monkeypatch.setattr(
        pipeline_audit,
        "build_science_audit_contract",
        build_science_contract,
    )
    monkeypatch.setattr(
        pipeline_audit,
        "_matching_formula_paths",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(pipeline_audit, "_disconnected_module_status_report", lambda: {})
    monkeypatch.setattr(pipeline_audit, "_evidence_posture_report", lambda: {})

    rc = pipeline_audit.main(["verify", "--json", "--no-audit"])

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert calls == 1
    assert payload["science_audit"]["data_coverage_pct"] == {"total": 100.0}
    assert payload["data_authority_coverage"]["science_coverage_pct"] == {
        "total": 100.0
    }


def test_complexity_benchmark_census_json(capsys) -> None:
    rc = pipeline_audit.main(
        ["complexity-benchmark", "--operation", "census", "--json"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["state"] == "PASS"
    assert payload["unclassified"] == []
    assert payload["provider_calls"] == 0


def test_complexity_benchmark_prepare_is_provider_free(
    monkeypatch, capsys
) -> None:
    expected = {
        "state": "PASS",
        "operation": "prepare",
        "provider_calls": 0,
        "run_dir": "output/complexity_xhigh_benchmark/test-run",
        "artifacts": [],
        "blockers": [],
        "prepared_request_count": 32,
    }
    monkeypatch.setattr(
        pipeline_audit,
        "prepare_complexity_benchmark",
        lambda **_: expected,
    )
    rc = pipeline_audit.main(
        [
            "complexity-benchmark",
            "--operation",
            "prepare",
            "--run-dir",
            "output/complexity_xhigh_benchmark/test-run",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["provider_calls"] == 0
    assert payload["prepared_request_count"] == 32


def test_complexity_benchmark_rejects_run_dir_traversal(capsys) -> None:
    rc = pipeline_audit.main(
        [
            "complexity-benchmark",
            "--operation",
            "prepare",
            "--run-dir",
            "../outside",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert payload["state"] == "BENCHMARK_BLOCKED"


def test_complexity_benchmark_blocked_terminal_receipt_returns_nonzero(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        pipeline_audit,
        "write_complexity_benchmark_receipt",
        lambda **_: {
            "state": "BENCHMARK_BLOCKED_UNVERIFIED_XHIGH",
            "operation": "receipt",
            "provider_calls": 0,
            "run_dir": "output/complexity_xhigh_benchmark/blocked",
            "artifacts": [],
            "blockers": ["xhigh cannot be attested"],
        },
    )
    rc = pipeline_audit.main(
        ["complexity-benchmark", "--operation", "receipt", "--json"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["state"] == "BENCHMARK_BLOCKED_UNVERIFIED_XHIGH"


def test_artifact_verify_blocks_stale_or_tampered_bindings(
    tmp_path, monkeypatch, capsys
):
    formulas_dir = tmp_path / "formulas"
    formulas_dir.mkdir()
    formula = formulas_dir / "Bound.md"
    formula.write_text("# Bound\n", encoding="utf-8")
    monkeypatch.setattr(pipeline_audit, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        pipeline_audit,
        "validate_pipeline_analysis_artifact",
        lambda _path, **_kwargs: {
            "status": "STALE",
            "issues": ["formula_definition"],
        },
    )

    rc = pipeline_audit.main(
        ["artifact-verify", "--glob", "formulas/*.md", "--json"]
    )

    captured = capsys.readouterr().out
    assert rc == 1
    assert '"status": "FAIL"' in captured
    assert '"STALE": 1' in captured


def test_artifact_verify_accepts_explicit_quarantine_as_nonpromoting(
    tmp_path, monkeypatch, capsys
):
    formulas_dir = tmp_path / "formulas"
    formulas_dir.mkdir()
    formula = formulas_dir / "Quarantined.md"
    formula.write_text(
        "# Quarantined\n\n"
        "**Status:** QUARANTINED — do not mix or release pending repair.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(pipeline_audit, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        pipeline_audit,
        "validate_pipeline_analysis_artifact",
        lambda _path, **_kwargs: {
            "status": "QUARANTINED",
            "artifact_binding_status": "STALE",
            "issues": ["formula_definition"],
            "release_authority": False,
        },
    )

    rc = pipeline_audit.main(
        ["artifact-verify", "--glob", "formulas/*.md", "--json"]
    )

    captured = capsys.readouterr().out
    assert rc == 0
    assert '"status": "PASS"' in captured
    assert '"QUARANTINED": 1' in captured
    assert '"quarantined_release_authority": false' in captured
