from datetime import datetime, timezone
from itertools import permutations
from types import SimpleNamespace

import pytest

from app.models.lab_backfill import (
    BACKFILL_DASHBOARD_DIMENSIONS,
    BACKFILL_REQUIREMENT_TYPES,
)
from app.services.lab_backfill import (
    BACKFILL_PRIORITY_DIMENSIONS,
    BACKFILL_PRIORITY_POLICY,
    BackfillConflictError,
    BackfillGapProjection,
    BackfillSignalCommand,
    BackfillSignalVector,
    LabBackfillServiceMixin,
    ResolvedBackfillMaterial,
    backfill_policy_hash,
    build_backfill_dashboard,
    rank_backfill_materials,
)


def _gap(
    state: str = "MISSING",
    requirement_type: str = "EXACT_IDENTITY",
    evidence_class: str = "UNKNOWN",
) -> BackfillGapProjection:
    return BackfillGapProjection(
        requirement_type=requirement_type,
        state=state,
        evidence_class=evidence_class,
    )


def _material(
    material_id: str,
    *,
    current_inventory: bool | None = False,
    active_or_shipped_formula: bool | None = False,
    high_dose_structure: float | None = 0.0,
    potent_trace: float | None = 0.0,
    regulatory_or_family_driver: int | None = 0,
    analytical_standard: bool | None = False,
    natural_constituent: bool | None = False,
    model_sensitivity: float | None = 0.0,
    gaps: tuple[BackfillGapProjection, ...] = (_gap(),),
    canonical_name: str | None = None,
) -> ResolvedBackfillMaterial:
    return ResolvedBackfillMaterial(
        material_id=material_id,
        canonical_name=canonical_name or material_id,
        chemical_family=None,
        evidence_class="UNKNOWN",
        signal_vector=BackfillSignalVector(
            current_inventory=current_inventory,
            active_or_shipped_formula=active_or_shipped_formula,
            high_dose_structure=high_dose_structure,
            potent_trace=potent_trace,
            regulatory_or_family_driver=regulatory_or_family_driver,
            analytical_standard=analytical_standard,
            natural_constituent=natural_constituent,
            model_sensitivity=model_sensitivity,
        ),
        gaps=gaps,
    )


def test_b8_priority_policy_has_exact_order_and_stable_hash():
    assert BACKFILL_PRIORITY_DIMENSIONS == (
        "CURRENT_INVENTORY",
        "ACTIVE_OR_SHIPPED_FORMULA",
        "HIGH_DOSE_STRUCTURE",
        "POTENT_TRACE",
        "REGULATORY_OR_FAMILY_DRIVER",
        "ANALYTICAL_STANDARD",
        "NATURAL_CONSTITUENT",
        "MODEL_SENSITIVITY",
    )
    assert tuple(BACKFILL_PRIORITY_POLICY["dimensions"]) == (
        BACKFILL_PRIORITY_DIMENSIONS
    )
    assert BACKFILL_PRIORITY_POLICY["requirement_types"] == list(
        BACKFILL_REQUIREMENT_TYPES
    )
    assert len(backfill_policy_hash()) == 64
    assert backfill_policy_hash() == backfill_policy_hash()


def test_b8_ranking_is_strictly_lexicographic():
    fixtures = (
        _material("unknown", current_inventory=None),
        _material("sensitive", model_sensitivity=1.0),
        _material("natural", natural_constituent=True),
        _material("standard", analytical_standard=True),
        _material("regulatory", regulatory_or_family_driver=1),
        _material("potent-trace", potent_trace=1.0),
        _material("high-dose", high_dose_structure=1.0),
        _material("active", active_or_shipped_formula=True),
        _material("owned", current_inventory=True),
    )

    ordered = rank_backfill_materials(fixtures)

    assert [row.material_id for row in ordered] == [
        "owned",
        "active",
        "high-dose",
        "potent-trace",
        "regulatory",
        "standard",
        "natural",
        "sensitive",
        "unknown",
    ]
    assert [row.rank for row in ordered] == list(range(1, 10))


