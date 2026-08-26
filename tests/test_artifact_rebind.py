from scripts.rebind_formula_artifact import semantic_manifest_diff


def test_rebind_semantic_diff_ignores_volatile_values_but_shows_inputs():
    prior = {
        "artifact_sha256": "a" * 64,
        "generated_at_utc": "2026-07-30T01:00:00+00:00",
        "repository_commit": "b" * 40,
        "analysis_input_sha256": "c" * 64,
    }
    proposed = {
        "artifact_sha256": "d" * 64,
        "generated_at_utc": "2026-07-30T02:00:00+00:00",
        "repository_commit": "e" * 40,
        "analysis_input_sha256": "f" * 64,
    }

    diff = semantic_manifest_diff(prior, proposed)

    assert "analysis_input_sha256" in diff
    assert "generated_at_utc" not in diff
    assert "repository_commit" not in diff
    assert "artifact_sha256" not in diff
