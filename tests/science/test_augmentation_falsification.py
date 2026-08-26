from __future__ import annotations

import json
from pathlib import Path

from engine.evidence.augmentation import EvidenceAugmentationState, no_augmentation_receipt
from engine.sensory.ledger import (
    ObservationCellKey,
    SensoryProtocolScope,
    TemporalEvidenceDisposition,
    TemporalEvidenceRequest,
    TemporalObservationCell,
    audit_temporal_evidence,
)
from engine.sensory.order_balance import generate_williams_schedule
from engine.solforge.orchestrator import route_evidence_delta

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/benchmarks/solforge/rebuild_science_v1/manifest.json"


def _scope() -> tuple[SensoryProtocolScope, object]:
    schedule = generate_williams_schedule(("control", "candidate"))
    scope = SensoryProtocolScope(
        protocol_id="science-temporal-v1",
        sample_ids=("control", "candidate"),
        assessor_ids=("p1",),
        repeat_ids=("r1",),
        timepoints_seconds=(0.0, 300.0),
        endpoint_ids=("PERCEIVED_DEPTH",),
        schedule_sha256=schedule.schedule_sha256,
    )
    return scope, schedule


def _cell(sample: str, timepoint: float, value: float, suffix: str = "") -> TemporalObservationCell:
    return TemporalObservationCell(
        key=ObservationCellKey(
            protocol_id="science-temporal-v1",
            sample_id=sample,
            assessor_id="p1",
            repeat_id="r1",
            time_seconds=timepoint,
            endpoint_id="PERCEIVED_DEPTH",
        ),
        observation_id=f"obs-{sample}-{timepoint:g}{suffix}",
        value=value,
        presentation_sequence_id="seq-1",
        presentation_position=1 if sample == "control" else 2,
    )


def test_resolved_temporal_grid_emits_zero_next_action() -> None:
    scope, schedule = _scope()
    audit = audit_temporal_evidence(
        TemporalEvidenceRequest(
            scope=scope,
            schedule=schedule,
            cells=(
                _cell("control", 0, 2.0),
                _cell("control", 300, 2.5),
                _cell("candidate", 0, 2.0),
                _cell("candidate", 300, 4.0),
            ),
        )
    )

    assert audit.disposition is TemporalEvidenceDisposition.RESOLVED
    assert audit.next_discriminator is None
    assert audit.receipt.next_action is None
    assert set(audit.receipt.authority.values()) == {False}


def test_missing_and_conflicted_cells_are_not_imputed() -> None:
    scope, schedule = _scope()
    missing = audit_temporal_evidence(
        TemporalEvidenceRequest(
            scope=scope,
            schedule=schedule,
            cells=(_cell("control", 0, 2.0),),
        )
    )
    conflict = audit_temporal_evidence(
        TemporalEvidenceRequest(
            scope=scope,
            schedule=schedule,
            cells=(
                _cell("control", 0, 2.0),
                _cell("control", 0, 5.0, "-duplicate"),
                _cell("control", 300, 2.5),
                _cell("candidate", 0, 2.0),
                _cell("candidate", 300, 4.0),
            ),
        )
    )

    assert missing.disposition is TemporalEvidenceDisposition.INCOMPLETE
    assert missing.next_discriminator.startswith("COLLECT_CELL:")
    assert conflict.disposition is TemporalEvidenceDisposition.CONFLICTED
    assert conflict.excluded_duplicate_row_count == 2
    assert conflict.next_discriminator.startswith("AUDIT_PROVENANCE:")


def test_no_augmentation_is_a_successful_silent_receipt() -> None:
    receipt = no_augmentation_receipt(
        module_id="architectural_delta",
        exact_scope="reference/already-resolved",
        input_sha256="a" * 64,
        evidence_sha256="b" * 64,
        policy_sha256="c" * 64,
        reasons=("QUESTION_ALREADY_RESOLVED",),
    )
    route = route_evidence_delta(receipt)

    assert route.state is EvidenceAugmentationState.NO_AUGMENTATION
    assert route.receipt_sha256 == receipt.receipt_sha256
    assert route.decision_delta is None
    assert route.advisory_text == ()


def test_manifest_declares_every_critical_trap_and_product_ablation() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    traps = payload["required_falsifications"]
    assert "count inflation" in traps["architectural"]
    assert "Neroli primary misuse" in traps["architectural"]
    assert "unqualified within-sniff" in traps["temporal"]
    assert "row versus assessor-cluster reversal" in traps["preference"]
    assert "OAV and product-narrative ablation" in traps["preference"]
    assert all(
        item["evidence_class"] == "HYPOTHESIS_ONLY"
        for item in payload["reference_architectures"]
    )
