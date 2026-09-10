"""Versioned truth contracts for named-fragrance claims.

Family/archetype gates remain creative diagnostics.  A named commercial
reference is a provenance claim and must opt into one of the bounded contracts
below.  Official note pyramids can support architecture checks only; they do
not provide formula ratios, GC-MS composition, or sensory-equivalence evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping, cast

from engine.name_utils import normalize_name

if TYPE_CHECKING:
    from engine.pipeline.formula_state import FormulaState


ARCHITECTURE = "architecture"
QUANTITATIVE_SIMILARITY = "quantitative_similarity"
SENSORY_SIMILARITY = "sensory_similarity"
UNCLAIMED = "unclaimed"
NAMED_REFERENCE = "named_reference"


@dataclass(frozen=True, slots=True)
class ReferenceMarkerGroup:
    name: str
    alternatives: tuple[str, ...]
    layer: str = "unspecified"
    prominence: str = "required"


@dataclass(frozen=True, slots=True)
class ReferenceContract:
    contract_id: str
    display_name: str
    target_aliases: tuple[str, ...]
    allowed_scopes: tuple[str, ...]
    marker_groups: tuple[ReferenceMarkerGroup, ...]
    source_url: str
    evidence_class: str
    version: int = 1


MONTBLANC_EXPLORER_OFFICIAL_NOTES_V1 = ReferenceContract(
    contract_id="montblanc_explorer_official_notes_v1",
    display_name="Montblanc Explorer",
    target_aliases=("montblanc explorer", "mont blanc explorer", "explorer"),
    allowed_scopes=(ARCHITECTURE,),
    marker_groups=(
        ReferenceMarkerGroup("bergamot", ("bergamot",)),
        ReferenceMarkerGroup(
            "pomarose_or_sage",
            ("pink pepper", "pomarose", "clary sage", "sage"),
        ),
        ReferenceMarkerGroup("vetiver", ("vetiver", "vetival")),
        ReferenceMarkerGroup(
            "leather_or_sandalwood",
            (
                "leather",
                "suederal",
                "isobutyl quinoline",
                "sandalwood",
                "javanol",
                "sandalore",
            ),
        ),
        ReferenceMarkerGroup("patchouli", ("patchouli", "clearwood")),
        ReferenceMarkerGroup(
            "amberwood",
            ("ambrofix", "ambrox", "akigalawood"),
        ),
    ),
    source_url="https://www.montblanc.com/en-ph/fragrances/collection/explorer",
    evidence_class="official_brand_note_architecture_only",
)


CREED_AVENTUS_OFFICIAL_NOTES_V1 = ReferenceContract(
    contract_id="creed_aventus_official_notes_v1",
    display_name="Creed Aventus",
    # Retained for explicit historical receipts only. Current aliases resolve to V2.
    target_aliases=(),
    allowed_scopes=(ARCHITECTURE,),
    marker_groups=(
        ReferenceMarkerGroup("citrus", ("bergamot", "lemon")),
        ReferenceMarkerGroup("blackcurrant", ("blackcurrant", "cassis")),
        ReferenceMarkerGroup(
            "pineapple",
            (
                "pineapple",
                "allyl amyl glycolate",
                "allyl cyclohexyl propionate",
                "dynascone",
                "blackcurrant",
                "cassis",
            ),
        ),
        ReferenceMarkerGroup(
            "pink_pepper_or_jasmine",
            ("pink pepper", "jasmine", "hedione", "jasmone"),
        ),
        ReferenceMarkerGroup(
            "smoky_birch",
            (
                "birch tar",
                "birch",
                "cypriol",
                "nagarmotha",
                "isobutyl quinoline",
                "leather",
            ),
        ),
        ReferenceMarkerGroup("patchouli", ("patchouli", "clearwood")),
        ReferenceMarkerGroup(
            "musk",
            (
                "musk",
                "ethylene brassylate",
                "zenolide",
                "ambrettolide",
                "exaltolide",
                "helvetolide",
            ),
        ),
    ),
    source_url="https://creedboutique.com/products/aventus",
    evidence_class="official_brand_note_architecture_only",
)


CREED_AVENTUS_OFFICIAL_NOTES_V2 = ReferenceContract(
    contract_id="creed_aventus_official_notes_v2",
    display_name="Creed Aventus",
    target_aliases=("creed aventus", "aventus"),
    allowed_scopes=(ARCHITECTURE,),
    marker_groups=(
        ReferenceMarkerGroup(
            "bergamot",
            ("bergamot", "bergamot fcf", "bergamot fcf oil sicilian"),
            layer="head",
            prominence="primary",
        ),
        ReferenceMarkerGroup(
            "blackcurrant",
            ("blackcurrant", "cassis"),
            layer="head",
            prominence="primary",
        ),
        ReferenceMarkerGroup(
            "pineapple",
            (
                "pineapple",
                "allyl amyl glycolate",
                "allyl cyclohexyl propionate",
                "dynascone",
            ),
            layer="heart",
            prominence="secondary",
        ),
        ReferenceMarkerGroup(
            "pink_pepper",
            ("pink pepper", "schinus molle"),
            layer="heart",
            prominence="supporting",
        ),
        ReferenceMarkerGroup(
            "jasmine_radiance",
            ("jasmine", "hedione", "jasmone", "dihydrojasmone"),
            layer="heart",
            prominence="supporting",
        ),
        ReferenceMarkerGroup(
            "smoky_birch",
            (
                "birch tar",
                "birch",
                "cypriol",
                "nagarmotha",
                "isobutyl quinoline",
                "leather",
                "cade oil rectified",
                "suederal",
            ),
            layer="base",
            prominence="primary",
        ),
        ReferenceMarkerGroup(
            "patchouli",
            ("patchouli", "clearwood"),
            layer="base",
            prominence="primary",
        ),
        ReferenceMarkerGroup(
            "musk",
            (
                "musk",
                "ethylene brassylate",
                "romandolide",
                "habanolide",
                "zenolide",
                "ambrettolide",
                "exaltolide",
                "helvetolide",
            ),
            layer="base",
            prominence="primary",
        ),
    ),
    source_url="https://creedboutique.com/products/aventus",
    evidence_class="official_brand_note_architecture_only_current_us_page_2026_09_04",
    version=2,
)


PRADA_LHOMME_OFFICIAL_NOTES_V1 = ReferenceContract(
    contract_id="prada_lhomme_official_notes_v1",
    display_name="Prada L'Homme",
    target_aliases=(
        "prada l'homme",
        "prada l homme",
        "l'homme prada",
        "l homme prada",
    ),
    allowed_scopes=(ARCHITECTURE,),
    marker_groups=(
        ReferenceMarkerGroup("neroli", ("neroli",)),
        ReferenceMarkerGroup(
            "violet_or_iris",
            (
                "iris",
                "orris",
                "irone",
                "ionone",
                "orivone",
                "irotyl",
            ),
        ),
        ReferenceMarkerGroup("geranium", ("geranium", "geraniol", "rhodinol")),
        ReferenceMarkerGroup("black_pepper", ("black pepper",)),
        ReferenceMarkerGroup(
            "amber",
            (
                "ambrox",
                "ambrofix",
                "amberwood",
                "cedramber",
                "benzoin",
                "labdanum",
            ),
        ),
        ReferenceMarkerGroup("cedar", ("cedar", "timberol", "iso e super")),
        ReferenceMarkerGroup("patchouli", ("patchouli", "clearwood")),
    ),
    source_url=(
        "https://www.prada-beauty.com/fragrance/lhomme-prada/"
        "lhomme-prada-eau-de-toilette/MPL01352.html"
    ),
    evidence_class="official_brand_note_architecture_only",
)


DIOR_HOMME_INTENSE_2011_05443A_ARCHITECTURE_V1 = ReferenceContract(
    contract_id="dior_homme_intense_2011_05443a_architecture_v1",
    display_name="Dior Homme Intense 2011 (05443/A)",
    target_aliases=(
        "dior homme intense",
        "dior homme intense 2011",
        "dhi 2011",
        "dhi-2011",
    ),
    allowed_scopes=(ARCHITECTURE,),
    marker_groups=(
        ReferenceMarkerGroup(
            "lavender_opening",
            ("lavender", "linalool", "linalyl acetate"),
            layer="head",
            prominence="supporting",
        ),
        ReferenceMarkerGroup(
            "iris_or_orris_heart",
            (
                "iris",
                "orris",
                "irone",
                "ionone",
                "orivone",
                "irotyl",
            ),
            layer="heart",
            prominence="primary",
        ),
        ReferenceMarkerGroup(
            "ambrette_musk_mediator",
            (
                "ambrette",
                "ambrettolide",
                "musk mallow",
            ),
            layer="heart_to_base",
            prominence="primary",
        ),
        ReferenceMarkerGroup(
            "pear_liqueur_facet",
            (
                "pear",
                "ethyl 2-methylbutyrate",
                "verdox",
                "hexyl acetate",
                "benzyl acetate",
                "osmanthus",
                "allyl cyclohexyl propionate",
            ),
            layer="heart",
            prominence="supporting",
        ),
        ReferenceMarkerGroup(
            "talc_textile_cushion",
            (
                "talc",
                "ethylene brassylate",
                "benzyl salicylate",
                "mimosa",
                "heliotropal",
                "piperonal",
            ),
            layer="heart_to_base",
            prominence="supporting",
        ),
        ReferenceMarkerGroup(
            "coumarinic_tonka_shadow",
            (
                "coumarin",
                "tonka",
                "tonkarome",
            ),
            layer="heart_to_base",
            prominence="supporting",
        ),
        ReferenceMarkerGroup(
            "vanillic_amber_shadow",
            (
                "vanilla",
                "vanillin",
                "isobutavan",
                "benzoin",
            ),
            layer="heart_to_base",
            prominence="supporting",
        ),
        ReferenceMarkerGroup(
            "virginia_cedar",
            ("cedarwood oil virginia", "virginia cedar", "juniperus virginiana"),
            layer="base",
            prominence="primary",
        ),
        ReferenceMarkerGroup(
            "vetiver",
            ("vetiver", "vetival", "vetikon"),
            layer="base",
            prominence="primary",
        ),
    ),
    source_url="https://www.dior.com/en_ch/beauty/products/dior-homme-intense-Y0479201.html",
    evidence_class=(
        "bounded_2011_architecture_official_house_plus_contemporaneous_launch_"
        "no_formula_ratios_or_sensory_equivalence"
    ),
)


YSL_LA_NUIT_DE_LHOMME_V1 = ReferenceContract(
    contract_id="ysl_la_nuit_de_lhomme_architecture",
    display_name="YSL La Nuit de L'Homme",
    target_aliases=("la nuit de l'homme", "la nuit", "ysl la nuit"),
    allowed_scopes=(ARCHITECTURE,),
    marker_groups=(
        ReferenceMarkerGroup("cardamom", ("cardamom",)),
        ReferenceMarkerGroup("bergamot", ("bergamot", "bergamot fcf", "bergamot fcf oil sicilian")),
        ReferenceMarkerGroup("lavender", ("lavender", "lavender eo", "lavender eo high altitude")),
        ReferenceMarkerGroup("cedar", ("cedarwood", "cedarwood virginia", "iso e super")),
        ReferenceMarkerGroup("coumarin", ("coumarin", "tonka", "tonkarome")),
        ReferenceMarkerGroup("vetiver", ("vetiver", "vetiver eo", "vetival", "vetikon")),
    ),
    source_url="https://www.ysl.com/la-nuit-de-lhomme",
    evidence_class="official_brand_note_architecture_only",
)


CHANEL_AHSEE_OFFICIAL_ARCHITECTURE_V1 = ReferenceContract(
    contract_id="chanel_allure_homme_sport_eau_extreme_edp_official_architecture_v1",
    display_name="Chanel Allure Homme Sport Eau Extreme EDP",
    # Do not capture the original EDT, Sport Cologne, or other Allure products.
    target_aliases=(
        "chanel allure homme sport eau extreme",
        "chanel allure homme sport eau extrême",
        "allure homme sport eau extreme",
        "allure homme sport eau extrême",
        "ahsee",
    ),
    allowed_scopes=(ARCHITECTURE,),
    # These are local functional name candidates, not Chanel ingredient aliases.
    # The official description gives no complete temporal hierarchy or amounts.
    marker_groups=(
        ReferenceMarkerGroup("mandarin", ("mandarin",)),
        ReferenceMarkerGroup("cypress", ("cypress",)),
        ReferenceMarkerGroup(
            "white_musk",
            (
                "white musk",
                "galaxolide",
                "romandolide",
                "ethylene brassylate",
                "habanolide",
                "zenolide",
                "exaltolide",
                "ambrettolide",
            ),
        ),
        ReferenceMarkerGroup("almond_tonka", ("tonka", "coumarin")),
    ),
    source_url=(
        "https://www.chanel.com/gb/fragrance/p/123560/"
        "allure-homme-sport-eau-extreme-eau-de-parfum-spray/"
    ),
    evidence_class="official_brand_four_facet_name_coverage_only_2026_09_08",
)


REFERENCE_CONTRACTS: dict[str, ReferenceContract] = {
    contract.contract_id: contract
    for contract in (
        YSL_LA_NUIT_DE_LHOMME_V1,
        MONTBLANC_EXPLORER_OFFICIAL_NOTES_V1,
        CREED_AVENTUS_OFFICIAL_NOTES_V1,
        CREED_AVENTUS_OFFICIAL_NOTES_V2,
        PRADA_LHOMME_OFFICIAL_NOTES_V1,
        DIOR_HOMME_INTENSE_2011_05443A_ARCHITECTURE_V1,
        CHANEL_AHSEE_OFFICIAL_ARCHITECTURE_V1,
    )
}


@dataclass(frozen=True, slots=True)
class ReferenceClaimDetection:
    status: str
    mode: str
    scope: str
    contract_ids: tuple[str, ...]
    explicit: bool
    detected_targets: tuple[str, ...]
    quantitative_requested: bool
    detail: str

    @property
    def requires_exact_ppm(self) -> bool:
        return self.mode == NAMED_REFERENCE and self.scope == QUANTITATIVE_SIMILARITY


def _metadata(body: str, label: str) -> str:
    match = re.search(
        rf"(?im)^\s*\*\*{re.escape(label)}:\*\*\s*(.+?)\s*$",
        body,
    )
    return match.group(1).strip().strip("`") if match else ""


def _split_ids(value: str) -> tuple[str, ...]:
    return tuple(
        token.strip().strip("`") for token in re.split(r"[,;]", value) if token.strip().strip("`")
    )


def _contract_for_alias(alias: str) -> ReferenceContract | None:
    normalized = normalize_name(alias).replace("_", " ")
    for contract in REFERENCE_CONTRACTS.values():
        if normalized == normalize_name(contract.contract_id).replace("_", " "):
            return contract
        if any(normalized == normalize_name(value) for value in contract.target_aliases):
            return contract
    return None


def _implicit_targets(text: str) -> tuple[str, ...]:
    low = normalize_name(text)
    claim_language = any(
        token in low
        for token in (
            " dna",
            "reference",
            "ratio",
            "similar",
            "silhouette",
            "territory",
            "dupe",
            "clone",
            "inspired",
            "reconstruction",
            "smell like",
            " form",
            " style",
        )
    )
    found: list[str] = []
    for contract in REFERENCE_CONTRACTS.values():
        matched = False
        for alias in contract.target_aliases:
            normalized_alias = normalize_name(alias)
            if normalized_alias == "explorer":
                matched = bool(re.search(r"\bexplorer\b", low)) and claim_language
            else:
                matched = bool(re.search(rf"\b{re.escape(normalized_alias)}\b", low))
            if matched:
                break
        if matched:
            found.append(contract.contract_id)
    return tuple(found)


def detect_reference_claim(formula: Mapping) -> ReferenceClaimDetection:
    body = str(formula.get("body", "") or "")
    text = f"{formula.get('name', '')}\n{body}"
    implicit = _implicit_targets(text)
    claim_mode_raw = _metadata(body, "Claim mode").lower().replace("-", "_")
    scope_raw = _metadata(body, "Reference scope").lower().replace("-", "_")
    contract_raw = _metadata(body, "Reference contract")
    legacy_claim = _metadata(body, "Reference claim").lower().replace("-", "_")
    explicit = bool(claim_mode_raw or scope_raw or contract_raw or legacy_claim)

    if legacy_claim:
        if legacy_claim in {"none", UNCLAIMED}:
            claim_mode_raw = UNCLAIMED
            scope_raw = ""
        else:
            claim_mode_raw = NAMED_REFERENCE
            scope_raw = {
                "architecture": ARCHITECTURE,
                "quantitative": QUANTITATIVE_SIMILARITY,
                "sensory": SENSORY_SIMILARITY,
            }.get(legacy_claim, legacy_claim)

    quantitative_language = bool(
        re.search(r"(?i)\b(?:ratio|ratios|quantitative|gc[- ]?ms)\b", text)
    )
    sensory_language = bool(
        re.search(r"(?i)\b(?:smells? like|sensory likeness|dupe|clone)\b", text)
    )
    claim_language = bool(
        re.search(
            r"(?i)\b(?:dna|ratios?|similar|silhouette|territory|dupe|clone|inspired|reconstruction|smells? like|style)\b",
            text,
        )
    )

    if not explicit:
        if implicit:
            inferred_scope = (
                QUANTITATIVE_SIMILARITY
                if quantitative_language
                else SENSORY_SIMILARITY
                if sensory_language
                else ARCHITECTURE
            )
            return ReferenceClaimDetection(
                status="FAIL",
                mode=NAMED_REFERENCE,
                scope=inferred_scope,
                contract_ids=(),
                explicit=False,
                detected_targets=implicit,
                quantitative_requested=quantitative_language,
                detail=(
                    "Named-reference language was detected without explicit Claim mode, "
                    "Reference contract, and Reference scope metadata."
                ),
            )
        return ReferenceClaimDetection(
            status="PASS",
            mode=UNCLAIMED,
            scope="",
            contract_ids=(),
            explicit=False,
            detected_targets=(),
            quantitative_requested=False,
            detail="No named-reference claim detected.",
        )

    if claim_mode_raw in {"none", UNCLAIMED}:
        if implicit and claim_language:
            return ReferenceClaimDetection(
                status="FAIL",
                mode=UNCLAIMED,
                scope="",
                contract_ids=(),
                explicit=True,
                detected_targets=implicit,
                quantitative_requested=quantitative_language,
                detail=(
                    "Claim mode is unclaimed, but the formula prose still makes a named-reference claim."
                ),
            )
        return ReferenceClaimDetection(
            status="PASS",
            mode=UNCLAIMED,
            scope="",
            contract_ids=(),
            explicit=True,
            detected_targets=implicit,
            quantitative_requested=False,
            detail="Reference comparison explicitly disclaimed.",
        )
    if claim_mode_raw != NAMED_REFERENCE:
        return ReferenceClaimDetection(
            "FAIL",
            claim_mode_raw or "missing",
            scope_raw,
            (),
            True,
            implicit,
            quantitative_language,
            "Claim mode must be 'unclaimed' or 'named_reference'.",
        )

    resolved_ids: list[str] = []
    unknown_ids: list[str] = []
    for token in _split_ids(contract_raw):
        contract = REFERENCE_CONTRACTS.get(token) or _contract_for_alias(token)
        if contract is None:
            unknown_ids.append(token)
        elif contract.contract_id not in resolved_ids:
            resolved_ids.append(contract.contract_id)
    if unknown_ids or not resolved_ids:
        reason = (
            "Unknown reference contract(s): " + ", ".join(unknown_ids)
            if unknown_ids
            else "Named-reference mode requires at least one Reference contract."
        )
        return ReferenceClaimDetection(
            "FAIL",
            NAMED_REFERENCE,
            scope_raw,
            tuple(resolved_ids),
            True,
            implicit,
            quantitative_language,
            reason,
        )
    if scope_raw not in {ARCHITECTURE, QUANTITATIVE_SIMILARITY, SENSORY_SIMILARITY}:
        return ReferenceClaimDetection(
            "FAIL",
            NAMED_REFERENCE,
            scope_raw or "missing",
            tuple(resolved_ids),
            True,
            implicit,
            quantitative_language,
            "Reference scope must be architecture, quantitative_similarity, or sensory_similarity.",
        )
    if quantitative_language and scope_raw != QUANTITATIVE_SIMILARITY:
        return ReferenceClaimDetection(
            "FAIL",
            NAMED_REFERENCE,
            scope_raw,
            tuple(resolved_ids),
            True,
            implicit,
            True,
            "Formula prose makes a quantitative/ratio claim but the declared scope is not quantitative_similarity.",
        )
    uncovered = sorted(set(implicit).difference(resolved_ids))
    if uncovered:
        return ReferenceClaimDetection(
            "FAIL",
            NAMED_REFERENCE,
            scope_raw,
            tuple(resolved_ids),
            True,
            implicit,
            quantitative_language,
            "Reference prose names targets not covered by the declared contracts: "
            + ", ".join(uncovered),
        )
    return ReferenceClaimDetection(
        "PASS",
        NAMED_REFERENCE,
        scope_raw,
        tuple(resolved_ids),
        True,
        implicit,
        quantitative_language,
        "Named-reference declaration is structurally valid.",
    )


def _ahsee_coverage_metadata(material_names: set[str]) -> dict[str, object]:
    """Keep four-facet name coverage separate from source identity and performance."""
    spearmint_names = sorted(
        material
        for material in material_names
        if "spearmint" in material or "mentha viridis" in material
    )
    peppermint_names = sorted(
        material
        for material in material_names
        if "peppermint" in material or "mentha piperita" in material
    )
    return {
        "coverage_basis": "NAME_FACET_COVERAGE_ONLY",
        "material_mapping_basis": "LOCAL_FUNCTIONAL_NAME_CANDIDATES_NOT_CHANEL_COMPOSITION",
        "relational_performance": "NOT_TESTED",
        "sensory_performance": "NOT_TESTED",
        "authority": {
            "source_ingredient_identity": False,
            "source_formula_proportions": False,
            "dose": False,
            "quantitative_similarity": False,
            "sensory_similarity": False,
            "relational_performance": False,
            "physical_compounding": False,
            "safety": False,
        },
        "ingredient_declarations": [
            {
                "inci_name": "MENTHA VIRIDIS LEAF OIL",
                "source_url": CHANEL_AHSEE_OFFICIAL_ARCHITECTURE_V1.source_url,
                "source_checked_on": "2026-09-08",
                "label_code": "PS000069A",
                "evidence_class": "OFFICIAL_INGREDIENT_DECLARATION_ONLY",
                "required_architecture_facet": False,
                "matched_materials": spearmint_names,
                "claim_ceiling": (
                    "Name presence does not verify botanical grade, source lot, "
                    "concentration, salience, or sensory equivalence."
                ),
            }
        ],
        "non_equivalent_mappings": (
            [
                {
                    "source_target": "MENTHA VIRIDIS LEAF OIL",
                    "build_materials": peppermint_names,
                    "status": "NON_EQUIVALENT_FUNCTIONAL_SUBSTITUTION_UNTESTED",
                    "identity_equivalent": False,
                    "sensory_equivalent": False,
                    "detail": (
                        "Peppermint / Mentha piperita is a separate build material; "
                        "it does not satisfy the source's spearmint identity."
                    ),
                }
            ]
            if peppermint_names
            else []
        ),
    }


def _evaluate_contract_groups(
    contract: ReferenceContract,
    material_names: set[str],
    scope: str,
) -> dict[str, object]:
    """Evaluate a single contract's marker groups against formula materials."""
    group_metadata = {
        group.name: {"layer": group.layer, "prominence": group.prominence}
        for group in contract.marker_groups
    }
    coverage_metadata = (
        _ahsee_coverage_metadata(material_names)
        if contract.contract_id == CHANEL_AHSEE_OFFICIAL_ARCHITECTURE_V1.contract_id
        else {}
    )
    if scope not in contract.allowed_scopes:
        return {
            "contract_id": contract.contract_id,
            "display_name": contract.display_name,
            "status": "FAIL",
            "source_url": contract.source_url,
            "evidence_class": contract.evidence_class,
            "scope_error": (
                f"Contract authorizes {', '.join(contract.allowed_scopes)} only; "
                f"cannot authorize {scope}"
            ),
            "matched_groups": {},
            "missing_groups": [g.name for g in contract.marker_groups],
            "all_group_names": [g.name for g in contract.marker_groups],
            "group_metadata": group_metadata,
            **coverage_metadata,
        }

    matched_groups: dict[str, list[str]] = {}
    missing_groups: list[str] = []
    for group in contract.marker_groups:
        matches = sorted(
            material
            for material in material_names
            if any(normalize_name(alternative) in material for alternative in group.alternatives)
        )
        if matches:
            matched_groups[group.name] = matches
        else:
            missing_groups.append(group.name)

    return {
        "contract_id": contract.contract_id,
        "display_name": contract.display_name,
        "status": "FAIL" if missing_groups else "PASS",
        "source_url": contract.source_url,
        "evidence_class": contract.evidence_class,
        "matched_groups": matched_groups,
        "missing_groups": missing_groups,
        "all_group_names": [g.name for g in contract.marker_groups],
        "group_metadata": group_metadata,
        **coverage_metadata,
    }


