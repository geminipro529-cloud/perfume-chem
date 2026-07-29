from datetime import datetime, timezone

from engine.provenance import (
    Activity,
    Agent,
    AIProposalProvenance,
    Derivation,
    Entity,
    Generation,
    HumanReview,
    ProvenanceRecord,
)


def test_provenance_reconstructs_w3c_shaped_derivation_and_review():
    generated_at = datetime(2026, 7, 30, 8, 0, tzinfo=timezone.utc)
    record = ProvenanceRecord(
        schema_version="provenance-v1",
        entities=(
            Entity("source-1", "SOURCE", "a" * 64),
            Entity("target-1", "TARGET_VERSION", "b" * 64),
        ),
        activities=(
            Activity(
                "activity-1",
                "TARGET_RECONSTRUCTION",
                generated_at,
                generated_at,
                {"temperature_K": 298.15},
            ),
        ),
        agents=(Agent("agent-sol", "HUMAN_REVIEWER", "Sol"),),
        generations=(
            Generation("target-1", "activity-1", generated_at),
        ),
        derivations=(
            Derivation(
                generated_entity_id="target-1",
                source_entity_id="source-1",
                activity_id="activity-1",
                transformation="target-transform-v1",
            ),
        ),
        software_version="perfume-chem:test",
        model_version=None,
        evidence_class="EXACT",
        uncertainty={"state": "bounded"},
        human_review=HumanReview(
            state="APPROVED",
            reviewer_agent_id="agent-sol",
            reviewed_at=generated_at,
            rationale="Fixture reviewed",
        ),
    )

    payload = record.as_prov_dict()
    assert payload["prov:wasDerivedFrom"] == [
        {
            "prov:generatedEntity": "target-1",
            "prov:usedEntity": "source-1",
            "prov:activity": "activity-1",
            "perfume:transformation": "target-transform-v1",
        }
    ]
    assert record.source_entities("target-1") == ("source-1",)
    assert payload["perfume:humanReview"]["state"] == "APPROVED"


def test_ai_proposal_records_prompt_digest_reads_output_and_review():
    proposal = AIProposalProvenance(
        model_id="deepseek-v4-flash",
        instruction_digest="c" * 64,
        records_read=("source-1", "source-2"),
        output_record="target-1",
        review_status="PENDING",
    )
    assert proposal.as_dict() == {
        "model_id": "deepseek-v4-flash",
        "instruction_digest": "c" * 64,
        "records_read": ["source-1", "source-2"],
        "output_record": "target-1",
        "review_status": "PENDING",
    }