def test_b8_ranking_is_input_order_independent():
    fixtures = (
        _material("owned", current_inventory=True),
        _material("active", active_or_shipped_formula=True),
        _material("sensitive", model_sensitivity=1.0),
    )
    expected = ["owned", "active", "sensitive"]
    for ordering in permutations(fixtures):
        assert [
            row.material_id for row in rank_backfill_materials(ordering)
        ] == expected


def test_b8_ranking_uses_gap_counts_then_name_and_id_for_ties():
    critical = _material(
        "critical",
        gaps=(
            _gap("MISSING", "EXACT_IDENTITY"),
            _gap("MISSING", "DENSITY"),
        ),
    )
    fewer = _material("fewer", gaps=(_gap("MISSING", "DENSITY"),))
    alpha_b = _material(
        "id-b",
        gaps=(_gap("NOT_APPLICABLE", "NATURAL_LOT_COMPOSITION"),),
        canonical_name="alpha",
    )
    alpha_a = _material(
        "id-a",
        gaps=(_gap("NOT_APPLICABLE", "NATURAL_LOT_COMPOSITION"),),
        canonical_name="alpha",
    )

    ordered = rank_backfill_materials((alpha_b, fewer, alpha_a, critical))

    assert [row.material_id for row in ordered] == [
        "critical",
        "fewer",
        "id-a",
        "id-b",
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("high_dose_structure", float("nan")),
        ("potent_trace", float("inf")),
        ("model_sensitivity", -0.1),
        ("model_sensitivity", 1.1),
    ),
)
def test_b8_ranking_rejects_nonfinite_or_out_of_range_signals(field, value):
    overrides = {field: value}
    with pytest.raises(ValueError):
        rank_backfill_materials((_material("bad", **overrides),))


def test_b8_dashboard_emits_seven_strata_without_overall_score():
    material = _material(
        "owned",
        current_inventory=True,
        active_or_shipped_formula=None,
        regulatory_or_family_driver=1,
        model_sensitivity=None,
        gaps=(
            _gap("ACCEPTED_EXACT", "EXACT_IDENTITY", "MEASURED"),
            _gap("MISSING", "DENSITY", "UNKNOWN"),
        ),
    )

    cells = build_backfill_dashboard(rank_backfill_materials((material,)))

    assert {cell.dimension for cell in cells} == set(
        BACKFILL_DASHBOARD_DIMENSIONS
    )
    assert all(
        cell.requirements_total
        == cell.accepted_exact_count
        + cell.accepted_scoped_count
        + cell.weak_count
        + cell.conflicted_count
        + cell.unknown_count
        + cell.missing_count
        + cell.not_applicable_count
        for cell in cells
    )
    banned = {
        "OVERALL",
        "TOTAL_CONFIDENCE",
        "COVERAGE_SCORE",
        "CONFIDENCE_PERCENT",
    }
    assert not any(
        cell.dimension in banned or cell.dimension_key in banned
        for cell in cells
    )


def test_b8_dashboard_keeps_evidence_classes_separate():
    material = _material(
        "mixed",
        gaps=(
            _gap("ACCEPTED_EXACT", "EXACT_IDENTITY", "MEASURED"),
            _gap("WEAK", "DENSITY", "HEURISTIC"),
            _gap("UNKNOWN", "VAPOR_PRESSURE", "UNKNOWN"),
        ),
    )

    cells = build_backfill_dashboard(rank_backfill_materials((material,)))
    evidence_keys = {
        cell.dimension_key
        for cell in cells
        if cell.dimension == "EVIDENCE_CLASS"
    }

    assert evidence_keys == {"MEASURED", "HEURISTIC", "UNKNOWN"}