def _detect_over_add_materials(
    material_names: set[str],
    primary_contract: ReferenceContract,
    other_contracts: list[ReferenceContract],
) -> list[dict[str, object]]:
    """Find materials that match another contract's groups but not the primary's.

    Returns materials that are extraneous to the primary reference — they belong
    to a different perfume's DNA and would be wasted if targeting the primary.
    """
    primary_all = set()
    for group in primary_contract.marker_groups:
        primary_all.update(group.alternatives)

    over_adds: list[dict[str, object]] = []
    for other in other_contracts:
        other_groups: dict[str, list[str]] = {}
        for group in other.marker_groups:
            matches = sorted(
                m
                for m in material_names
                if any(normalize_name(alt) in m for alt in group.alternatives)
            )
            if matches:
                # Check if these materials also match the primary contract
                extraneous = [
                    m for m in matches if not any(normalize_name(p) in m for p in primary_all)
                ]
                if extraneous:
                    other_groups[group.name] = extraneous
        if other_groups:
            over_adds.append(
                {
                    "source_contract_id": other.contract_id,
                    "source_display_name": other.display_name,
                    "extraneous_groups": other_groups,
                }
            )
    return over_adds


def evaluate_reference_contract(formula: Mapping, state: FormulaState) -> dict[str, object]:
    detection = detect_reference_claim(formula)
    data: dict[str, object] = {
        "mode": detection.mode,
        "scope": detection.scope,
        "contract_ids": list(detection.contract_ids),
        "explicit": detection.explicit,
        "detected_targets": list(detection.detected_targets),
        "quantitative_requested": detection.quantitative_requested,
    }

    material_names = {
        normalize_name(material.canonical_name or material.name) for material in state.materials
    }

    # --- Implicit detection (no metadata): evaluate architecture anyway ---
    if detection.status == "FAIL" and detection.detected_targets:
        evaluations: list[dict[str, object]] = []
        failures: list[str] = []
        valid_targets = [tid for tid in detection.detected_targets if tid in REFERENCE_CONTRACTS]
        for contract_id in valid_targets:
            contract = REFERENCE_CONTRACTS[contract_id]
            ev = _evaluate_contract_groups(contract, material_names, ARCHITECTURE)
            evaluations.append(ev)
            if ev["missing_groups"]:
                failures.append(
                    f"{contract.display_name} architecture missing: "
                    f"{', '.join(cast(list[str], ev['missing_groups']))}"
                )

        # Over-add detection: materials matching Aventus but not Explorer etc.
        over_adds: list[dict[str, object]] = []
        if len(valid_targets) >= 2:
            for i, primary_id in enumerate(valid_targets):
                primary = REFERENCE_CONTRACTS[primary_id]
                others = [
                    REFERENCE_CONTRACTS[valid_targets[j]]
                    for j in range(len(valid_targets))
                    if j != i
                ]
                oa = _detect_over_add_materials(material_names, primary, others)
                if oa:
                    over_adds.append(
                        {
                            "primary_contract_id": primary_id,
                            "primary_display_name": primary.display_name,
                            "over_adds": oa,
                        }
                    )

        data["evaluations"] = evaluations
        if over_adds:
            data["over_add_analysis"] = over_adds
        data["metadata_warning"] = detection.detail

        detail = detection.detail
        if failures:
            detail += " | Deviations: " + "; ".join(failures)
        elif not valid_targets:
            detail = detection.detail

        return {
            "status": "FAIL",
            "detail": detail,
            "data": data,
        }

    if detection.status == "FAIL":
        return {"status": "FAIL", "detail": detection.detail, "data": data}
    if detection.mode == UNCLAIMED:
        return {"status": "PASS", "detail": detection.detail, "data": data}

    # --- Explicit metadata: full evaluation with declared scope ---
    evaluations = []
    failures = []
    for contract_id in detection.contract_ids:
        contract = REFERENCE_CONTRACTS[contract_id]
        ev = _evaluate_contract_groups(contract, material_names, detection.scope)
        evaluations.append(ev)
        if ev.get("scope_error"):
            failures.append(f"{contract.display_name}: {ev['scope_error']}")
        elif ev["missing_groups"]:
            failures.append(
                f"{contract.display_name} architecture missing: {', '.join(cast(list[str], ev['missing_groups']))}"
            )

    data["evaluations"] = evaluations
    if failures:
        return {"status": "FAIL", "detail": "; ".join(failures), "data": data}
    if any(item.get("coverage_basis") == "NAME_FACET_COVERAGE_ONLY" for item in evaluations):
        return {
            "status": "PASS",
            "detail": (
                "Declared reference marker checks passed; AHSEE is name/facet coverage only. "
                "Sensory and relational performance are untested; this grants no dose "
                "or proprietary formula likeness authority."
            ),
            "data": data,
        }
    return {
        "status": "PASS",
        "detail": "All declared architecture-only reference contracts are satisfied.",
        "data": data,
    }
