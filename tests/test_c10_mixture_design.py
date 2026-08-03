from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest
from engine.optimization import (
    C10ContractError,
    CandidateDose,
    CandidateRole,
    DesignStage,
    FamilyFractionRange,
    GateReceipt,
    GateStatus,
    MixtureCandidate,
    MixtureDesignAxis,
    MixtureDomain,
    ModuleActiveRange,
    NegativeSpaceCap,
    NumericRange,
    RecognizerFloor,
    StockDefinition,
    assess_candidate,
    candidate_formula_state_sha256,
    generate_mixture_design,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_SHA = "e" * 64


def _stock(
    stock_id: str,
    material_id: str,
    family: str,
    *,
    active: float,
    carriers: tuple[tuple[str, float], ...],
    available: float = 20.0,
    minimum: float = 1.0,
    increment: float = 1.0,
    cost: float = 1.0,
) -> StockDefinition:
    return StockDefinition(
        stock_id=stock_id,
        material_id=material_id,
        family=family,
        active_mass_fraction=active,
        carrier_mass_fractions=carriers,
        available_raw_mass_mg=available,
        minimum_measurable_raw_mass_mg=minimum,
        dispensing_increment_mg=increment,
        cost_per_raw_mass_mg=cost,
    )


def _domain() -> MixtureDomain:
    return MixtureDomain(
        domain_id="c10-test-domain-v1",
        total_active_mass_mg=NumericRange(4.0, 4.0),
        stocks=(
            _stock(
                "stock-a",
                "material-a",
                "floral",
                active=0.5,
                carriers=(("ethanol", 0.5),),
                minimum=2.0,
                increment=2.0,
                cost=1.0,
            ),
            _stock(
                "stock-b",
                "material-b",
                "woody",
                active=1.0,
                carriers=(),
                increment=1.0,
                cost=2.0,
            ),
        ),
        module_active_mass_ranges=(
            ModuleActiveRange("core", 2.0, 2.0),
            ModuleActiveRange("module", 2.0, 2.0),
        ),
        recognizer_floors=(RecognizerFloor("material-a", 2.0),),
        family_fraction_ranges=(
            FamilyFractionRange("floral", 0.5, 0.5),
            FamilyFractionRange("woody", 0.5, 0.5),
        ),
        negative_space_caps=(NegativeSpaceCap("material-b", 2.0),),
        required_gate_ids=("safety", "action_permission", "applicability"),
        maximum_candidates=100,
    )


def _candidate(
    candidate_id: str = "candidate-1",
    *,
    role: CandidateRole = CandidateRole.SCREENING,
    doses: tuple[CandidateDose, ...] | None = None,
    replicate_of: str | None = None,
) -> MixtureCandidate:
    return MixtureCandidate(
        candidate_id=candidate_id,
        stage=DesignStage.SCREENING,
        role=role,
        doses=doses
        or (
            CandidateDose("stock-a", 4.0, "core"),
            CandidateDose("stock-b", 2.0, "module"),
        ),
        replicate_of=replicate_of,
    )


def _gate_candidate(
    domain: MixtureDomain,
    candidate: MixtureCandidate,
    *,
    statuses: dict[str, GateStatus] | None = None,
    subject_override: str | None = None,
) -> MixtureCandidate:
    formula_hash = subject_override or candidate_formula_state_sha256(domain, candidate)
    status_by_gate = statuses or {}
    receipts = tuple(
        GateReceipt(
            gate_id=gate_id,
            status=status_by_gate.get(gate_id, GateStatus.PASS),
            subject_sha256=formula_hash,
            evidence_sha256=EVIDENCE_SHA,
            authority=f"versioned-{gate_id}-v1",
        )
        for gate_id in domain.required_gate_ids
    )
    return replace(candidate, gate_receipts=receipts)


@pytest.mark.parametrize(
    ("active", "carriers"),
    [
        (0.5, (("ethanol", 0.4),)),
        (0.5, (("ethanol", 0.5), ("ethanol", 0.0))),
        (1.1, ()),
        (0.0, (("ethanol", 1.0),)),
    ],
)
def test_stock_requires_complete_unique_active_and_carrier_partition(
    active: float,
    carriers: tuple[tuple[str, float], ...],
) -> None:
    with pytest.raises(C10ContractError):
        _stock("bad", "material", "family", active=active, carriers=carriers)


def test_candidate_accounting_conserves_raw_active_and_named_carrier_mass() -> None:
    domain = _domain()
    candidate = _gate_candidate(domain, _candidate())

    assessment = assess_candidate(domain, candidate)

    assert assessment.feasible is True
    assert assessment.violations == ()
    assert assessment.accounting.raw_mass_mg == pytest.approx(6.0)
    assert assessment.accounting.active_mass_mg == pytest.approx(4.0)
    assert assessment.accounting.carrier_mass_mg == pytest.approx(2.0)
    assert assessment.accounting.unallocated_mass_mg == pytest.approx(0.0)
    assert dict(assessment.accounting.carrier_masses_mg) == {"ethanol": 2.0}
    assert assessment.accounting.cost == pytest.approx(8.0)
    assert assessment.formula_state_sha256 == candidate_formula_state_sha256(domain, candidate)


@pytest.mark.parametrize(
    ("doses", "expected_code"),
    [
        ((CandidateDose("missing", 4.0, "core"),), "UNKNOWN_STOCK"),
        (
            (
                CandidateDose("stock-a", 2.0, "core"),
                CandidateDose("stock-a", 2.0, "core"),
                CandidateDose("stock-b", 2.0, "module"),
            ),
            "DUPLICATE_STOCK_DOSE",
        ),
        (
            (
                CandidateDose("stock-a", 1.0, "core"),
                CandidateDose("stock-b", 2.0, "module"),
            ),
            "BELOW_MEASURABLE_MINIMUM",
        ),
        (
            (
                CandidateDose("stock-a", 3.0, "core"),
                CandidateDose("stock-b", 2.0, "module"),
            ),
            "OFF_DISPENSING_INCREMENT",
        ),
        (
            (
                CandidateDose("stock-a", 22.0, "core"),
                CandidateDose("stock-b", 2.0, "module"),
            ),
            "INVENTORY_EXCEEDED",
        ),
        (
            (
                CandidateDose("stock-a", 4.0, "module"),
                CandidateDose("stock-b", 2.0, "module"),
            ),
            "MODULE_RANGE_BREACH",
        ),
        (
            (
                CandidateDose("stock-a", 2.0, "core"),
                CandidateDose("stock-b", 3.0, "module"),
            ),
            "TOTAL_ACTIVE_MASS_BREACH",
        ),
    ],
)
def test_candidate_rejects_composition_and_measurement_violations(
    doses: tuple[CandidateDose, ...],
    expected_code: str,
) -> None:
    domain = _domain()
    candidate = _candidate(doses=doses)
    assessment = assess_candidate(domain, candidate)

    assert assessment.feasible is False
    assert expected_code in {item.code for item in assessment.violations}


def test_candidate_rejects_recognizer_family_and_negative_space_breaches() -> None:
    base = _domain()
    candidate = _candidate()
    variants = (
        (
            replace(base, recognizer_floors=(RecognizerFloor("material-a", 2.1),)),
            "RECOGNIZER_FLOOR_BREACH",
        ),
        (
            replace(
                base,
                family_fraction_ranges=(FamilyFractionRange("floral", 0.6, 1.0),),
            ),
            "FAMILY_RANGE_BREACH",
        ),
        (
            replace(base, negative_space_caps=(NegativeSpaceCap("material-b", 1.9),)),
            "NEGATIVE_SPACE_BREACH",
        ),
    )

    for domain, expected_code in variants:
        assessment = assess_candidate(domain, candidate)
        assert expected_code in {item.code for item in assessment.violations}


@pytest.mark.parametrize("status", [GateStatus.FAIL, GateStatus.UNKNOWN])
def test_candidate_rejects_failed_or_unknown_formula_bound_gate(
    status: GateStatus,
) -> None:
    domain = _domain()
    candidate = _gate_candidate(
        domain,
        _candidate(),
        statuses={"safety": status},
    )

    assessment = assess_candidate(domain, candidate)

    assert assessment.feasible is False
    assert "HARD_GATE_NOT_PASS" in {item.code for item in assessment.violations}


def test_candidate_rejects_missing_and_stale_formula_bound_gates() -> None:
    domain = _domain()
    missing = assess_candidate(domain, _candidate())
    stale = assess_candidate(
        domain,
        _gate_candidate(domain, _candidate(), subject_override="a" * 64),
    )

    assert "MISSING_HARD_GATE" in {item.code for item in missing.violations}
    assert "HARD_GATE_SUBJECT_MISMATCH" in {item.code for item in stale.violations}


def test_constrained_mixture_generator_emits_only_feasible_integer_lattice_points() -> None:
    domain = replace(
        _domain(),
        total_active_mass_mg=NumericRange(3.0, 4.0),
        module_active_mass_ranges=(
            ModuleActiveRange("core", 1.0, 2.0),
            ModuleActiveRange("module", 2.0, 2.0),
        ),
        recognizer_floors=(RecognizerFloor("material-a", 1.0),),
        family_fraction_ranges=(),
        negative_space_caps=(),
    )

    result = generate_mixture_design(
        domain,
        axes=(
            MixtureDesignAxis("stock-a", "core", 2.0, 4.0),
            MixtureDesignAxis("stock-b", "module", 1.0, 3.0),
        ),
        stage=DesignStage.SCREENING,
        maximum_combinations=20,
    )

    assert result.truncated is False
    assert result.considered_count == 6
    assert result.rejected_count > 0
    assert result.candidates
    assert len({item.candidate_id for item in result.candidates}) == len(result.candidates)
    for candidate in result.candidates:
        assessment = assess_candidate(domain, candidate, require_gate_receipts=False)
        assert assessment.feasible is True
        for dose in candidate.doses:
            stock = {item.stock_id: item for item in domain.stocks}[dose.stock_id]
            assert dose.raw_mass_mg / stock.dispensing_increment_mg == pytest.approx(
                round(dose.raw_mass_mg / stock.dispensing_increment_mg)
            )


def test_constrained_mixture_generator_reports_visible_bounded_truncation() -> None:
    domain = replace(
        _domain(),
        total_active_mass_mg=NumericRange(0.0, 100.0),
        module_active_mass_ranges=(),
        recognizer_floors=(),
        family_fraction_ranges=(),
        negative_space_caps=(),
    )

    result = generate_mixture_design(
        domain,
        axes=(
            MixtureDesignAxis("stock-a", "core", 2.0, 20.0),
            MixtureDesignAxis("stock-b", "module", 1.0, 20.0),
        ),
        stage=DesignStage.SCREENING,
        maximum_combinations=5,
    )

    assert result.truncated is True
    assert result.considered_count == 5
    assert len(result.candidates) <= 5


def test_c10_runtime_dependency_surface_is_pure_and_deterministic() -> None:
    forbidden_roots = {
        "backend",
        "engine.optimizer",
        "engine.experiments",
        "engine.receptor",
        "engine.hedonic_model",
        "engine.diffusion_model",
        "engine.chemistry.maturation",
        "os",
        "random",
        "sqlite3",
        "time",
        "urllib",
        "requests",
    }
    package = PROJECT_ROOT / "engine" / "optimization"
    runtime_paths = sorted(package.glob("*.py"))
    assert runtime_paths

    imported: set[str] = set()
    for path in runtime_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)

    assert not any(
        imported_name == forbidden or imported_name.startswith(forbidden + ".")
        for imported_name in imported
        for forbidden in forbidden_roots
    )
