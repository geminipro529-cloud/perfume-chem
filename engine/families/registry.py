"""Data-driven perfume family and archetype grammar.
The registry is intentionally lightweight: it expresses perfumer-readable
anchors and drift limits in terms of raw or active concentrate percentages.
Release gates and optimizers can use the same specs without hardcoded family
thresholds scattered across the codebase.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping
from engine.name_utils import normalize_name
@dataclass(frozen=True, slots=True)
class GroupRule:
    name: str
    materials: tuple[str, ...]
    basis: str = "active"  # "active" or "raw"
    minimum: float | None = None
    maximum: float | None = None
    detail: str = ""
    @property
    def normalized_materials(self) -> frozenset[str]:
        return frozenset(normalize_name(material) for material in self.materials)
@dataclass(frozen=True, slots=True)
class ArchetypeSpec:
    key: str
    family: str
    label: str
    role: str
    anchors: tuple[GroupRule, ...]
    drift_limits: tuple[GroupRule, ...]
    forbidden_materials: tuple[str, ...] = ()
    forbidden_tokens: tuple[str, ...] = ()
    oav_targets: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    repair_pool: Mapping[str, float] = field(default_factory=dict)
    novelty_reference: str = ""
    novelty_message: str = ""
@dataclass(frozen=True, slots=True)
class FamilyCheck:
    name: str
    status: str
    detail: str
    value: float
    rule: GroupRule | None = None
@dataclass(frozen=True, slots=True)
class FamilyEvaluation:
    archetype: str
    family: str
    label: str
    status: str
    checks: tuple[FamilyCheck, ...]
    forbidden_hits: tuple[str, ...] = ()
AROMATIC = (
    "Lavender EO",
    "Lavender EO High Altitude",
    "Spike Lavender EO",
    "Lavender Spike Essential Oil",
    "Clary Sage EO",
    "Petitgrain EO",
    "Juniper Berry EO",
    "Beta-Pinene",
    "Pine EO",
    "Pine Essential Oil",
    "Linalool",
    "Linalyl Acetate",
    "Ethyl Linalool",
    "Dihydromyrcenol",
    "Terpinyl Acetate",
)
CITRUS = (
    "Bergamot FCF",
    "Bergamot",
    "Bergamot FCF Sicilian",
    "Bergamot FCF oil Sicilian",
    "Cedrat FCF Sicilian",
    "Cedrat FCF oil Sicilian",
    "Grapefruit FCF",
    "Red Mandarin EO",
    "Lime Distilled EO",
    "Lime Distilled Essential Oil",
    "Limonene",
    "D-Limonene",
    "Petitgrain EO",
)
FOUGERE_BASE = (
    "Coumarin",
    "Evernyl",
    "Vetiver EO",
    "Patchouli EO",
    "Cedarwood EO",
    "Cedarwood oil Virginia",
    "Iso E Super",
)
MARINE = ("Calone", "Floralozone", "Scentenal")
FRESH_POWER = ("Dihydromyrcenol", "Calone", "Floralozone", "Scentenal")
LOUD_FRUIT = ("Apritone", "Hexyl Acetate", "Ethyl 2-Methylbutyrate", "Methyl Pamplemousse")
GOURMAND = ("Vanillin", "Ethyl Vanillin", "Ethyl Maltol", "Benzoin Resinoid", "Coumarin")
APPLE = ("Apritone", "Hexyl Acetate", "Ethyl 2-Methylbutyrate")
LAYTON_SPICE = ("Terpinyl Acetate", "Eugenol")
LAVENDER_SUPPORT = ("Lavender EO", "Linalool", "Linalyl Acetate", "Ethyl Linalool")
RADIANCE = ("Hedione", "Hedione HC", "Dihydrojasmone")
AMBER_WOOD_MUSK = (
    "Ambrox Super",
    "Ambrofix",
    "Azarbre",
    "Ambermax",
    "Iso E Super",
    "Sandalore",
    "Timberol",
    "Norlimbanol Dextro",
    "Cashmeran",
    "Habanolide",
    "Romandolide",
    "Galaxolide",
    "Ethylene Brassylate",
    "Ambrettolide",
)
FOUGERE_SHADOW = ("Coumarin", "Evernyl", "Vetiver EO", "Patchouli EO", "Cedarwood EO", "Cedarwood oil Virginia")
VETIVER_WOODY = (
    "Vetiver EO",
    "Vetiver EO (India)",
    "Vetival",
    "Vetikon",
    "Cedarwood EO",
    "Cedarwood oil Virginia",
    "Iso E Super",
    "Vertofix",
    "Timberol",
    "Evernyl",
    "Patchouli EO",
    "Koavone",
    "Clearwood",
    "Nagarmortha Oil",
)
WOODY_SPICE = (
    "Black Pepper EO",
    "Black Pepper FTEC",
    "Cardamom EO",
    "Cardamom FTEC",
    "Ethyl Safranate",
    "Eugenol",
    "Isoeugenol",
)
OPAQUE_PREBLENDS = ( "Pink Pepper Base")
def _rule(name: str, materials: tuple[str, ...], *, basis: str = "active", minimum=None, maximum=None, detail="") -> GroupRule:
    return GroupRule(name=name, materials=materials, basis=basis, minimum=minimum, maximum=maximum, detail=detail)
ARCHETYPES: dict[str, ArchetypeSpec] = {
    "aromatic_fougere.classic_reference": ArchetypeSpec(
        key="aromatic_fougere.classic_reference",
        family="aromatic_fougere",
        label="Classic/reference aromatic fougere",
        role="reference_control",
        anchors=(
            _rule("fougere_aromatic_lavender_axis", AROMATIC, minimum=5.0),
            _rule("fougere_citrus_fresh_top", CITRUS, minimum=4.0),
            _rule("fougere_coumarin_tonka_axis", ("Coumarin",), minimum=0.35),
            _rule("fougere_moss_wood_drydown", FOUGERE_BASE, minimum=3.0),
        ),
        drift_limits=(
            _rule("marine_not_shower_gel", MARINE, basis="raw", maximum=7.5),
            _rule("fruit_not_candy_axis", LOUD_FRUIT, maximum=1.0),
        ),
        forbidden_materials=OPAQUE_PREBLENDS,
        oav_targets={
            "top": {"citrus": 900, "aromatic": 260, "fresh": 210},
            "heart": {"aromatic": 260, "coumarin": 16, "green": 80},
            "base": {"aromatic": 95, "wood": 45, "moss": 10, "coumarin": 12},
        },
        repair_pool={"Iso E Super": 2.0, "Vetiver EO": 1.5, "Patchouli EO": 1.2, "Habanolide": 0.8},
        novelty_message="Reference/control archetype; expected to be familiar rather than new.",
    ),
    "aromatic_fougere.modern_mineral": ArchetypeSpec(
        key="aromatic_fougere.modern_mineral",
        family="aromatic_fougere",
        label="Modern mineral aromatic fougere",
        role="modern_exploration",
        anchors=(
            _rule("mineral_fougere_lavender_axis", AROMATIC, minimum=4.5),
            _rule("mineral_fougere_citrus_lift", CITRUS, minimum=4.0),
            _rule("mineral_fougere_coumarin_trace", ("Coumarin",), minimum=0.20),
            _rule("mineral_fougere_moss_wood_backbone", FOUGERE_BASE, minimum=3.0),
            _rule("mineral_signature_present", MARINE + ("Dihydromyrcenol",), basis="raw", minimum=3.0),
        ),
        drift_limits=(
            _rule("marine_not_shower_gel", MARINE, basis="raw", maximum=7.5),
            _rule("dhm_not_functional_flood", ("Dihydromyrcenol",), basis="raw", maximum=8.0),
            _rule("fruit_not_candy_axis", LOUD_FRUIT, maximum=0.8),
        ),
        forbidden_materials=OPAQUE_PREBLENDS,
        oav_targets={
            "top": {"citrus": 1800, "fresh": 1200, "aromatic": 180, "marine": 45},
            "heart": {"fresh": 3200, "aromatic": 700, "marine": 260},
            "base": {"marine": 160, "wood": 70, "aromatic": 30},
        },
        repair_pool={"Iso E Super": 2.0, "Cedarwood EO": 1.5, "Vetiver EO": 1.0, "Habanolide": 0.8},
        novelty_reference="aromatic_fougere.classic_reference",
        novelty_message="Modernity should come from mineral/fresh air while the fougere backbone remains readable.",
    ),
    "aromatic_fougere.modern_tonka_mass": ArchetypeSpec(
        key="aromatic_fougere.modern_tonka_mass",
        family="aromatic_fougere",
        label="Modern tonka mass-appeal aromatic fougere",
        role="modern_exploration",
        anchors=(
            _rule("tonka_fougere_lavender_axis", AROMATIC, minimum=5.0),
            _rule("tonka_fougere_citrus_top", CITRUS, minimum=3.5),
            _rule("tonka_fougere_coumarin_tonka_axis", ("Coumarin",), minimum=0.35),
            _rule("tonka_fougere_moss_wood_backbone", FOUGERE_BASE, minimum=3.0),
            _rule("tonka_mass_hook_present", LOUD_FRUIT + ("Vanillin", "Ethyl Vanillin"), minimum=0.25),
        ),
        drift_limits=(
            _rule("fruit_not_amber_fruity", LOUD_FRUIT, maximum=1.2),
            _rule("gourmand_not_amber_gourmand", GOURMAND, maximum=3.0),
            _rule("marine_not_shower_gel", MARINE, basis="raw", maximum=2.5),
        ),
        forbidden_materials=OPAQUE_PREBLENDS,
        oav_targets={
            "top": {"citrus": 1500, "fruity": 160, "aromatic": 180},
            "heart": {"aromatic": 700, "fruity": 900, "coumarin": 18},
            "base": {"wood": 40, "musk": 18, "coumarin": 12},
        },
        repair_pool={"Iso E Super": 2.0, "Vetiver EO": 1.2, "Habanolide": 1.0, "Ambrox Super": 0.5},
        novelty_reference="aromatic_fougere.classic_reference",
        novelty_message="Novelty should come from a controlled fruit/tonka hook, not an amber-gourmand family switch.",
    ),
    "layton_dna.fresh_thai": ArchetypeSpec(
        key="layton_dna.fresh_thai",
        family="layton_dna",
        label="Fresh Thai Layton DNA-inspired amber",
        role="transparent_layton_trial",
        anchors=(
            _rule("layton_apple_hook", APPLE, minimum=0.12),
            _rule("layton_citrus_lift", CITRUS, minimum=4.0),
            _rule("layton_cardamom_like_spice", LAYTON_SPICE, minimum=0.25),
            _rule("layton_hedione_radiance", RADIANCE, minimum=4.0),
            _rule("layton_amber_wood_musk_base", AMBER_WOOD_MUSK, minimum=18.0),
            _rule("layton_vanilla_coumarin_comfort", GOURMAND, minimum=1.25),
        ),
        drift_limits=(
            _rule("lavender_support_not_theme", LAVENDER_SUPPORT, basis="raw", maximum=8.0),
            _rule("fougere_shadow_not_mossy", FOUGERE_SHADOW, maximum=3.0),
            _rule("fresh_layton_gourmand_not_heavy", GOURMAND, maximum=3.0),
        ),
        forbidden_materials=(),
        forbidden_tokens=(" ftec", " f-tec", " fleuressence", " accord", " base", " fo"),
        oav_targets={
            "top": {"citrus": 1700, "fruity": 85, "fresh": 420, "aromatic": 230},
            "heart": {"citrus": 900, "fruity": 110, "fresh": 780, "amber": 140},
            "base": {"amber": 280, "wood": 45, "musk": 24, "gourmand": 12},
        },
        repair_pool={"Iso E Super": 2.0, "Ambrox Super": 1.5, "Habanolide": 1.2, "Sandalore": 1.0},
    ),
    "layton_dna.indoor_amber": ArchetypeSpec(
        key="layton_dna.indoor_amber",
        family="layton_dna",
        label="Air-conditioned amber Layton DNA-inspired trial",
        role="transparent_layton_trial",
        anchors=(
            _rule("layton_apple_hook", APPLE, minimum=0.10),
            _rule("layton_citrus_lift", CITRUS, minimum=3.0),
            _rule("layton_cardamom_like_spice", LAYTON_SPICE, minimum=0.20),
            _rule("layton_hedione_radiance", RADIANCE, minimum=5.0),
            _rule("layton_amber_wood_musk_base", AMBER_WOOD_MUSK, minimum=20.0),
            _rule("layton_vanilla_coumarin_comfort", GOURMAND, minimum=1.25),
        ),
        drift_limits=(
            _rule("lavender_support_not_theme", LAVENDER_SUPPORT, basis="raw", maximum=8.0),
            _rule("fougere_shadow_not_mossy", FOUGERE_SHADOW, maximum=3.0),
            _rule("indoor_gourmand_not_heavy", GOURMAND, maximum=3.4),
        ),
        forbidden_materials=(),
        forbidden_tokens=(" ftec", " f-tec", " fleuressence", " accord", " base", " fo"),
        oav_targets={
            "top": {"citrus": 1150, "fruity": 65, "aromatic": 175, "amber": 190},
            "heart": {"amber": 145, "fruity": 85, "radiance": 140, "wood": 70},
            "base": {"amber": 145, "wood": 42, "musk": 24, "gourmand": 12},
        },
        repair_pool={"Iso E Super": 2.0, "Ambrox Super": 1.5, "Habanolide": 1.2, "Sandalore": 1.0},
    ),
    "layton_dna.night_intense": ArchetypeSpec(
        key="layton_dna.night_intense",
        family="layton_dna",
        label="Night intense Layton DNA-inspired trial",
        role="transparent_layton_trial",
        anchors=(
            _rule("layton_apple_hook", APPLE, minimum=0.12),
            _rule("layton_citrus_lift", CITRUS, minimum=3.0),
            _rule("layton_cardamom_like_spice", LAYTON_SPICE, minimum=0.25),
            _rule("layton_hedione_radiance", RADIANCE, minimum=3.5),
            _rule("layton_amber_wood_musk_base", AMBER_WOOD_MUSK, minimum=20.0),
            _rule("layton_vanilla_coumarin_comfort", GOURMAND, minimum=1.5),
        ),
        drift_limits=(
            _rule("lavender_support_not_theme", LAVENDER_SUPPORT, basis="raw", maximum=8.0),
            _rule("fougere_shadow_not_mossy", FOUGERE_SHADOW, maximum=3.2),
            _rule("night_gourmand_not_overweight", GOURMAND, maximum=4.2),
        ),
        forbidden_materials=(),
        forbidden_tokens=(" ftec", " f-tec", " fleuressence", " accord", " base", " fo"),
        oav_targets={
            "top": {"citrus": 1200, "fruity": 85, "aromatic": 180, "amber": 190},
            "heart": {"amber": 165, "fruity": 115, "radiance": 105, "wood": 70},
            "base": {"amber": 165, "wood": 72, "musk": 25, "gourmand": 20},
        },
        repair_pool={"Iso E Super": 2.0, "Ambrox Super": 1.5, "Habanolide": 1.2, "Sandalore": 1.0},
    ),
    "woody.vetiver_classical": ArchetypeSpec(
        key="woody.vetiver_classical",
        family="woody",
        label="Classical vetiver woody",
        role="reference_control",
        anchors=(
            _rule("vetiver_star_axis", ("Vetiver EO", "Vetiver EO (India)", "Vetival"), minimum=8.0),
            _rule("citrus_fresh_top", CITRUS, minimum=6.0),
            _rule("woody_spine", VETIVER_WOODY, minimum=12.0),
            _rule("moss_structure", ("Evernyl",), minimum=0.3),
            _rule("coumarin_warmth", ("Coumarin",), minimum=0.3),
            _rule("tobacco_resin_depth", ("Tobacco Absolute",), minimum=0.1),
        ),
        drift_limits=(
            _rule("not_gourmand", GOURMAND, maximum=2.5),
            _rule("not_aquatic", MARINE, basis="raw", maximum=2.0),
            _rule("not_aromatic_fougere", AROMATIC, maximum=4.0),
            _rule("fruit_not_candy", LOUD_FRUIT, maximum=0.8),
        ),
        forbidden_materials=OPAQUE_PREBLENDS,
        forbidden_tokens=(" ftec", " f-tec", " fleuressence", " accord", " base", " fo"),
        oav_targets={
            "top": {"citrus": 1200, "spice": 80, "aromatic": 120, "green": 60},
            "heart": {"woody": 800, "floral": 250, "spice": 40, "radiance": 150},
            "base": {"wood": 120, "musk": 35, "moss": 12, "coumarin": 18},
        },
        repair_pool={"Iso E Super": 2.0, "Vetiver EO": 1.5, "Cedarwood EO": 1.2, "Habanolide": 0.8},
        novelty_message="Classical vetiver reference; expected to be familiar rather than novel.",
    ),
}
BRIEF_DEFAULTS = {
    "aromatic_fougere": "aromatic_fougere.classic_reference",
    "layton_dna": "layton_dna.fresh_thai",
    "vetiver_woody": "woody.vetiver_classical",
}
def all_archetypes() -> tuple[ArchetypeSpec, ...]:
    return tuple(ARCHETYPES.values())
def infer_archetype(brief: str = "auto", family_archetype: str = "") -> str:
    requested = str(family_archetype or "").strip()
    if requested:
        return requested
    return BRIEF_DEFAULTS.get(str(brief or "").strip(), "")
def get_archetype(key: str) -> ArchetypeSpec | None:
    return ARCHETYPES.get(str(key or "").strip())
def _formula_percentages(formula: Mapping) -> tuple[Mapping[str, float], Mapping[str, float]]:
    ingredients = formula.get("ingredients_pct") or {}
    if not ingredients and formula.get("ingredients_ul"):
        total = sum(float(v or 0.0) for v in formula.get("ingredients_ul", {}).values()) or 1.0
        ingredients = {
            material: float(amount or 0.0) / total * 100.0
            for material, amount in formula.get("ingredients_ul", {}).items()
        }
    dilutions = formula.get("dilutions") or {}
    return ingredients, dilutions
def group_value(formula: Mapping, rule: GroupRule) -> float:
    ingredients, dilutions = _formula_percentages(formula)
    material_set = rule.normalized_materials
    total = 0.0
    for material, raw_pct in ingredients.items():
        if normalize_name(str(material)) not in material_set:
            continue
        value = float(raw_pct or 0.0)
        if rule.basis == "active":
            value *= float(dilutions.get(material, 1.0) or 1.0)
        total += value
    return total
def forbidden_hits(formula: Mapping, spec: ArchetypeSpec) -> tuple[str, ...]:
    ingredients, _dilutions = _formula_percentages(formula)
    forbidden = {normalize_name(material) for material in spec.forbidden_materials}
    token_hits = []
    exact_hits = []
    for material in ingredients:
        normalized = normalize_name(str(material))
        raw = f" {str(material).lower()} "
        if normalized in forbidden:
            exact_hits.append(str(material))
        elif any(token in raw for token in spec.forbidden_tokens):
            token_hits.append(str(material))
    return tuple(sorted(set(exact_hits + token_hits)))
def _check_rule(rule: GroupRule, value: float) -> FamilyCheck:
    status = "PASS"
    parts = []
    unit = "% raw" if rule.basis == "raw" else "% active"
    if rule.minimum is not None:
        parts.append(f"{value:.3f}{unit} >= {rule.minimum:.3f}")
        if value < rule.minimum:
            status = "FAIL"
            parts[-1] = f"{value:.3f}{unit} below {rule.minimum:.3f}"
    if rule.maximum is not None:
        parts.append(f"{value:.3f}{unit} <= {rule.maximum:.3f}")
        if value > rule.maximum:
            status = "FAIL"
            parts[-1] = f"{value:.3f}{unit} above {rule.maximum:.3f}"
    if rule.detail:
        parts.append(rule.detail)
    return FamilyCheck(name=rule.name, status=status, detail="; ".join(parts), value=round(value, 6), rule=rule)
def evaluate_family_archetype(formula: Mapping, archetype: str) -> FamilyEvaluation:
    spec = get_archetype(archetype)
    if spec is None:
        return FamilyEvaluation(
            archetype=str(archetype or ""),
            family="unknown",
            label="unknown",
            status="WARN" if archetype else "PASS",
            checks=(),
        )
    checks = [
        _check_rule(rule, group_value(formula, rule))
        for rule in (*spec.anchors, *spec.drift_limits)
    ]
    hits = forbidden_hits(formula, spec)
    if hits:
        checks.append(
            FamilyCheck(
                name="forbidden_archetype_materials",
                status="FAIL",
                detail=", ".join(hits),
                value=float(len(hits)),
            )
        )
    status = "FAIL" if any(check.status == "FAIL" for check in checks) else "PASS"
    return FamilyEvaluation(
        archetype=spec.key,
        family=spec.family,
        label=spec.label,
        status=status,
        checks=tuple(checks),
        forbidden_hits=hits,
    )
def archetype_penalty(formula: Mapping, archetype: str, *, fail_weight: float = 4.0) -> float:
    evaluation = evaluate_family_archetype(formula, archetype)
    return sum(fail_weight for check in evaluation.checks if check.status == "FAIL")
def novelty_assessment(formula: Mapping, archetype: str) -> dict:
    spec = get_archetype(archetype)
    if spec is None:
        return {"status": "PASS", "detail": "not requested", "score": 1.0}
    if spec.key == "aromatic_fougere.classic_reference":
        return {
            "status": "WARN",
            "detail": "reference/control archetype; familiar by design, not the new exploration target",
            "score": 0.0,
        }
    if spec.key == "aromatic_fougere.modern_mineral":
        signature = group_value(formula, _rule("mineral_signature_present", MARINE + ("Dihydromyrcenol",), basis="raw"))
        status = "PASS" if signature >= 3.0 else "WARN"
        return {
            "status": status,
            "detail": f"mineral/fresh signature {signature:.2f}% raw; target >= 3.00 for meaningful modernity",
            "score": min(signature / 3.0, 1.0),
        }
    if spec.key == "aromatic_fougere.modern_tonka_mass":
        signature = group_value(formula, _rule("tonka_mass_hook_present", LOUD_FRUIT + ("Vanillin", "Ethyl Vanillin")))
        status = "PASS" if signature >= 0.25 else "WARN"
        return {
            "status": status,
            "detail": f"fruit/tonka mass hook {signature:.2f}% active; target >= 0.25 for meaningful modernity",
            "score": min(signature / 0.25, 1.0),
        }
    if spec.key == "woody.vetiver_classical":
        return {
            "status": "WARN",
            "detail": "reference/control archetype; familiar by design, not the new exploration target",
            "score": 0.0,
        }
    return {
        "status": "PASS",
        "detail": f"{spec.label}; novelty judged against Layton DNA transparency rather than fougere reference",
        "score": 1.0,
    }