class _SignalRepository:
    def __init__(self):
        self.records = {}
        self.component_lists = {}
        self.sequence_entries = {}

    async def get_oav_assessment(self, record_id):
        return self.records.get(("oav", record_id))

    async def get_property_observation(self, record_id):
        return self.records.get(("observation", record_id))

    async def get_knowledge_rule(self, record_id):
        return self.records.get(("rule", record_id))

    async def get_regulatory_snapshot_version(self, record_id):
        return self.records.get(("snapshot", record_id))

    async def get_formula_version(self, record_id):
        return self.records.get(("formula", record_id))

    async def formula_components(self, record_id):
        return self.component_lists.get(record_id, [])

    async def get_stock(self, record_id):
        return self.records.get(("stock", record_id))

    async def get_analytical_sequence_entry(self, record_id):
        return self.records.get(("analytical_entry", record_id))

    async def get_analytical_sequence(self, record_id):
        return self.records.get(("sequence", record_id))

    async def analytical_sequence_entries(self, record_id):
        return self.sequence_entries.get(record_id, [])

    async def get_analytical_method_authority(self, record_id):
        return self.records.get(("method", record_id))

    async def get_regulatory_composition_entry(self, record_id):
        return self.records.get(("composition_entry", record_id))

    async def get_regulatory_composition_profile(self, record_id):
        return self.records.get(("composition_profile", record_id))


class _SignalHarness(LabBackfillServiceMixin):
    def __init__(self, repository):
        self.repository = repository


def _signal_repository() -> _SignalRepository:
    repository = _SignalRepository()
    repository.records[("observation", "concentration")] = SimpleNamespace(
        id="concentration",
        subject_identity_json={"material_id": "material"},
        evidence_class="MEASURED",
    )
    repository.records[("oav", "oav")] = SimpleNamespace(
        id="oav",
        concentration_observation_id="concentration",
        strict_science_mode=True,
        status="COMPUTED",
        oav_value=250.0,
        mismatch_count=0,
        requested_endpoint="ODOR_DETECTION_THRESHOLD",
        requested_route="ORTHONASAL",
        input_snapshot_json={"matrix": "air"},
        content_sha256="a" * 64,
    )
    repository.records[("rule", "rule")] = SimpleNamespace(
        id="rule",
        status="AUTHORITATIVE",
        review_state="APPROVED",
        runtime_role="BLOCKING",
        evidence_class="LITERATURE_DERIVED",
        matrix_context_json={"material_id": "material"},
        subject_identity_scope_sha256=None,
        object_identity_scope_sha256=None,
        relation="SAFETY_CONTRIBUTION",
        content_sha256="b" * 64,
    )
    repository.records[("snapshot", "snapshot")] = SimpleNamespace(
        id="snapshot",
        subject_type="FORMULA_VERSION",
        subject_id="formula",
        result_state="PASS_FOR_DECLARED_SCOPE",
        rule_version_ids_json=["rule-version"],
        jurisdiction="EU",
        product_category="fine-fragrance",
        use_classification="leave-on",
        content_sha256="c" * 64,
    )
    repository.records[("formula", "formula")] = SimpleNamespace(id="formula")
    repository.component_lists["formula"] = [
        SimpleNamespace(id="component", stock_solution_id="stock")
    ]
    repository.records[("stock", "stock")] = SimpleNamespace(
        id="stock",
        material_id="material",
    )
    repository.records[("analytical_entry", "entry")] = SimpleNamespace(
        id="entry",
        sequence_id="sequence",
        role="RI_STANDARD",
        level_json={"material_id": "material"},
        content_sha256="d" * 64,
    )
    repository.records[("sequence", "sequence")] = SimpleNamespace(
        id="sequence",
        status="ACQUIRED",
        method_authority_id="method",
        entry_count=1,
        content_sha256="e" * 64,
    )
    repository.sequence_entries["sequence"] = [
        repository.records[("analytical_entry", "entry")]
    ]
    repository.records[("method", "method")] = SimpleNamespace(
        id="method",
        status="VALIDATED_FOR_SCOPE",
        content_sha256="f" * 64,
    )
    repository.records[("composition_entry", "natural")] = SimpleNamespace(
        id="natural",
        composition_profile_id="profile",
        material_id="material",
        fraction=0.42,
        fraction_basis="MASS_FRACTION",
        content_sha256="1" * 64,
    )
    repository.records[("composition_profile", "profile")] = SimpleNamespace(
        id="profile",
        origin="NATURAL",
        completeness="COMPLETE",
        stock_solution_id="natural-stock",
        supplier_document_binding_id="supplier-document",
        content_sha256="2" * 64,
    )
    return repository


