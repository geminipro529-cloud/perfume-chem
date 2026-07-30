import json
from hashlib import sha256
from pathlib import Path

from engine.material_resolver import resolve_material

from app.adapters.legacy_rules import (
    LegacyRuleSource,
    inventory_legacy_rule_corpus,
)

ROOT = Path(__file__).resolve().parents[3]
CORPUS_PATHS = (
    "data/knowledge_graph/theory_rules.json",
    "data/knowledge_graph/pairing_rules.json",
    "data/knowledge_graph/pairing_rules_discovered.json",
    "data/knowledge_graph/synergy_matrix.json",
)
IDENTITY_SNAPSHOT_PATH = (
    ROOT
    / "backend"
    / "tests"
    / "fixtures"
    / "b4_identity_resolution_baseline.json"
)
IDENTITY_SNAPSHOT_RAW = IDENTITY_SNAPSHOT_PATH.read_bytes()
IDENTITY_SNAPSHOT = json.loads(IDENTITY_SNAPSHOT_RAW.decode("utf-8"))
FROZEN_IDENTITIES = IDENTITY_SNAPSHOT["identity_resolution_by_raw_label"]


def _source(path: str) -> LegacyRuleSource:
    full_path = ROOT / path
    raw = full_path.read_bytes()
    return LegacyRuleSource(
        path=path,
        payload=json.loads(raw.decode("utf-8")),
        source_sha256=sha256(raw).hexdigest(),
    )


def _identity(label: str) -> str | None:
    resolved = resolve_material(label)
    if not resolved.is_known:
        return None
    return sha256(resolved.canonical_name.encode("utf-8")).hexdigest()


def _frozen_identity(label: str) -> str | None:
    if label not in FROZEN_IDENTITIES:
        raise AssertionError(f"missing B4 frozen identity resolution for {label!r}")
    return FROZEN_IDENTITIES[label]


def test_legacy_adapter_never_promotes_hard_or_numeric_claims():
    source = LegacyRuleSource(
        path="legacy.json",
        source_sha256="a" * 64,
        payload=[
            {
                "material_a": "Hedione",
                "material_b": "Musks (Galaxolide, Habanolide)",
                "type": "synergy",
                "effect": "3-5x intensity",
                "ratio": "1:1",
                "source": "narrative.md",
                "determinism": "hard",
            }
        ],
    )

    report = inventory_legacy_rule_corpus(
        (source,),
        identity_resolver=_identity,
    )
    candidate = report.candidates[0]

    assert report.total_records == 1
    assert candidate.status == "ADVISORY"
    assert candidate.runtime_role == "EXPLANATORY"
    assert candidate.numerical_model_ref is None
    assert candidate.object.kind == "GENERIC_PROSE"
    assert candidate.raw_json_pointer == "/0"
    assert "LEGACY_HARD_PROMOTION_REJECTED" in report.diagnostic_codes
    assert "NUMERICAL_CLAIM_WITHOUT_CONTROLLED_EVIDENCE" in report.diagnostic_codes


def test_generic_label_requires_explicit_group_resolution():
    source = LegacyRuleSource(
        path="legacy.json",
        source_sha256="b" * 64,
        payload=[
            {
                "material_a": "rose",
                "material_b": "florals",
                "type": "pairing",
                "effect": "supports",
                "source": "notes.md",
            }
        ],
    )

    without_groups = inventory_legacy_rule_corpus(
        (source,),
        identity_resolver=_identity,
    )
    with_groups = inventory_legacy_rule_corpus(
        (source,),
        identity_resolver=_identity,
        group_resolver={"rose": "group-rose", "florals": "group-florals"},
    )

    assert without_groups.candidates[0].subject.kind == "GENERIC_PROSE"
    assert without_groups.candidates[0].object.kind == "GENERIC_PROSE"
    assert with_groups.candidates[0].subject.kind == "GROUP"
    assert with_groups.candidates[0].subject.group_id == "group-rose"
    assert with_groups.candidates[0].object.kind == "GROUP"
    assert with_groups.candidates[0].object.group_id == "group-florals"


def test_full_legacy_corpus_inventory_is_complete_and_deterministic():
    sources = tuple(_source(path) for path in CORPUS_PATHS)

    first = inventory_legacy_rule_corpus(
        sources,
        identity_resolver=_frozen_identity,
    )
    second = inventory_legacy_rule_corpus(
        tuple(reversed(sources)),
        identity_resolver=_frozen_identity,
    )

    assert first.total_records == 3381
    assert first.source_record_counts == {
        "data/knowledge_graph/pairing_rules.json": 2408,
        "data/knowledge_graph/pairing_rules_discovered.json": 915,
        "data/knowledge_graph/synergy_matrix.json": 53,
        "data/knowledge_graph/theory_rules.json": 5,
    }
    assert first.report_sha256 == second.report_sha256
    assert first.invalid_exact_count == second.invalid_exact_count
    assert first.blocking_count == 0
    assert first.numerical_model_count == 0
    assert all(candidate.raw_json_pointer for candidate in first.candidates)


def test_frozen_corpus_baseline_prevents_invalid_exact_rule_increase():
    baseline = json.loads(
        (
            ROOT
            / "backend"
            / "tests"
            / "fixtures"
            / "b4_rule_corpus_baseline.json"
        ).read_text(encoding="utf-8")
    )
    sources = tuple(_source(path) for path in CORPUS_PATHS)
    report = inventory_legacy_rule_corpus(
        sources,
        identity_resolver=_frozen_identity,
    )

    snapshot_expected = baseline["identity_resolution_snapshot"]
    assert sha256(IDENTITY_SNAPSHOT_RAW).hexdigest() == snapshot_expected["sha256"]
    assert len(FROZEN_IDENTITIES) == snapshot_expected["labels"]
    assert IDENTITY_SNAPSHOT["authority"] == snapshot_expected["authority"]
    assert IDENTITY_SNAPSHOT["source_corpus_sha256"] == {
        source.path: source.source_sha256 for source in sources
    }
    assert report.total_records == baseline["total_records"]
    assert report.invalid_exact_count <= baseline["invalid_exact_count_ceiling"]
    assert report.blocking_count == baseline["blocking_count"] == 0
    assert report.numerical_model_count == baseline["numerical_model_count"] == 0
    assert report.duplicate_count == baseline["duplicate_count"]
    assert report.cycle_count == baseline["cycle_count"]
    assert report.report_sha256 == baseline["report_sha256"]
    assert len(report.diagnostic_codes) == len(set(report.diagnostic_codes))

    for source in sources:
        expected = baseline["sources"][source.path]
        assert source.source_sha256 == expected["sha256"]
        assert report.source_record_counts[source.path] == expected["records"]
