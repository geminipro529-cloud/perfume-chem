from pathlib import Path

from engine.families.registry import all_archetypes
from engine.family_scorer import get_family_weights
from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from scripts.verify_formula_workflow import parse_formula_markdown


EXPECTED_ARCHETYPES = {
    "aromatic_fougere.classic_reference",
    "aromatic_fougere.modern_mineral",
    "aromatic_fougere.modern_tonka_mass",
    "citrus_classical.4711_reference",
    "citrus_aromatic.eau_sauvage_reference",
    "floral_soliflore.rose_reference",
    "floral_bouquet.quelques_fleurs_reference",
    "floral_white.fracas_reference",
    "floral_muguet.diorissimo_reference",
    "floral_carnation.bellodgia_reference",
    "floral_powdery.apres_londee_reference",
    "floral_green.no19_reference",
    "floral_aldehydic.no5_reference",
    "fougere_classical.fougere_royale_reference",
    "aromatic_fougere.azzaro_reference",
    "chypre_classical.coty_reference",
    "chypre_floral.miss_dior_reference",
    "chypre_fruity.mitsouko_reference",
    "chypre_green.vent_vert_reference",
    "chypre_leathery.bandit_reference",
    "oriental_classical.shalimar_reference",
    "oriental_soft.jicky_reference",
    "oriental_floral.lheure_bleue_reference",
    "layton_dna.fresh_thai",
    "layton_dna.indoor_amber",
    "layton_dna.night_intense",
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STUDY_DIR = PROJECT_ROOT / "formulas" / "classical_study"


def _formula(ingredients, archetype, brief):
    total = sum(ingredients.values()) or 1.0
    return {
        "number": 1,
        "name": "Archetype Test",
        "body": "Archetype Test",
        "family_archetype": archetype,
        "ingredients_ul": dict(ingredients),
        "ingredients_pct": {k: v / total * 100.0 for k, v in ingredients.items()},
        "dilutions": {},
    }


def _gate_map(report):
    return {gate.gate: gate for gate in report.gates}


def _assert_advisory_drift_failure(gate):
    assert gate.status == "WARN"
    assert gate.data["original_status"] == "FAIL"


def _assert_resolved_reference_drift(gate):
    assert "unknown family archetype" not in gate.detail.lower()
    assert gate.status in {"PASS", "WARN"}
    if gate.status == "WARN":
        assert gate.data["original_status"] == "FAIL"


def _formula_from_file(name: str):
    formulas = parse_formula_markdown(STUDY_DIR / name)
    assert formulas, name
    return formulas[0]


def test_family_registry_has_required_archetype_specs():
    specs = {spec.key: spec for spec in all_archetypes()}

    assert EXPECTED_ARCHETYPES <= set(specs)
    for key in EXPECTED_ARCHETYPES:
        spec = specs[key]
        assert spec.anchors
        assert spec.drift_limits
        assert spec.repair_pool
        assert spec.oav_targets


def test_family_weight_aliases_resolve_dotted_historical_keys():
    assert get_family_weights("citrus_classical.4711_reference") == get_family_weights("citrus_classical")
    assert get_family_weights("fougere_classical.fougere_royale_reference") == get_family_weights("fougere_classical")
    assert get_family_weights("chypre_classical.coty_reference") == get_family_weights("chypre_classical")
    assert get_family_weights("oriental_floral.lheure_bleue_reference") == get_family_weights("oriental_floral")


def test_classical_study_markdown_smoke_files_parse_and_gate_without_unknown_family():
    for name in (
        "01_Eau_de_Cologne_4711_30mL_EdC.md",
        "04_Floral_Bouquet_Quelques_Fleurs_30mL_EdP.md",
        "11_Classic_Fougere_Fougere_Royale_30mL_EdT.md",
        "13_Classic_Chypre_Coty_30mL_EdP.md",
        "18_Classic_Oriental_Shalimar_30mL_EdP.md",
    ):
        formula = _formula_from_file(name)
        total = sum(formula["ingredients_ul"].values())
        report = gate_formula(
            formula,
            ReleaseGateConfig(
                brief="generic",
                family_archetype=formula["family_archetype"],
                expected_concentrate_ul=total,
                audit_enabled=False,
            ),
        )
        gates = _gate_map(report)

        _assert_resolved_reference_drift(gates["family_drift_detector"])


def test_classic_fougere_passes_drift_but_warns_low_novelty():
    formula = _formula(
        {
            "Bergamot FCF": 1200.0,
            "Lavender EO": 700.0,
            "Linalyl Acetate": 600.0,
            "Hedione": 900.0,
            "Coumarin": 300.0,
            "Evernyl": 10.0,
            "Iso E Super": 1500.0,
            "Vetiver EO": 300.0,
            "Habanolide": 490.0,
        },
        "aromatic_fougere.classic_reference",
        "aromatic_fougere",
    )
    gates = _gate_map(gate_formula(formula, ReleaseGateConfig(brief="aromatic_fougere", audit_enabled=False)))

    assert gates["family_drift_detector"].status == "PASS"
    assert gates["novelty_vs_reference"].status == "WARN"


def test_cologne_reference_resolves_drift_and_warns_low_novelty():
    formula = _formula_from_file("01_Eau_de_Cologne_4711_30mL_EdC.md")
    total = sum(formula["ingredients_ul"].values())
    gates = _gate_map(
        gate_formula(
            formula,
            ReleaseGateConfig(
                brief="generic",
                family_archetype=formula["family_archetype"],
                expected_concentrate_ul=total,
                audit_enabled=False,
            ),
        )
    )

    _assert_resolved_reference_drift(gates["family_drift_detector"])
    assert gates["novelty_vs_reference"].status == "WARN"


def test_cologne_reference_fails_when_resinous_base_overwhelms_citrus():
    formula = _formula(
        {
            "Bergamot FCF oil Sicilian": 200.0,
            "Lemon FCF oil Sicilian": 100.0,
            "Aurantiol": 120.0,
            "Siam Benzoin": 900.0,
            "Patchouli EO": 900.0,
            "Vanillin": 600.0,
            "Iso E Super": 500.0,
            "Ethylene Brassylate": 280.0,
        },
        "citrus_classical.4711_reference",
        "generic",
    )
    gates = _gate_map(
        gate_formula(
            formula,
            ReleaseGateConfig(
                brief="generic",
                family_archetype="citrus_classical.4711_reference",
                expected_concentrate_ul=sum(formula["ingredients_ul"].values()),
                audit_enabled=False,
            ),
        )
    )

    _assert_advisory_drift_failure(gates["family_drift_detector"])


def test_fougere_royale_reference_passes_drift_but_warns_low_novelty():
    formula = _formula_from_file("11_Classic_Fougere_Fougere_Royale_30mL_EdT.md")
    total = sum(formula["ingredients_ul"].values())
    gates = _gate_map(
        gate_formula(
            formula,
            ReleaseGateConfig(
                brief="generic",
                family_archetype=formula["family_archetype"],
                expected_concentrate_ul=total,
                audit_enabled=False,
            ),
        )
    )

    assert gates["family_drift_detector"].status == "PASS"
    assert gates["novelty_vs_reference"].status == "WARN"


def test_mineral_fougere_fails_when_marine_fresh_floods_backbone():
    formula = _formula(
        {
            "Bergamot FCF": 600.0,
            "Lavender EO": 200.0,
            "Coumarin": 50.0,
            "Evernyl": 10.0,
            "Iso E Super": 500.0,
            "Dihydromyrcenol": 3000.0,
            "Calone": 1000.0,
            "Floralozone": 640.0,
        },
        "aromatic_fougere.modern_mineral",
        "aromatic_fougere",
    )
    gates = _gate_map(gate_formula(formula, ReleaseGateConfig(brief="aromatic_fougere", audit_enabled=False)))

    _assert_advisory_drift_failure(gates["family_drift_detector"])
    assert "marine_not_shower_gel" in gates["family_drift_detector"].detail


def test_tonka_fougere_fails_when_it_becomes_fruity_gourmand_amber():
    formula = _formula(
        {
            "Bergamot FCF": 600.0,
            "Lavender EO": 400.0,
            "Coumarin": 500.0,
            "Evernyl": 10.0,
            "Iso E Super": 700.0,
            "Apritone": 1500.0,
            "Hexyl Acetate": 800.0,
            "Vanillin": 800.0,
            "Ethyl Vanillin": 690.0,
        },
        "aromatic_fougere.modern_tonka_mass",
        "aromatic_fougere",
    )
    gates = _gate_map(gate_formula(formula, ReleaseGateConfig(brief="aromatic_fougere", audit_enabled=False)))

    _assert_advisory_drift_failure(gates["family_drift_detector"])
    assert "fruit_not_amber_fruity" in gates["family_drift_detector"].detail


def test_layton_fails_when_moss_coumarin_turns_it_into_fougere():
    formula = _formula(
        {
            "Bergamot FCF": 600.0,
            "Apritone": 80.0,
            "Hexyl Acetate": 50.0,
            "Ethyl 2-Methylbutyrate": 20.0,
            "Terpinyl Acetate": 100.0,
            "Eugenol": 20.0,
            "Hedione": 500.0,
            "Iso E Super": 1000.0,
            "Ambrox Super": 1000.0,
            "Sandalore": 500.0,
            "Habanolide": 500.0,
            "Vanillin": 300.0,
            "Coumarin": 700.0,
            "Evernyl": 200.0,
            "Vetiver EO": 430.0,
        },
        "layton_dna.fresh_thai",
        "layton_dna",
    )
    gates = _gate_map(gate_formula(formula, ReleaseGateConfig(brief="layton_dna", audit_enabled=False)))

    _assert_advisory_drift_failure(gates["family_drift_detector"])
    assert "fougere_shadow_not_mossy" in gates["family_drift_detector"].detail


def test_layton_fails_when_signature_top_and_base_disappear():
    formula = _formula(
        {
            "Bergamot FCF": 2000.0,
            "Lavender EO": 1000.0,
            "Hedione": 1000.0,
            "Vanillin": 100.0,
            "Ethyl Vanillin": 100.0,
            "Linalyl Acetate": 900.0,
            "Dihydromyrcenol": 900.0,
        },
        "layton_dna.fresh_thai",
        "layton_dna",
    )
    gates = _gate_map(gate_formula(formula, ReleaseGateConfig(brief="layton_dna", audit_enabled=False)))

    _assert_advisory_drift_failure(gates["family_drift_detector"])
    assert "layton_apple_hook" in gates["family_drift_detector"].detail
    assert "layton_cardamom_like_spice" in gates["family_drift_detector"].detail


def test_floral_bouquet_reference_resolves_drift_and_warns_low_novelty():
    formula = _formula_from_file("04_Floral_Bouquet_Quelques_Fleurs_30mL_EdP.md")
    total = sum(formula["ingredients_ul"].values())
    gates = _gate_map(
        gate_formula(
            formula,
            ReleaseGateConfig(
                brief="generic",
                family_archetype=formula["family_archetype"],
                expected_concentrate_ul=total,
                audit_enabled=False,
            ),
        )
    )

    _assert_resolved_reference_drift(gates["family_drift_detector"])
    assert gates["novelty_vs_reference"].status == "WARN"


def test_green_floral_fails_when_it_turns_into_fruity_amber():
    formula = _formula(
        {
            "Galbanum Resinoid": 30.0,
            "Phenethyl Alcohol": 150.0,
            "Hydroxycitronellal": 100.0,
            "Apritone": 1200.0,
            "Vanillin": 700.0,
            "Ethyl Vanillin": 600.0,
            "Iso E Super": 1200.0,
            "Galaxolide": 1200.0,
            "Siam Benzoin": 820.0,
        },
        "floral_green.no19_reference",
        "generic",
    )
    gates = _gate_map(
        gate_formula(
            formula,
            ReleaseGateConfig(
                brief="generic",
                family_archetype="floral_green.no19_reference",
                expected_concentrate_ul=sum(formula["ingredients_ul"].values()),
                audit_enabled=False,
            ),
        )
    )

    _assert_advisory_drift_failure(gates["family_drift_detector"])


def test_chypre_classical_reference_resolves_drift_and_warns_low_novelty():
    formula = _formula_from_file("13_Classic_Chypre_Coty_30mL_EdP.md")
    total = sum(formula["ingredients_ul"].values())
    gates = _gate_map(
        gate_formula(
            formula,
            ReleaseGateConfig(
                brief="generic",
                family_archetype=formula["family_archetype"],
                expected_concentrate_ul=total,
                audit_enabled=False,
            ),
        )
    )

    _assert_resolved_reference_drift(gates["family_drift_detector"])
    assert gates["novelty_vs_reference"].status == "WARN"


def test_leather_chypre_fails_when_juicy_fruit_and_vanilla_replace_leather_spine():
    formula = _formula(
        {
            "Bergamot FCF oil Sicilian": 220.0,
            "Patchouli EO": 220.0,
            "Evernyl": 60.0,
            "Apritone": 1100.0,
            "Hexyl Acetate": 1000.0,
            "Vanillin": 850.0,
            "Ethyl Vanillin": 760.0,
            "Galaxolide": 800.0,
            "Iso E Super": 990.0,
        },
        "chypre_leathery.bandit_reference",
        "generic",
    )
    gates = _gate_map(
        gate_formula(
            formula,
            ReleaseGateConfig(
                brief="generic",
                family_archetype="chypre_leathery.bandit_reference",
                expected_concentrate_ul=sum(formula["ingredients_ul"].values()),
                audit_enabled=False,
            ),
        )
    )

    _assert_advisory_drift_failure(gates["family_drift_detector"])


def test_oriental_classical_reference_passes_drift_but_warns_low_novelty():
    formula = _formula_from_file("18_Classic_Oriental_Shalimar_30mL_EdP.md")
    total = sum(formula["ingredients_ul"].values())
    gates = _gate_map(
        gate_formula(
            formula,
            ReleaseGateConfig(
                brief="generic",
                family_archetype=formula["family_archetype"],
                expected_concentrate_ul=total,
                audit_enabled=False,
            ),
        )
    )

    assert gates["family_drift_detector"].status == "PASS"
    assert gates["novelty_vs_reference"].status == "WARN"


def test_soft_oriental_fails_when_blue_fresh_materials_displace_amber_core():
    formula = _formula(
        {
            "Bergamot FCF oil Sicilian": 260.0,
            "Lavender EO": 150.0,
            "Dihydromyrcenol": 2200.0,
            "Calone": 900.0,
            "Floralozone": 900.0,
            "Iso E Super": 700.0,
            "Galaxolide": 600.0,
            "Ethylene Brassylate": 290.0,
        },
        "oriental_soft.jicky_reference",
        "generic",
    )
    gates = _gate_map(
        gate_formula(
            formula,
            ReleaseGateConfig(
                brief="generic",
                family_archetype="oriental_soft.jicky_reference",
                expected_concentrate_ul=sum(formula["ingredients_ul"].values()),
                audit_enabled=False,
            ),
        )
    )

    _assert_advisory_drift_failure(gates["family_drift_detector"])
