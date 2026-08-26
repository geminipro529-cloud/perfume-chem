from engine.release_readiness import (
    ReadinessInput,
    ReadinessStatus,
    build_release_readiness,
)


def test_laboratory_beta_can_be_ready_while_scientific_release_is_blocked():
    report = build_release_readiness(
        ReadinessInput(
            code_checks_passed=True,
            data_contracts_passed=True,
            local_validation_passed=True,
            migration_verified=True,
            backup_restore_verified=True,
            heldout_sensory_validation_passed=False,
        )
    )

    assert report.laboratory_beta_status is ReadinessStatus.READY
    assert report.scientific_release_status is ReadinessStatus.BLOCKED
    assert report.axes["code"].status is ReadinessStatus.READY
    assert report.axes["data"].status is ReadinessStatus.READY
    assert report.axes["validation"].status is ReadinessStatus.BLOCKED
    assert report.axes["infrastructure"].status is ReadinessStatus.READY
    assert "held-out sensory validation" in report.external_blockers[0]
    assert all("hosted" not in blocker.lower() for blocker in report.external_blockers)
    assert report.evidence.classification.value == "EXACT"


def test_code_failure_blocks_both_beta_and_release():
    report = build_release_readiness(
        ReadinessInput(
            code_checks_passed=False,
            data_contracts_passed=True,
            local_validation_passed=True,
            migration_verified=True,
            backup_restore_verified=True,
            heldout_sensory_validation_passed=True,
        )
    )

    assert report.laboratory_beta_status is ReadinessStatus.BLOCKED
    assert report.scientific_release_status is ReadinessStatus.BLOCKED
    assert report.axes["code"].status is ReadinessStatus.BLOCKED


def test_all_gates_ready_supports_scientific_release_status():
    report = build_release_readiness(
        ReadinessInput(
            code_checks_passed=True,
            data_contracts_passed=True,
            local_validation_passed=True,
            migration_verified=True,
            backup_restore_verified=True,
            heldout_sensory_validation_passed=True,
        )
    )

    assert report.laboratory_beta_status is ReadinessStatus.READY
    assert report.scientific_release_status is ReadinessStatus.READY
    assert all(axis.status is ReadinessStatus.READY for axis in report.axes.values())
