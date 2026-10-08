"""Runtime literature is bounded design guidance, not invented sensory data."""

import hashlib
import json
import socket
from dataclasses import replace
from pathlib import Path

import pytest

from engine.formulation_intelligence.formula_design_runtime import design_formula
from engine.formulation_intelligence.literature_knowledge import (
    audit_prior_research,
    load_knowledge_pack,
    material_knowledge,
    retrieve_formulation_knowledge,
    validate_knowledge_pack,
)
from engine.formulation_intelligence.semantic_brief_adapter import compile_semantic_brief
from engine.research.goal_analysis import (
    GoalAnalysisRequestV1,
    GoalFormulaRowV1,
    analyze_formula_for_goal,
)


def _brief(text: str, avoid: tuple[str, ...] = ()):
    return compile_semantic_brief(
        formula_name="Research trial",
        request=text,
        interpretation={"must_avoid": avoid, "must_preserve": (), "explicit_materials": ()},
        max_materials=18,
    )


@pytest.mark.parametrize(
    ("text", "profile"),
    [
        ("Rooty mineral iris without sweetness", "iris_root"),
        ("Buttery waxy orris", "iris_butter"),
        ("Lipstick cosmetic iris", "iris_cosmetic"),
        ("Transparent iris with neroli", "iris_transparent"),
        ("Woody tobacco iris with suede", "iris_woody"),
        ("Fresh violet petals", "violet_petals"),
        ("Powdery candied violet", "violet_powder"),
        ("Green violet leaf, not violet flowers", "violet_leaf"),
    ],
)
def test_iris_violet_profile_distinctions(text: str, profile: str) -> None:
    context = retrieve_formulation_knowledge(text)
    assert profile in context["profile_ids"]
    assert context["network_used"] is False
    assert context["authority"]["compounding_authority"] is False


def test_rooty_iris_does_not_require_vetiver() -> None:
    brief = _brief("Rooty mineral iris, not sweeter")
    assert "vetiver_root" not in brief.facets
    assert "iris_root" in brief.facets


def test_violet_leaf_is_not_a_powdery_flower_requirement() -> None:
    brief = _brief("Green violet leaf with cedar, no powder", ("powder",))
    assert "violet_leaf" in brief.facets
    assert "iris_violet" not in brief.facets
    assert "violet_petals" not in brief.facets


def test_exact_material_grades_are_not_collapsed() -> None:
    aimi = material_knowledge("Alpha Isomethyl Ionone")
    gamma = material_knowledge("Methyl Ionone Gamma Coeur")
    assert aimi and gamma
    assert aimi["material_id"] != gamma["material_id"]
    assert material_knowledge("Methyl Ionone") is None
    assert material_knowledge("Mystery orris product") is None


def test_pack_preserves_source_classes_and_has_no_dose_or_hedonic_labels() -> None:
    pack = load_knowledge_pack()
    assert len(pack["sources"]) >= 15
    assert len(pack["claims"]) >= 20
    assert pack["authority"]["evidence_admission_authorized"] is False
    assert all(claim["source_ids"] for claim in pack["claims"])
    assert all("beauty_score" not in claim for claim in pack["claims"])
    assert all("dose" not in claim for claim in pack["claims"])
    assert all(
        source["rights_scope"] == "METADATA_AND_ORIGINAL_SUMMARY_ONLY" for source in pack["sources"]
    )


def test_prior_research_snapshot_is_byte_verified_and_non_authoritative() -> None:
    result = audit_prior_research()
    assert result["indexed_record_count"] >= 128
    assert result["drifted_paths"] == []
    assert result["runtime_claim_authority"] is False
    assert result["reviewed_full_text"] is False


def test_byte_successor_preserves_original_corpus_and_exact_newline_proofs() -> None:
    from engine.formulation_intelligence import literature_knowledge as knowledge

    parent_bytes = knowledge.CORPUS_PARENT_PATH.read_bytes()
    assert hashlib.sha256(parent_bytes).hexdigest() == (
        "d614d475e88b049a21747737842fe35e8ff40292c83c403b73ba69e1c554841a"
    )
    parent = knowledge._parse_corpus(parent_bytes)
    successor = knowledge._parse_corpus(knowledge.CORPUS_PATH.read_bytes(), parent_bytes)
    rebound = [row for row in successor["records"] if "byte_rebinding" in row]
    assert len(rebound) == 8
    assert [row["path"] for row in successor["records"]] == [
        row["path"] for row in parent["records"]
    ]
    assert set(audit_prior_research(manifest=parent)["drifted_paths"]) == {
        row["path"] for row in rebound
    }
    assert audit_prior_research(manifest=successor)["drifted_paths"] == []


def test_cached_corpus_cannot_hide_parent_byte_drift() -> None:
    from engine.formulation_intelligence import literature_knowledge as knowledge

    child_bytes = knowledge.CORPUS_PATH.read_bytes()
    parent_bytes = knowledge.CORPUS_PARENT_PATH.read_bytes()
    knowledge._parse_corpus(child_bytes, parent_bytes)
    with pytest.raises(ValueError, match="predecessor hash drift"):
        knowledge._parse_corpus(child_bytes, parent_bytes + b"\n")


