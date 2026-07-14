from scripts import pipeline_audit


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