@pytest.mark.asyncio
async def test_b8_resolves_all_scientific_priority_signal_types():
    repository = _signal_repository()
    harness = _SignalHarness(repository)
    now = datetime(2026, 7, 31, tzinfo=timezone.utc)
    cases = (
        ("POTENT_TRACE", "oav", "LITERATURE_DERIVED"),
        ("FAMILY_DRIVER", "rule", "LITERATURE_DERIVED"),
        ("REGULATORY_DRIVER", "snapshot", "LITERATURE_DERIVED"),
        ("ANALYTICAL_STANDARD", "entry", "UNKNOWN"),
        ("NATURAL_CONSTITUENT", "natural", "SUPPLIER_PROVIDED"),
    )

    resolved = [
        await harness._resolve_backfill_signal(
            material_id="material",
            command=BackfillSignalCommand(signal_type=kind, source_id=source),
            as_of_utc=now,
            reviewer_pseudonym="reviewer",
            reviewed_at=now,
        )
        for kind, source, _ in cases
    ]

    assert [row.evidence_class for row in resolved] == [
        expected for _, _, expected in cases
    ]
    assert resolved[0].signal_value["potency_priority"] == pytest.approx(
        250.0
    )
    assert resolved[1].signal_value["driver_count"] == 1
    assert resolved[2].signal_value["driver_count"] == 1
    assert resolved[3].signal_value["standard_role"] == "RI_STANDARD"
    assert resolved[4].signal_value["fraction"] == pytest.approx(0.42)
    assert all(len(row.upstream_content_sha256) == 64 for row in resolved)


@pytest.mark.asyncio
async def test_b8_scientific_signal_resolvers_fail_closed():
    now = datetime(2026, 7, 31, tzinfo=timezone.utc)
    cases = (
        (
            "POTENT_TRACE",
            "oav",
            ("oav", "oav"),
            "status",
            "WITHHELD",
            "BACKFILL_OAV_NOT_STRICT",
        ),
        (
            "FAMILY_DRIVER",
            "rule",
            ("rule", "rule"),
            "status",
            "ADVISORY",
            "BACKFILL_RULE_NOT_AUTHORITATIVE",
        ),
        (
            "REGULATORY_DRIVER",
            "snapshot",
            ("snapshot", "snapshot"),
            "result_state",
            "FAIL",
            "BACKFILL_REGULATORY_NOT_PASSING",
        ),
        (
            "ANALYTICAL_STANDARD",
            "entry",
            ("analytical_entry", "entry"),
            "level_json",
            {"material_id": "other"},
            "BACKFILL_ANALYTICAL_MATERIAL_MISMATCH",
        ),
        (
            "NATURAL_CONSTITUENT",
            "natural",
            ("composition_profile", "profile"),
            "completeness",
            "PARTIAL",
            "BACKFILL_NATURAL_PROFILE_INCOMPLETE",
        ),
    )
    for (
        signal_type,
        source_id,
        record_key,
        field,
        value,
        expected_code,
    ) in cases:
        repository = _signal_repository()
        setattr(repository.records[record_key], field, value)
        harness = _SignalHarness(repository)
        with pytest.raises(BackfillConflictError) as error:
            await harness._resolve_backfill_signal(
                material_id="material",
                command=BackfillSignalCommand(
                    signal_type=signal_type,
                    source_id=source_id,
                ),
                as_of_utc=now,
                reviewer_pseudonym="reviewer",
                reviewed_at=now,
            )
        assert error.value.code == expected_code