@pytest.mark.parametrize("mutation", ["title", "order", "authority"])
def test_byte_successor_cannot_rewrite_reference_scope(mutation: str) -> None:
    from engine.formulation_intelligence import literature_knowledge as knowledge

    child = json.loads(knowledge.CORPUS_PATH.read_bytes())
    if mutation == "title":
        child["records"][0]["title"] = "new scientific result"
    elif mutation == "order":
        child["records"].reverse()
    else:
        child["authority_scope"] = "EMPIRICAL_ADMISSION"
    with pytest.raises(ValueError, match="changed"):
        knowledge._parse_corpus(json.dumps(child).encode(), knowledge.CORPUS_PARENT_PATH.read_bytes())


def test_semantic_change_cannot_borrow_newline_rebinding(tmp_path: Path) -> None:
    original = b"original\r\n"
    changed = b"different\n"
    (tmp_path / "source.md").write_bytes(changed)
    manifest = {
        "records": [{
            "path": "source.md",
            "sha256": hashlib.sha256(changed).hexdigest(),
            "byte_count": len(changed),
            "byte_rebinding": {
                "kind": "VERIFIED_LF_CRLF_ONLY",
                "previous_sha256": hashlib.sha256(original).hexdigest(),
                "previous_byte_count": len(original),
            },
        }],
    }
    assert audit_prior_research(manifest=manifest, root=tmp_path)["state"] == "WITHHOLD_SOURCE_DRIFT"


def test_prior_document_drift_is_reported_not_silently_reindexed(tmp_path: Path) -> None:
    document = tmp_path / "old.md"
    document.write_text("changed", encoding="utf-8")
    manifest = {"records": [{"path": "old.md", "sha256": "a" * 64, "byte_count": 1}]}
    result = audit_prior_research(manifest=manifest, root=tmp_path)
    assert result["drifted_paths"] == ["old.md"]


def test_quarantined_receptor_and_family_rules_cannot_be_selected() -> None:
    context = retrieve_formulation_knowledge(
        "iris receptor saturation chemical family compatibility"
    )
    assert "ionone_receptor_ceiling" in context["quarantined_claim_ids"]
    assert all(claim["claim_id"] != "ionone_receptor_ceiling" for claim in context["claims"])
    assert any("OR5A1" in claim["statement"] for claim in context["claims"])


def test_missing_numeric_calibrations_remain_missing() -> None:
    context = retrieve_formulation_knowledge("iris intensity and pleasantness")
    assert context["numeric_calibrations_admitted"] == []
    assert context["pleasantness"] is None
    assert context["personal_liking"] is None


def test_invalid_pack_authority_and_dangling_sources_are_rejected() -> None:
    pack = load_knowledge_pack()
    pack["authority"]["release_authority"] = True
    with pytest.raises(ValueError, match="authority"):
        validate_knowledge_pack(pack)
    pack = load_knowledge_pack()
    pack["claims"][0]["source_ids"] = ["absent"]
    with pytest.raises(ValueError, match="source"):
        validate_knowledge_pack(pack)


def test_pack_returns_are_isolated_and_retrieval_is_deterministic() -> None:
    first = retrieve_formulation_knowledge("pear apple flesh and osmanthus")
    assert first == retrieve_formulation_knowledge("pear apple flesh and osmanthus")
    first["claims"].clear()
    assert retrieve_formulation_knowledge("pear apple flesh and osmanthus")["claims"]


def test_explicit_avoid_beats_literature_profile() -> None:
    brief = _brief("Iris and violet petals without violet leaf", ("violet leaf",))
    assert "violet_leaf" not in brief.facets
    assert "violet_petals" in brief.facets


def test_request_and_knowledge_versions_are_separately_bound() -> None:
    brief = _brief("Rooty mineral iris")
    assert brief.knowledge_context["pack_sha256"]
    assert brief.knowledge_context["prior_corpus_sha256"]
    assert replace(brief, normalized_request="another").knowledge_context == brief.knowledge_context


def test_rooty_transparent_iris_has_one_recognizer_and_a_root_texture() -> None:
    brief = _brief("Rooty transparent iris over quiet woods")
    assert sum(role.knowledge_role_slot == "iris recognizer" for role in brief.roles) == 1
    assert sum(role.knowledge_role_slot == "root texture" for role in brief.roles) == 1


def test_explicit_vetiver_survives_iris_context() -> None:
    brief = _brief("Rooty iris with vetiver")
    assert "vetiver_root" in brief.facets


def test_mineral_iris_does_not_force_forbidden_earthy_texture() -> None:
    brief = _brief("Transparent mineral iris without earthy roots", ("earthy roots",))
    assert "iris_root_texture" not in brief.facets


