from engine.scientific_contract import EvidenceDescriptor, ScientificClass


def test_evidence_descriptor_serializes_truth_posture():
    evidence = EvidenceDescriptor(
        classification=ScientificClass.HEURISTIC,
        basis="aromatic-only mole fraction with fallback activity coefficients",
        sources=("engine.pipeline.formula_state",),
        assumptions=("finished solvent matrix not represented",),
        limitations=("not a measured headspace concentration",),
    )

    assert evidence.as_dict() == {
        "classification": "HEURISTIC",
        "basis": "aromatic-only mole fraction with fallback activity coefficients",
        "sources": ["engine.pipeline.formula_state"],
        "assumptions": ["finished solvent matrix not represented"],
        "limitations": ["not a measured headspace concentration"],
    }


def test_scientific_classes_have_stable_external_values():
    assert [classification.value for classification in ScientificClass] == [
        "EXACT",
        "LITERATURE_DERIVED",
        "EMPIRICALLY_CALIBRATED",
        "HEURISTIC",
        "SPECULATIVE",
        "UNKNOWN",
    ]