def test_real_solver_uses_distinct_iris_roles_not_duplicate_stock_rows() -> None:
    report = design_formula(idea="Rooty mineral iris with pale cedar, no vanilla", max_materials=18)
    assert report["optimized_formula"]
    rows = report["optimized_formula"]["rows"]
    assert any(row["identity_name"] == "Orivone" for row in rows)
    assert any(row["identity_name"] in {"Alpha Irone", "Alpha Isomethyl Ionone"} for row in rows)
    assert len({row["stock_id"] for row in rows}) == len(rows)
    assert report["formulation_knowledge"]["profile_ids"] == ["iris_root"]
    assert report["critic"]["strongest_clue"] == report["formulation_knowledge"]["strongest_clue"]
    assert report["beauty_score"] is None


def test_fast_curated_and_ambiguous_paths_also_return_knowledge() -> None:
    curated = design_formula(idea="A dry lavender fougere with fresh bergamot")
    assert curated["formulation_knowledge"]["pack_sha256"]
    ambiguous = design_formula(idea="Exactly 40 materials", max_materials=10)
    assert ambiguous["formulation_knowledge"]["pack_sha256"]
    assert ambiguous["optimized_formula"] is None
    assert ambiguous["formula_action"] == "NO_CHANGE"


def test_goal_analysis_adds_clues_without_overriding_observation() -> None:
    report = analyze_formula_for_goal(
        GoalAnalysisRequestV1(
            formula_id="iris-study",
            formula_name="Rooty Iris",
            rows=(GoalFormulaRowV1("irone", "Alpha Irone", "100", "uL"),),
            goals=("Make the iris clearer",),
            observations=("The control smells too woody",),
        )
    )
    assert report["formulation_knowledge"]["pack_sha256"]
    assert any(clue["clue_id"].startswith("literature-") for clue in report["clues"])
    assert report["default_user_view"]["strongest_clue"] == "The control smells too woody"
    assert report["compounding_authority"] is False
    assert report["formula_modified"] is False


def test_unknown_material_does_not_inherit_a_molecular_calibration() -> None:
    report = retrieve_formulation_knowledge(
        "iris and lavender", material_names=("Commercial Iris Base", "Lavender Essential Oil")
    )
    assert report["material_bindings"] == []
    assert report["numeric_calibrations_admitted"] == []


def test_retrieval_is_offline_and_preserves_formula_inventory_bytes(monkeypatch) -> None:
    def forbidden_network(*args, **kwargs):
        raise AssertionError("knowledge retrieval must be offline")

    monkeypatch.setattr(socket, "socket", forbidden_network)
    paths = [
        Path("inventory.txt"),
        Path("formulas/Prada_LHomme_Intense_Research_Build_v1_30mL_EDP.json"),
    ]
    before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    report = retrieve_formulation_knowledge("transparent iris with neroli")
    assert report["network_used"] is False
    assert before == [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]


def test_bad_pack_is_withheld_not_an_empty_success(monkeypatch, tmp_path) -> None:
    from engine.formulation_intelligence import literature_knowledge as knowledge

    missing = tmp_path / "missing.json"
    monkeypatch.setattr(knowledge, "PACK_PATH", missing)
    report = knowledge.retrieve_formulation_knowledge("iris")
    assert report["state"] == "WITHHOLD_UNKNOWN"
    assert report["claims"] == []
    assert knowledge.material_knowledge("Alpha Irone") is None


def test_local_source_drift_withholds_dependent_claims(monkeypatch, tmp_path) -> None:
    import json

    from engine.formulation_intelligence import literature_knowledge as knowledge

    pack = knowledge.load_knowledge_pack()
    target = next(source for source in pack["sources"] if source["source_id"] == "iff_orivone")
    target.update(local_path="drift.md", local_sha256="0" * 64)
    (tmp_path / "drift.md").write_text("changed", encoding="utf-8")
    source = tmp_path / "pack.json"
    source.write_text(json.dumps(pack), encoding="utf-8")
    corpus = tmp_path / "corpus.json"
    corpus.write_text(
        json.dumps(
            {
                "schema_version": "formulation-prior-research-corpus-v1",
                "runtime_claim_authority": False,
                "reviewed_full_text": False,
                "records": [
                    {
                        "path": "drift.md",
                        "title": "Iris",
                        "sha256": "0" * 64,
                        "byte_count": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(knowledge, "ROOT", tmp_path)
    monkeypatch.setattr(knowledge, "PACK_PATH", source)
    monkeypatch.setattr(knowledge, "CORPUS_PATH", corpus)
    report = knowledge.retrieve_formulation_knowledge("rooty iris")
    assert "iff_orivone" in report["unavailable_source_ids"]
    assert "orivone_root_texture" not in {claim["claim_id"] for claim in report["claims"]}
    assert "iris_root" not in report["profile_ids"]


def test_reference_path_cannot_escape_repository(tmp_path) -> None:
    report = audit_prior_research(
        manifest={
            "records": [
                {
                    "path": "../outside.md",
                    "sha256": "0" * 64,
                    "byte_count": 0,
                }
            ]
        },
        root=tmp_path,
    )
    assert report["state"] == "WITHHOLD_SOURCE_DRIFT"
