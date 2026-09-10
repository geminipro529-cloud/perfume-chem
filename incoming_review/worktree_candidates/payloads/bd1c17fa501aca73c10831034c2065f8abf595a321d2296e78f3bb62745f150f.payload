"""Family-specific questions and adapters for universal perfume-depth profiles.

Templates describe anatomy and falsification questions. They contain no
formula, material default, sensory conclusion, or family-wide beauty rule.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.perception.depth_contracts import (
    FORMULA_BOUND_REQUIRED_DIMENSIONS,
    DepthArchitectureProfileV1,
    DepthDimension,
    DepthDimensionContractV1,
    DepthEvidenceState,
    DepthFormulaEvidenceV1,
    DepthFormulaRoleV1,
    DepthMechanismKind,
    DepthMechanismV1,
    DepthProbeType,
    DepthProbeV1,
    PerfumeFamily,
)
from engine.perception.floral_depth import (
    FloralDesignRequestV1,
    FloralFacetClass,
    FloralTrainingTrialV1,
    TrainingDomain,
)


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name) for value in tuple(values))
    if not normalized:
        raise ValueError(f"{field_name} must contain at least one value")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return normalized


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class FamilyDepthTemplateV1:
    SCHEMA_VERSION: ClassVar[str] = "family_depth_template_v1"

    family: PerfumeFamily
    identity_questions: tuple[str, ...]
    anatomy_axes: tuple[str, ...]
    relationship_mechanisms: tuple[str, ...]
    texture_vocabulary: tuple[str, ...]
    temporal_questions: tuple[str, ...]
    spatial_questions: tuple[str, ...]
    hedonic_questions: tuple[str, ...]
    collapse_risks: tuple[str, ...]
    required_dimensions: tuple[DepthDimension, ...]
    claim_boundary: str

    def __post_init__(self) -> None:
        if not isinstance(self.family, PerfumeFamily):
            raise TypeError("family must be a PerfumeFamily")
        for field_name in (
            "identity_questions",
            "anatomy_axes",
            "relationship_mechanisms",
            "texture_vocabulary",
            "temporal_questions",
            "spatial_questions",
            "hedonic_questions",
            "collapse_risks",
        ):
            object.__setattr__(
                self,
                field_name,
                _text_tuple(getattr(self, field_name), field_name),
            )
        dimensions = tuple(self.required_dimensions)
        if not dimensions or len(dimensions) != len(set(dimensions)):
            raise ValueError("required_dimensions must be nonempty and unique")
        if any(not isinstance(item, DepthDimension) for item in dimensions):
            raise TypeError("required_dimensions must contain DepthDimension values")
        object.__setattr__(self, "required_dimensions", dimensions)
        object.__setattr__(self, "claim_boundary", _text(self.claim_boundary, "claim_boundary"))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **{item.name: _json_value(getattr(self, item.name)) for item in fields(self)},
        }

    @property
    def template_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.as_dict()))


_CORE_DIMENSIONS = (
    DepthDimension.OBJECT_IDENTITY,
    DepthDimension.INTERNAL_ANATOMY,
    DepthDimension.RELATIONAL_TOPOLOGY,
    DepthDimension.CONTRAST_NEGATIVE_SPACE,
    DepthDimension.TEXTURE_MATERIALITY,
    DepthDimension.TEMPORAL_ARCHITECTURE,
    DepthDimension.SPATIAL_PERFORMANCE,
    DepthDimension.HEDONIC_ARCHITECTURE,
    DepthDimension.NONLINEAR_INTERACTION,
    DepthDimension.PHYSICAL_CHEMISTRY,
    DepthDimension.COGNITIVE_CONTEXT,
    DepthDimension.ROBUSTNESS_ANTI_COLLAPSE,
    DepthDimension.EVIDENCE_QUALITY,
)
_BOUNDARY = (
    "This template generates target questions and controlled tests only; it cannot establish "
    "sensory depth, liking, realism, similarity, performance, safety, stability, or release."
)


def _template(
    family: PerfumeFamily,
    *,
    identity: tuple[str, ...],
    anatomy: tuple[str, ...],
    relations: tuple[str, ...],
    textures: tuple[str, ...],
    temporal: tuple[str, ...],
    spatial: tuple[str, ...],
    hedonic: tuple[str, ...],
    collapse: tuple[str, ...],
) -> FamilyDepthTemplateV1:
    return FamilyDepthTemplateV1(
        family=family,
        identity_questions=identity,
        anatomy_axes=anatomy,
        relationship_mechanisms=relations,
        texture_vocabulary=textures,
        temporal_questions=temporal,
        spatial_questions=spatial,
        hedonic_questions=hedonic,
        collapse_risks=collapse,
        required_dimensions=_CORE_DIMENSIONS,
        claim_boundary=_BOUNDARY,
    )


_TEMPLATES = (
    _template(
        PerfumeFamily.FLORAL,
        identity=(
            "Which named flower or bouquet remains invariant across opening, heart, and drydown?",
            "Is realism botanical, emotional, stylized, or deliberately abstract, and what drift is forbidden?",
        ),
        anatomy=(
            "petal surface and edge",
            "living flesh and internal moisture",
            "pollen, nectar, wax, stem, leaf, and flower-specific shadow",
        ),
        relations=(
            "shared recognizers bind anatomy without erasing individual flower hierarchy",
            "petal-to-flesh, flower-to-air, and flower-to-base handoffs preserve the named organism",
        ),
        textures=("satin petal", "waxy flesh", "powdered pollen", "humid stem", "translucent air"),
        temporal=(
            "Does the flower remain named after volatile recognizers recede?",
            "Which anatomy emerges, recurs, or transforms rather than merely fading?",
        ),
        spatial=(
            "Where are petal halo, fleshy center, green relief, and rear enclosure located?",
            "Does diffusion preserve flower identity or export only a generic floral cloud?",
        ),
        hedonic=(
            "Does shadow intensify petal and flesh pleasure without dirt or medicinal drift?",
            "Does the complete anatomy increase re-smelling while retaining the named flower?",
        ),
        collapse=(
            "generic white-floral mass replaces named anatomy",
            "sweetness, wood, salicylate, or musk becomes the only apparent depth source",
        ),
    ),
    _template(
        PerfumeFamily.WOODY,
        identity=(
            "Is the named object living tree, cut timber, polished object, root, forest, or abstract wood space?",
            "Which grain, temperature, moisture, and species-like cues must remain invariant?",
        ),
        anatomy=("grain and fibre", "sapwood and heartwood", "bark, root, resin seam, polish, moisture, and char"),
        relations=(
            "grain-to-body contrast creates a surface and interior rather than one woody block",
            "root, mineral, resin, smoke, and air interfaces determine enclosure and recurrence",
        ),
        textures=("dry grain", "creamy cut", "splintered fibre", "oiled polish", "mineral root"),
        temporal=(
            "Does the wood change from cut surface to warm body to persistent grain?",
            "Which woody facet recurs after top and heart materials adapt?",
        ),
        spatial=(
            "Does wood form floor, wall, column, halo, or central object?",
            "Can rear persistence support the subject without becoming a woody-amber wall?",
        ),
        hedonic=(
            "Which contrast between dry grain and yielding body supplies tactile pleasure?",
            "Does polish, warmth, or mineral coolness increase re-smelling without flattening species identity?",
        ),
        collapse=("generic woody-amber wall", "sandalwood cream erases grain, root, and air"),
    ),
    _template(
        PerfumeFamily.AMBER_RESINOUS,
        identity=(
            "Is the target glowing resin, balsamic skin, mineral amber, incense amber, or abstract warmth?",
            "Which balance of radiance, balsam, dryness, and darkness defines the named amber?",
        ),
        anatomy=("resin body", "balsamic sweetness", "incense lift, leather edge, mineral glow, vanilla warmth, and char"),
        relations=(
            "dry resin and soft balsam interlock without becoming syrup",
            "smoke, spice, leather, wood, and skin cues articulate the amber body",
        ),
        textures=("molten resin", "powdered balsam", "lacquered glow", "smoky veil", "mineral heat"),
        temporal=(
            "Does brightness open space before the balsamic body closes it?",
            "Does the drydown reveal resin strata or only persistent sweetness?",
        ),
        spatial=(
            "Is heat concentrated at the core or radiated as a translucent field?",
            "Does persistent amber preserve internal relief at distance?",
        ),
        hedonic=(
            "Does warmth feel enveloping rather than suffocating?",
            "Do dryness, smoke, or bitterness prevent sweetness fatigue while retaining comfort?",
        ),
        collapse=("monolithic sweet amber block", "generic amberwood projection replaces resin anatomy"),
    ),
    _template(
        PerfumeFamily.LEATHER_SUEDE,
        identity=(
            "Is the target raw hide, polished leather, suede, glove, saddle, smoke-dark hide, or abstract skin?",
            "Which degree of animality, tannin, polish, and cleanliness defines the object?",
        ),
        anatomy=("grain surface", "suede nap", "oil, tannin, smoke, animal warmth, polish, stitching air, and worn skin"),
        relations=(
            "tannic edge and fatty body create hide rather than smoke alone",
            "floral, fruit, wood, musk, and smoke interfaces determine polish and wear",
        ),
        textures=("supple hide", "dry grain", "powdered suede", "oiled saddle", "smoked seam"),
        temporal=(
            "Does the opening expose polish before the hide warms and softens?",
            "Does animalic shadow emerge proportionally or become tar and phenol?",
        ),
        spatial=(
            "Is leather a central object, lining, glove-like skin layer, or enclosing room?",
            "Does trail carry recognizable hide texture rather than smoke alone?",
        ),
        hedonic=(
            "Does controlled dirt make clean grain more tactile and desirable?",
            "Does the surface invite re-smelling without medicinal, fecal, or burnt-rubber drift?",
        ),
        collapse=("smoke or quinoline caricature replaces hide", "clean musk turns suede into cosmetic powder"),
    ),
    _template(
        PerfumeFamily.CHYPRE,
        identity=(
            "Which citrus-floral-mossy tension defines this chypre rather than a generic woody floral?",
            "Is the target classical, fruity, leathered, green, modern-clean, or mineral chypre?",
        ),
        anatomy=("citrus rind entry", "floral or fruit heart", "mossy floor, patchouli soil, labdanum shadow, wood, and bitter-green hinge"),
        relations=(
            "a bitter-green hinge transfers volatile brightness into the dark floor",
            "floral or fruit flesh must remain suspended between citrus lift and mossy gravity",
        ),
        textures=("dry moss", "damp earth", "polished rind", "velvet flower", "resinous shadow"),
        temporal=(
            "Does the opening's bitterness predict the later mossy floor?",
            "Does the heart remain present during base ascent rather than disappearing into patchouli?",
        ),
        spatial=(
            "Are bright canopy, suspended heart, and dark floor simultaneously legible?",
            "Does the base project a shaped shadow rather than a uniform dark cloud?",
        ),
        hedonic=(
            "Does bitterness sharpen pleasure and sophistication without austerity?",
            "Does the base supply gravity while preserving floral or fruity reward?",
        ),
        collapse=("patchouli-moss base consumes the heart", "citrus top and dark base remain detached"),
    ),
    _template(
        PerfumeFamily.FOUGERE,
        identity=(
            "Which aromatic-coumarinic-mossy relationship makes the perfume a fougere?",
            "Is the target barbershop, fern-like, marine, spicy, floral, leathery, or modern abstract?",
        ),
        anatomy=("aromatic canopy", "lavender-like floral body", "hay-coumarin warmth, mossy floor, herb stem, cool air, and wood"),
        relations=(
            "cool aromatic lift folds into warm hay and moss rather than forming separate halves",
            "herbal bitterness and soft coumarinic body regulate cleanliness and comfort",
        ),
        textures=("brisk herb", "soft shaving foam", "dry hay", "damp moss", "tonic air"),
        temporal=(
            "Does aromatic freshness transform into hay and moss while retaining family identity?",
            "Does coumarinic warmth arrive as a handoff rather than a sudden sweet base?",
        ),
        spatial=(
            "Does the aromatic canopy remain lifted above the soft body and mossy floor?",
            "Does diffusion communicate structure rather than generic masculine freshness?",
        ),
        hedonic=(
            "Does the cool-to-warm transition supply comfort and renewed attention?",
            "Does cleanliness remain tactile without shaving-product cliché?",
        ),
        collapse=("generic shower-gel freshness", "coumarin sweetness and moss become a flat retro base"),
    ),
    _template(
        PerfumeFamily.GOURMAND,
        identity=(
            "Which edible or memory object is referenced, and how literal should it remain?",
            "Which non-edible perfume cues prevent the target from becoming flavoring?",
        ),
        anatomy=("surface or crust", "crumb or flesh", "syrup, fat, roast, spice, acid, bitterness, steam, and residue"),
        relations=(
            "sweetness is shaped by roast, salt, acid, bitterness, dryness, or aromatic lift",
            "edible anatomy is bridged to skin, wood, flower, smoke, or air without identity loss",
        ),
        textures=("caramelized crust", "creamy center", "powdered sugar", "sticky syrup", "dry cocoa dust"),
        temporal=(
            "Does aroma evolve from volatile steam to body to roasted or woody residue?",
            "Does sweetness fatigue increase, decrease, or transform across wear?",
        ),
        spatial=(
            "Is the edible object close and tactile or radiating as an atmospheric memory?",
            "Does trail retain contrast or export only vanilla-like sweetness?",
        ),
        hedonic=(
            "Which balance of comfort, novelty, bitterness, salt-like contrast, and restraint sustains desire?",
            "Does literal recognizability increase pleasure or make the perfume trivial and fatiguing?",
        ),
        collapse=("undifferentiated sugar-vanilla syrup", "flavor realism replaces perfume architecture"),
    ),
    _template(
        PerfumeFamily.CITRUS_HESPERIDIC,
        identity=(
            "Which fruit, cultivar-like quality, or citrus abstraction must be recognizable?",
            "Is the central object rind, expressed oil, juice, blossom, leaf, pith, or an entire grove?",
        ),
        anatomy=("expressed peel oil", "zest", "pith bitterness, juice, pulp, acid, leaf, blossom, twig, and oxidation edge"),
        relations=(
            "rind bitterness and juicy body prevent a one-note terpene flash",
            "leaf, flower, wood, tea, herb, or musk carries citrus identity beyond the opening",
        ),
        textures=("sparkling oil", "wet pulp", "dry pith", "waxy peel", "cool leaf"),
        temporal=(
            "What remains recognizably citrus after rapid top-note adaptation?",
            "Does the later phase echo rind, blossom, leaf, tea, or wood rather than generic freshness?",
        ),
        spatial=(
            "Is brightness a flash, halo, mist, peel spray, or sustained canopy?",
            "Does diffusion preserve cultivar-like character or only limonene brightness?",
        ),
        hedonic=(
            "Does bitter pith sharpen juiciness and refresh attention?",
            "Does freshness remain pleasurable without detergent, cologne, or functional-product drift?",
        ),
        collapse=("terpene flash followed by unrelated base", "generic bergamot-cologne identity"),
    ),
    _template(
        PerfumeFamily.AROMATIC_HERBAL,
        identity=(
            "Which herb, plant assemblage, landscape, or aromatic abstraction is named?",
            "Are culinary, medicinal, camphoraceous, floral, or wild aspects desired or forbidden?",
        ),
        anatomy=("leaf surface", "crushed stem", "essential-oil burst, camphor, spice, flower, soil, sun, sap, and dry residue"),
        relations=(
            "fresh terpene lift is grounded by leaf body, stem bitterness, and soil or wood",
            "warm spice, cool camphor, flower, and herb are ordered rather than stacked",
        ),
        textures=("crushed leaf", "oily herb", "dry twig", "cool camphor", "sun-warmed dust"),
        temporal=(
            "Does the aromatic burst reveal plant body and landscape after adaptation?",
            "Which dried or woody residue recalls the living herb?",
        ),
        spatial=(
            "Does the perfume create a plant canopy, kitchen intimacy, medicinal chamber, or open landscape?",
            "Does projection preserve leaf identity rather than functional freshness?",
        ),
        hedonic=(
            "Does bitterness and camphor create tonic pleasure without medicinal rejection?",
            "Does familiarity comfort or make the composition ordinary?",
        ),
        collapse=("medicinal terpene mass", "culinary seasoning replaces perfume identity"),
    ),
    _template(
        PerfumeFamily.GREEN,
        identity=(
            "Is the target crushed leaf, sap, stem, forest canopy, garden, cut grass, or abstract green force?",
            "Which balance of bitterness, moisture, floral life, and soil defines the green object?",
        ),
        anatomy=("leaf blade", "cut stem", "sap, chlorophyll, galbanic bite, dew, soil, flower, seed, and dry fibre"),
        relations=(
            "bitter cut surface is relieved by sap, dew, flower, fruit, or soft wood",
            "volatile green shock hands off to persistent vegetal memory without shampoo drift",
        ),
        textures=("crisp blade", "watery sap", "fibrous stem", "damp leaf", "resinous green"),
        temporal=(
            "Does crushed-green impact become a living plant rather than vanish?",
            "Does drydown retain vegetal fibre, soil, seed, or leaf shadow?",
        ),
        spatial=(
            "Is green experienced as a blade, canopy, mist, stem cluster, or floor?",
            "Does humidity create relief or flatten the composition into aqueous shampoo?",
        ),
        hedonic=(
            "Does bitterness create appetite and realism without hostility?",
            "Does wet-dry contrast invite repeated smelling?",
        ),
        collapse=("shampoo-cucumber green", "aggressive galbanic bitterness erases living anatomy"),
    ),
    _template(
        PerfumeFamily.FRUITY,
        identity=(
            "Which fruit, ripeness stage, preparation, or imagined hybrid must be recognizable?",
            "Is the target fresh, bruised, fermented, candied, dried, lactonic, floral, or woody?",
        ),
        anatomy=("skin", "pulp", "juice, acid, seed or pit, lactonic flesh, aroma plume, bruising, fermentation, and leaf"),
        relations=(
            "acid, skin, seed, or green leaf gives contour to sweet pulp",
            "flower, wood, spice, musk, or fermentation shadow prevents candy abstraction",
        ),
        textures=("crisp skin", "juicy pulp", "velvety flesh", "waxy peel", "fermented haze"),
        temporal=(
            "Does fresh fruit become bruised, dried, floral, fermented, or woody coherently?",
            "Which recognizer survives after the volatile ester burst?",
        ),
        spatial=(
            "Is fruit a close object, suspended heart, sparkling top, or atmospheric orchard?",
            "Does trail carry fruit identity or only sweetness and musk?",
        ),
        hedonic=(
            "Does acid or seed bitterness increase juiciness and sophistication?",
            "Does ripeness remain pleasurable without candy, shampoo, or rotting drift?",
        ),
        collapse=("generic fruity candy", "lactonic pulp and sweetness erase skin, acid, and seed"),
    ),
    _template(
        PerfumeFamily.AQUATIC_OZONIC,
        identity=(
            "Is the target sea, rain, cold air, wet skin, pool, river, mist, or abstract water?",
            "Which salinity, mineral, vegetation, temperature, and cleanliness limits define it?",
        ),
        anatomy=("water body", "air boundary", "salinity, mineral, algae or plant life, humidity, foam, wet surface, and depth shadow"),
        relations=(
            "air-water contrast creates a boundary rather than one watery chemical field",
            "salt, mineral, green, floral, musk, and wood cues locate the water in a believable world",
        ),
        textures=("cold mist", "wet stone", "saline skin", "transparent water", "foamy air"),
        temporal=(
            "Does ozone or watery impact reveal water body and environment after adaptation?",
            "Does drydown preserve wetness memory without marine-functional residue?",
        ),
        spatial=(
            "Is water a surface, volume, mist, horizon, rain column, or skin film?",
            "Does diffusion create distance and air without emptiness?",
        ),
        hedonic=(
            "Does coolness refresh without becoming sterile or detergent-like?",
            "Do salt, mineral, skin, or vegetation provide rewarding specificity?",
        ),
        collapse=("generic marine-clean chemical cloud", "calone-like volume replaces water anatomy"),
    ),
    _template(
        PerfumeFamily.MINERAL_EARTH,
        identity=(
            "Is the target stone, metal, salt, soil, clay, dust, concrete, petrichor, or an imagined mineral?",
            "Which wet-dry, warm-cool, clean-dirty, and natural-industrial boundaries define it?",
        ),
        anatomy=("surface grain", "fracture or pore", "dust, salt, metal, wetness, earth, smoke, heat, lichen, and subterranean shadow"),
        relations=(
            "wet-dry and warm-cool contrasts create material volume",
            "wood, root, smoke, air, skin, and vegetation locate the mineral object",
        ),
        textures=("wet stone", "dry dust", "saline crystal", "metallic edge", "porous clay"),
        temporal=(
            "Does volatile wetness uncover dry mineral grain?",
            "Does the late phase retain stone or soil identity rather than generic amber dryness?",
        ),
        spatial=(
            "Is the mineral a held object, floor, wall, cave, dust field, or distant atmosphere?",
            "Does emptiness articulate scale or merely reduce intensity?",
        ),
        hedonic=(
            "Does tactile specificity create fascination despite low conventional sweetness?",
            "Does metallic, earthy, or smoky tension remain inviting rather than hostile?",
        ),
        collapse=("generic dry amber called mineral", "metallic harshness or petrichor effect replaces the object"),
    ),
    _template(
        PerfumeFamily.MUSK_SKIN,
        identity=(
            "Is the target clean skin, warm body, fabric, powder, animalic skin, breath, or abstract intimacy?",
            "Which cleanliness, warmth, fat, fruit, powder, and animality limits define it?",
        ),
        anatomy=("skin film", "warm body", "fatty softness, powder, fabric, breath, salt, fruit nuance, animal shadow, and halo"),
        relations=(
            "clean lift and bodily warmth create intimacy without laundry fog",
            "flower, wood, amber, fruit, salt, and animal trace determine character echo",
        ),
        textures=("warm skin", "soft fabric", "powdered veil", "fatty bloom", "salty breath"),
        temporal=(
            "Does the musk reveal differentiated skin facets as more volatile notes leave?",
            "Does persistence retain character or become an anonymous clean residue?",
        ),
        spatial=(
            "Is intimacy close, breathing, halo-like, diffusive, or fabric-trailing?",
            "How does specific anosmia alter apparent contour and comparison validity?",
        ),
        hedonic=(
            "Does skin warmth increase comfort and desire for proximity?",
            "Does animalic or salty trace make cleanliness more human without rejection?",
        ),
        collapse=("redundant laundry-musk fog", "anosmia is mistaken for structural absence or success"),
    ),
    _template(
        PerfumeFamily.INCENSE_SMOKE,
        identity=(
            "Is the target burning resin, cold incense, church air, temple wood, ash, char, or abstract smoke?",
            "Which sacred, domestic, industrial, medicinal, or destructive associations are desired?",
        ),
        anatomy=("resin source", "ember", "smoke plume, ash, char, cool air, wood, mineral chamber, spice, and lingering cloth"),
        relations=(
            "hot ember and cool air shape the plume in time and space",
            "resin, wood, mineral, floral, leather, spice, and ash define meaning and temperature",
        ),
        textures=("dry smoke", "oily resin", "powdered ash", "charred wood", "cool stone air"),
        temporal=(
            "Does smoke rise, disperse, settle, and leave coherent resin or ash memory?",
            "Does the source remain identifiable after the plume dominates?",
        ),
        spatial=(
            "Is smoke a line, veil, room, column, distant trace, or skin stain?",
            "Do source, plume, chamber, and residue occupy differentiated positions?",
        ),
        hedonic=(
            "Does ritual familiarity and warmth balance dryness, bitterness, and char?",
            "Does smoke create fascination without suffocation or burnt-rubber rejection?",
        ),
        collapse=("uniform smoky-amber cloud", "tar, phenol, or ash erases resin source and space"),
    ),
    _template(
        PerfumeFamily.TOBACCO_HAY,
        identity=(
            "Is the target green leaf, cured tobacco, pipe chamber, cigar box, hay field, smoke, or abstract brown warmth?",
            "Which sweetness, dryness, fermentation, leather, spice, and smoke boundaries define it?",
        ),
        anatomy=("leaf lamina", "vein and dry fibre", "cured sugar, hay, fermentation, tannin, smoke, ash, leather, spice, and wood box"),
        relations=(
            "dry leaf and fermented sweetness produce tobacco rather than vanilla smoke",
            "hay, leather, fruit, spice, wood, and ash articulate curing and use",
        ),
        textures=("dry leaf", "silky cured ribbon", "dusty hay", "oily smoke", "powdered ash"),
        temporal=(
            "Does green or aromatic leaf become cured, warmed, smoked, and ashy coherently?",
            "Does late sweetness preserve leaf fibre or become generic amber gourmand?",
        ),
        spatial=(
            "Is tobacco a held leaf, box, room, field, smoke plume, or clothing trace?",
            "Does trail preserve cured-leaf identity rather than sweetness alone?",
        ),
        hedonic=(
            "Does fermented sweetness make tannic dryness rewarding without edible drift?",
            "Do smoke and leather add intimacy and memory without stale-ash rejection?",
        ),
        collapse=("vanilla-amber sweetness called tobacco", "smoke and ash erase cured leaf anatomy"),
    ),
    _template(
        PerfumeFamily.ALDEHYDIC_ABSTRACT,
        identity=(
            "What abstract object, light condition, fabric, cosmetic body, or motion is named?",
            "Which degree of recognizability versus abstraction must survive beneath the flash?",
        ),
        anatomy=("high-energy flash", "air gap", "waxy or floral body, metallic edge, soap, powder, fabric, skin, and soft base"),
        relations=(
            "brilliant discontinuity reveals rather than disconnects the body beneath it",
            "wax, flower, powder, wood, musk, and metal define the abstract object's materiality",
        ),
        textures=("sparkling edge", "waxy body", "pressed powder", "starched fabric", "metallic air"),
        temporal=(
            "Does the initial flash resolve into a coherent body with remembered brilliance?",
            "Does abstraction gain intimacy and texture rather than simply lose intensity?",
        ),
        spatial=(
            "Does brilliance create height, distance, facets, or a surrounding aura?",
            "Does the body remain present beneath the volatile flash?",
        ),
        hedonic=(
            "Does the shock of brightness renew attention without harsh wax, soap, or metal?",
            "Does cosmetic familiarity support pleasure without dated cliché?",
        ),
        collapse=("harsh aldehydic flash over an unrelated base", "soap and powder erase the intended abstraction"),
    ),
    _template(
        PerfumeFamily.HYBRID_MULTIFAMILY,
        identity=(
            "Which family or named object leads, which support, and what hierarchy must never invert?",
            "Is the target fusion, juxtaposition, transformation, or sequential travel between families?",
        ),
        anatomy=("lead-family anatomy", "support-family anatomy", "shared recognizers, interface tissue, transition cues, negative space, and final integrated object"),
        relations=(
            "explicit interfaces explain why family modules belong together",
            "hierarchy, contrast, echo, and temporal handoff are tested separately from mere coexistence",
        ),
        textures=("interface texture", "lead surface", "support body", "transitional veil", "integrated residue"),
        temporal=(
            "Does hierarchy remain intentional as volatile families recede and persistent families rise?",
            "Is transformation legible without becoming unrelated perfumes in sequence?",
        ),
        spatial=(
            "Do family modules share one space, occupy distinct planes, or move through space intentionally?",
            "Does one diffusive chassis falsely homogenize the hybrid?",
        ),
        hedonic=(
            "Does cross-family tension create discovery while retaining coherence?",
            "Is novelty rewarding after repeated exposure or merely surprising once?",
        ),
        collapse=("generic chassis homogenizes every family", "lead hierarchy inverts or modules split into unrelated perfumes"),
    ),
)

_BY_FAMILY = {item.family: item for item in _TEMPLATES}
if tuple(_BY_FAMILY) != tuple(PerfumeFamily):  # pragma: no cover - import-time invariant
    raise RuntimeError("family depth templates do not cover the complete PerfumeFamily enum")


def all_family_depth_templates() -> tuple[FamilyDepthTemplateV1, ...]:
    return _TEMPLATES


def family_depth_template(family: PerfumeFamily) -> FamilyDepthTemplateV1:
    if not isinstance(family, PerfumeFamily):
        raise TypeError("family must be a PerfumeFamily")
    return _BY_FAMILY[family]


def _humanize(value: str) -> str:
    return " ".join(value.replace("_", " ").split())


def _probe_type(trial: FloralTrainingTrialV1) -> DepthProbeType:
    changed = trial.changed_factor.casefold()
    if "TRANSITION_LIKING" in trial.primary_endpoints:
        return DepthProbeType.TEMPORAL
    if trial.domain is TrainingDomain.BACKGROUND:
        return DepthProbeType.ABLATION
    if trial.domain is TrainingDomain.WOOD:
        return DepthProbeType.TEXTURE
    if trial.domain is TrainingDomain.MUSK:
        return DepthProbeType.SPATIAL
    if "ratio" in changed or "interaction" in changed:
        return DepthProbeType.RATIO_SWEEP
    if len(trial.controlled_arms) > 2:
        return DepthProbeType.RECOMBINATION
    return DepthProbeType.ABLATION


def _trial_probe(trial: FloralTrainingTrialV1) -> DepthProbeV1:
    return DepthProbeV1(
        probe_id=trial.trial_id,
        probe_type=_probe_type(trial),
        changed_factor=_humanize(trial.changed_factor),
        arms=tuple(_humanize(value) for value in trial.controlled_arms),
        constant_constraints=tuple(
            _humanize(value) for value in trial.constant_constraints
        ),
        primary_endpoints=tuple(_humanize(value) for value in trial.primary_endpoints),
        failure_endpoints=tuple(_humanize(value) for value in trial.failure_endpoints),
        time_windows=tuple(_humanize(value) for value in trial.time_windows),
        blinding_rule=trial.blinding_rule,
        order_rule=trial.order_rule,
        accept_rule=trial.accept_rule,
        reject_rule=trial.reject_rule,
        evidence_refs=trial.evidence_refs,
    )


_DIMENSION_TARGETS = {
    DepthDimension.CONSTRUCTION_COMPLEXITY: "formula rows remain a role ledger whose burden is explicit and never promoted into perceptual depth",
    DepthDimension.OBJECT_IDENTITY: "the named flower object remains invariant rather than becoming a generic floral family smell",
    DepthDimension.INTERNAL_ANATOMY: "flower-specific facets remain purposeful, connected, and falsifiable",
    DepthDimension.RELATIONAL_TOPOLOGY: "declared floral and support modules interact through explicit bridges and controlled interfaces",
    DepthDimension.CONTRAST_NEGATIVE_SPACE: "shadow and relief increase target articulation without dirt, harshness, or family drift",
    DepthDimension.TEXTURE_MATERIALITY: "flower and support textures remain differentiated and target-linked",
    DepthDimension.TEMPORAL_ARCHITECTURE: "recognizers transform and recur across declared windows while retaining the named flower",
    DepthDimension.SPATIAL_PERFORMANCE: "diffusion and enclosure hypotheses preserve flower identity and remain physically unclaimed",
    DepthDimension.HEDONIC_ARCHITECTURE: "liking remains separate from desire to re-smell, comfort, fascination, fatigue, and target fidelity",
    DepthDimension.NONLINEAR_INTERACTION: "coupling, suppression, masking, and emergence are tested as mixture effects rather than inferred from isolated materials",
    DepthDimension.PHYSICAL_CHEMISTRY: "ppm, OAV, stock rebase, volatility, and temporal diagnostics constrain design without becoming sensory truth",
    DepthDimension.COGNITIVE_CONTEXT: "labels, familiarity, and reference identity are isolated from target recognition and liking",
    DepthDimension.ROBUSTNESS_ANTI_COLLAPSE: "omission and perturbation controls distinguish architecture from padding and genericization",
    DepthDimension.EVIDENCE_QUALITY: "blinded repeats, ties, assessor heterogeneity, order, carryover, and immutable formula identity govern admission",
}


def adapt_floral_design_request(
    request: FloralDesignRequestV1,
    *,
    profile_id: str,
    evidence_refs: tuple[str, ...],
) -> DepthArchitectureProfileV1:
    """Project explicit floral contracts into the universal comparison language."""

    if not isinstance(request, FloralDesignRequestV1):
        raise TypeError("request must be a FloralDesignRequestV1")
    if not request.training_trials:
        raise ValueError("floral adaptation requires at least one controlled training trial")

    probes = tuple(_trial_probe(trial) for trial in request.training_trials)
    probe_ids = {probe.probe_id for probe in probes}
    default_probe_id = probes[0].probe_id
    subjects = tuple(subject.subject_id for subject in request.identity.floral_subjects)
    mechanisms: list[DepthMechanismV1] = []

    mechanisms.append(
        DepthMechanismV1(
            mechanism_id="floral_object_identity_anchor",
            dimension=DepthDimension.OBJECT_IDENTITY,
            kind=DepthMechanismKind.ANCHOR,
            target_link=request.identity.target_identity,
            causal_hypothesis=(
                "the declared flower subjects and recognizers form one named object whose "
                "identity survives controlled omission and time"
            ),
            participant_ids=subjects,
            expected_contribution="named floral identity retained across the declared contour",
            failure_mode="generic floral family odor or hierarchy inversion",
            falsification_probe_id=default_probe_id,
            temporal_windows=tuple(
                window.window_id for window in request.temporal_contour.windows
            ),
            evidence_state=DepthEvidenceState.EXPERIMENT_DESIGN,
            evidence_refs=request.identity.evidence_refs,
        )
    )

    for facet in request.facets:
        probe_id = (
            facet.controlled_comparison_ref
            if facet.controlled_comparison_ref in probe_ids
            else default_probe_id
        )
        participants = facet.current_build_bindings or facet.ideal_materials or (
            facet.subject_owner,
        )
        mechanisms.append(
            DepthMechanismV1(
                mechanism_id=f"floral_facet_{facet.facet_id}",
                dimension=(
                    DepthDimension.CONTRAST_NEGATIVE_SPACE
                    if facet.facet_class is FloralFacetClass.SHADOW
                    else DepthDimension.SPATIAL_PERFORMANCE
                    if facet.facet_class is FloralFacetClass.DIFFUSION
                    else DepthDimension.INTERNAL_ANATOMY
                ),
                kind=(
                    DepthMechanismKind.CONTRAST
                    if facet.facet_class is FloralFacetClass.SHADOW
                    else DepthMechanismKind.DIFFUSION_CARRIER
                    if facet.facet_class is FloralFacetClass.DIFFUSION
                    else DepthMechanismKind.FACET
                ),
                target_link=facet.target_function,
                causal_hypothesis=facet.omission_loss,
                participant_ids=participants,
                expected_contribution=facet.target_function,
                failure_mode=facet.failure_mode,
                falsification_probe_id=probe_id,
                temporal_windows=facet.required_temporal_windows,
                evidence_state=DepthEvidenceState.EXPERIMENT_DESIGN,
                evidence_refs=facet.evidence_refs,
            )
        )

    if request.coupling is not None:
        coupling_probe = next(
            (
                trial.trial_id
                for trial in request.training_trials
                if trial.controlled_arms == request.coupling.controlled_arms
            ),
            default_probe_id,
        )
        mechanisms.append(
            DepthMechanismV1(
                mechanism_id=f"floral_coupling_{request.coupling.coupling_id}",
                dimension=DepthDimension.RELATIONAL_TOPOLOGY,
                kind=DepthMechanismKind.BRIDGE,
                target_link=request.coupling.bridge,
                causal_hypothesis="; ".join(request.coupling.relationship_edges),
                participant_ids=request.coupling.facet_ids,
                expected_contribution="; ".join(request.coupling.identity_retention_endpoints),
                failure_mode="; ".join(request.coupling.collision_risks),
                falsification_probe_id=coupling_probe,
                temporal_windows=tuple(
                    window.window_id for window in request.temporal_contour.windows
                ),
                evidence_state=DepthEvidenceState.EXPERIMENT_DESIGN,
                evidence_refs=request.identity.evidence_refs,
            )
        )

    for wood in request.wood_texture_contracts:
        wood_probe = next(
            (
                trial.trial_id
                for trial in request.training_trials
                if trial.controlled_arms == wood.controlled_arms
            ),
            default_probe_id,
        )
        mechanisms.append(
            DepthMechanismV1(
                mechanism_id=f"floral_wood_texture_{wood.contract_id}",
                dimension=DepthDimension.TEXTURE_MATERIALITY,
                kind=DepthMechanismKind.TEXTURE_MODULATION,
                target_link=wood.floral_echo,
                causal_hypothesis=wood.texture_axis,
                participant_ids=wood.material_ids,
                expected_contribution=wood.omission_loss,
                failure_mode=wood.failure_mode,
                falsification_probe_id=wood_probe,
                temporal_windows=tuple(
                    window.window_id for window in request.temporal_contour.windows
                ),
                evidence_state=DepthEvidenceState.EXPERIMENT_DESIGN,
                evidence_refs=request.identity.evidence_refs,
            )
        )

    for background in request.background_contracts:
        resistance_probe = (
            background.controlled_trial_id
            if background.controlled_trial_id in probe_ids
            else default_probe_id
        )
        recession_probe = (
            background.preferred_recession_trial_id
            if background.preferred_recession_trial_id in probe_ids
            else default_probe_id
        )
        mechanisms.append(
            DepthMechanismV1(
                mechanism_id=f"floral_background_{background.background_id}",
                dimension=DepthDimension.RELATIONAL_TOPOLOGY,
                kind=DepthMechanismKind.PERSISTENCE_SUPPORT,
                target_link=background.flower_identity_link,
                causal_hypothesis=background.resistance_mechanism,
                participant_ids=background.material_ids,
                expected_contribution=background.target_function,
                failure_mode=background.takeover_failure_mode,
                falsification_probe_id=resistance_probe,
                temporal_windows=tuple(item.value for item in background.temporal_bands),
                evidence_state=DepthEvidenceState.EXPERIMENT_DESIGN,
                evidence_refs=request.identity.evidence_refs,
            )
        )
        mechanisms.append(
            DepthMechanismV1(
                mechanism_id=f"floral_recession_{background.background_id}",
                dimension=DepthDimension.TEMPORAL_ARCHITECTURE,
                kind=DepthMechanismKind.TEMPORAL_HANDOFF,
                target_link=background.recession_target,
                causal_hypothesis=(
                    "the flower's faster surface yields to its slower target-linked field "
                    "without a generic drydown or carrier takeover"
                ),
                participant_ids=background.material_ids,
                expected_contribution=background.omission_loss,
                failure_mode=background.takeover_failure_mode,
                falsification_probe_id=recession_probe,
                temporal_windows=tuple(item.value for item in background.temporal_bands),
                evidence_state=DepthEvidenceState.EXPERIMENT_DESIGN,
                evidence_refs=request.identity.evidence_refs,
            )
        )

    if request.relational_grammar is not None:
        grammar = request.relational_grammar
        mechanisms.append(
            DepthMechanismV1(
                mechanism_id=f"floral_hedonic_grammar_{grammar.grammar_id}",
                dimension=DepthDimension.HEDONIC_ARCHITECTURE,
                kind=DepthMechanismKind.HEDONIC_TENSION_RELEASE,
                target_link=grammar.flower_totality,
                causal_hypothesis=(
                    f"{grammar.preferred_recession}; {grammar.anti_compensation_rule}"
                ),
                participant_ids=tuple(
                    dict.fromkeys(
                        (
                            *grammar.internal_contrast_facet_ids,
                            *grammar.connective_tissue_material_ids,
                            grammar.resistant_background_id,
                        )
                    )
                ),
                expected_contribution="; ".join(
                    gate.accept_condition for gate in grammar.endpoint_gates
                ),
                failure_mode="; ".join(
                    gate.reject_condition for gate in grammar.endpoint_gates
                ),
                falsification_probe_id=grammar.preferred_recession_trial_id,
                temporal_windows=tuple(
                    dict.fromkeys(
                        window
                        for gate in grammar.endpoint_gates
                        for window in gate.time_windows
                    )
                ),
                evidence_state=DepthEvidenceState.EXPERIMENT_DESIGN,
                evidence_refs=request.identity.evidence_refs,
            )
        )
    temporal_participants = tuple(
        dict.fromkeys(
            participant
            for mechanism in mechanisms
            for participant in mechanism.participant_ids
        )
    ) or subjects
    mechanisms.append(
        DepthMechanismV1(
            mechanism_id="floral_temporal_contour",
            dimension=DepthDimension.TEMPORAL_ARCHITECTURE,
            kind=DepthMechanismKind.METAMORPHOSIS,
            target_link="named flower recognizers remain continuous through declared state changes",
            causal_hypothesis="; ".join(
                window.state_hypothesis for window in request.temporal_contour.windows
            ),
            participant_ids=temporal_participants,
            expected_contribution="flower-specific transformation with recognizer retention",
            failure_mode="opening-only recognizer followed by unrelated generic base",
            falsification_probe_id=default_probe_id,
            temporal_windows=tuple(
                window.window_id for window in request.temporal_contour.windows
            ),
            evidence_state=DepthEvidenceState.EXPERIMENT_DESIGN,
            evidence_refs=request.identity.evidence_refs,
        )
    )
    mechanisms.append(
        DepthMechanismV1(
            mechanism_id="floral_anti_collapse",
            dimension=DepthDimension.ROBUSTNESS_ANTI_COLLAPSE,
            kind=DepthMechanismKind.ANTI_COLLAPSE,
            target_link="each retained floral function must survive an isolated causal comparison",
            causal_hypothesis="controlled omissions distinguish target-linked resolution from padding",
            participant_ids=temporal_participants,
            expected_contribution="repeatable identity and anatomy loss in the corresponding omission arm",
            failure_mode="no repeatable difference, genericization, or uncontrolled multi-factor change",
            falsification_probe_id=default_probe_id,
            temporal_windows=tuple(
                window.window_id for window in request.temporal_contour.windows
            ),
            evidence_state=DepthEvidenceState.EXPERIMENT_DESIGN,
            evidence_refs=request.identity.evidence_refs,
        )
    )

    mechanisms_by_dimension: dict[DepthDimension, list[DepthMechanismV1]] = {}
    for mechanism in mechanisms:
        mechanisms_by_dimension.setdefault(mechanism.dimension, []).append(mechanism)
    probes_by_id = {probe.probe_id: probe for probe in probes}
    dimension_contracts = tuple(
        DepthDimensionContractV1(
            dimension=dimension,
            target_definition=_DIMENSION_TARGETS[dimension],
            required=True,
            mechanism_ids=tuple(item.mechanism_id for item in dimension_mechanisms),
            observable_endpoints=tuple(
                dict.fromkeys(
                    endpoint
                    for item in dimension_mechanisms
                    for endpoint in probes_by_id[item.falsification_probe_id].primary_endpoints
                )
            ),
            failure_modes=tuple(
                dict.fromkeys(item.failure_mode for item in dimension_mechanisms)
            ),
            probe_ids=tuple(
                dict.fromkeys(item.falsification_probe_id for item in dimension_mechanisms)
            ),
            evidence_refs=tuple(
                dict.fromkeys(
                    reference
                    for item in dimension_mechanisms
                    for reference in item.evidence_refs
                )
            ),
        )
        for dimension, dimension_mechanisms in sorted(
            mechanisms_by_dimension.items(),
            key=lambda item: tuple(DepthDimension).index(item[0]),
        )
    )

    return DepthArchitectureProfileV1(
        profile_id=profile_id,
        target_identity=request.identity.target_identity,
        family=PerfumeFamily.FLORAL,
        emotional_tone=request.identity.emotional_tone,
        realism_or_abstraction_target=request.identity.realism_target,
        forbidden_drift=request.identity.forbidden_drift,
        ideal_formula_ref=request.identity.ideal_formula_ref,
        current_inventory_build_ref=request.identity.current_inventory_build_ref,
        dimension_contracts=dimension_contracts,
        mechanisms=tuple(mechanisms),
        probes=probes,
        construction_row_count=len(request.current_build_materials),
        source_refs=tuple(
            dict.fromkeys((*request.identity.evidence_refs, *tuple(evidence_refs)))
        ),
        claim_ceiling=request.identity.claim_ceiling,
    )


def _formula_number(value: str, field_name: str) -> float:
    cleaned = value.replace("**", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be numeric in the current-build table") from exc


def _pipeline_number(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"pipeline material {field_name} must be numeric")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0:
        raise ValueError(f"pipeline material {field_name} must be finite and nonnegative")
    return normalized


def _target_functions_from_formula_text(text: str) -> Mapping[str, str]:
    heading = re.search(
        r"(?m)^##\s+(?:\d+\.\s+)?TARGET\s*/\s*IDEAL FORMULA\s*$",
        text,
    )
    if heading is None:
        raise ValueError("TARGET / IDEAL FORMULA heading is missing from formula markdown")
    remainder = text[heading.end() :]
    next_heading = re.search(r"\n##\s+", remainder)
    section = remainder if next_heading is None else remainder[: next_heading.start()]
    functions: dict[str, str] = {}
    for line in section.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 5 or not cells[0].isdigit():
            continue
        role_id = cells[3]
        if re.fullmatch(r"R\d{2,}", role_id) is None:
            raise ValueError(
                f"target formula row {cells[0]} lacks an R01-style role ID"
            )
        target_function = cells[4].strip()
        if not target_function:
            raise ValueError(f"target formula role {role_id} lacks a target-linked function")
        if role_id in functions:
            raise ValueError(f"target formula role {role_id} is duplicated")
        functions[role_id] = target_function
    if not functions:
        raise ValueError("TARGET / IDEAL FORMULA contains no parser-visible role functions")
    return functions


def _parse_formula_roles(
    formula_path: Path,
    *,
    current_build_heading: str,
    pipeline_materials: Mapping[str, Mapping[str, object]] | None = None,
    total_raw_ul: float | None = None,
) -> tuple[DepthFormulaRoleV1, ...]:
    text = formula_path.read_text(encoding="utf-8")
    start = text.find(current_build_heading)
    if start < 0:
        raise ValueError("current-build heading is missing from formula markdown")
    remainder = text[start + len(current_build_heading) :]
    next_heading = re.search(r"\n##\s+", remainder)
    section = remainder if next_heading is None else remainder[: next_heading.start()]
    roles: list[DepthFormulaRoleV1] = []
    target_functions: Mapping[str, str] | None = None
    for line in section.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or not cells[0].isdigit():
            continue
        if len(cells) >= 7:
            role_match = re.fullmatch(r"(R\d{2,})\s+(.+)", cells[6])
            if role_match is None:
                raise ValueError(
                    f"formula row {cells[0]} lacks an R01-style target-linked function"
                )
            role_id = role_match.group(1)
            active_ul = _formula_number(cells[4], "active_ul")
            active_ppm = _formula_number(cells[5], "active_ppm")
            target_function = role_match.group(2)
        elif len(cells) >= 5:
            role_id = cells[4]
            if re.fullmatch(r"R\d{2,}", role_id) is None:
                raise ValueError(
                    f"formula row {cells[0]} lacks an R01-style current-build role ID"
                )
            if pipeline_materials is None or total_raw_ul is None:
                raise ValueError(
                    "five-column current-build rows require bound pipeline material evidence"
                )
            if total_raw_ul <= 0:
                raise ValueError("pipeline total_raw_ul must be positive")
            material_key = _normalized_material_name(cells[1])
            pipeline_material = pipeline_materials.get(material_key)
            if pipeline_material is None:
                raise ValueError(
                    f"pipeline material set does not contain current-build material {cells[1]}"
                )
            active_ul = _pipeline_number(pipeline_material.get("active_ul"), "active_ul")
            active_ppm = active_ul / total_raw_ul * 1_000_000.0
            if target_functions is None:
                target_functions = _target_functions_from_formula_text(text)
            target_function = target_functions.get(role_id, "")
            if not target_function:
                raise ValueError(
                    f"current-build role {role_id} has no TARGET / IDEAL function"
                )
        else:
            continue
        roles.append(
            DepthFormulaRoleV1(
                row_number=int(cells[0]),
                role_id=role_id,
                material_name=cells[1],
                raw_ul=_formula_number(cells[3], "raw_ul"),
                active_ul=active_ul,
                active_ppm=active_ppm,
                target_function=target_function,
            )
        )
    if not roles:
        raise ValueError("current-build table contains no parser-visible formula roles")
    return tuple(roles)


def _normalized_material_name(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("pipeline material name must be nonblank text")
    return " ".join(value.casefold().split())


def _formula_evidence_from_pipeline(
    *,
    formula_path: Path,
    current_build_heading: str,
    pipeline_payload: Mapping[str, object],
) -> DepthFormulaEvidenceV1:
    formulas = pipeline_payload.get("formulas")
    if not isinstance(formulas, list) or len(formulas) != 1:
        raise ValueError("pipeline payload must contain exactly one selected formula")
    formula = formulas[0]
    if not isinstance(formula, Mapping):
        raise ValueError("pipeline selected formula must be an object")
    state = formula.get("formula_state")
    if not isinstance(state, Mapping):
        raise ValueError("pipeline formula_state is missing")
    materials = state.get("materials")
    if not isinstance(materials, list) or not materials:
        raise ValueError("pipeline formula_state materials are missing")
    state_raw_total = state.get("total_raw_ul")
    state_active_total = state.get("total_active_ul")
    if not isinstance(state_raw_total, (int, float)) or isinstance(state_raw_total, bool):
        raise ValueError("pipeline total_raw_ul is missing")
    if not isinstance(state_active_total, (int, float)) or isinstance(state_active_total, bool):
        raise ValueError("pipeline total_active_ul is missing")
    pipeline_materials: dict[str, Mapping[str, object]] = {}
    for material in materials:
        if not isinstance(material, Mapping):
            raise ValueError("pipeline material entry must be an object")
        material_key = _normalized_material_name(material.get("name"))
        if material_key in pipeline_materials:
            raise ValueError("pipeline material names must be unique")
        pipeline_materials[material_key] = material
    roles = _parse_formula_roles(
        formula_path,
        current_build_heading=current_build_heading,
        pipeline_materials=pipeline_materials,
        total_raw_ul=float(state_raw_total),
    )
    pipeline_names = tuple(pipeline_materials)
    formula_names = tuple(_normalized_material_name(role.material_name) for role in roles)
    if len(pipeline_names) != len(materials) or set(pipeline_names) != set(formula_names):
        raise ValueError("pipeline material set does not match current-build formula rows")
    if len(pipeline_names) != len(formula_names):
        raise ValueError("pipeline material set does not match current-build formula rows")

    role_raw_total = sum(role.raw_ul for role in roles)
    role_active_total = sum(role.active_ul for role in roles)
    if abs(float(state_raw_total) - role_raw_total) > 1e-6:
        raise ValueError("pipeline total_raw_ul does not match current-build formula rows")
    if abs(float(state_active_total) - role_active_total) > 1e-6:
        raise ValueError("pipeline total_active_ul does not match current-build formula rows")

    time_series = formula.get("time_series")
    if not isinstance(time_series, list) or not time_series:
        raise ValueError("pipeline time_series is missing")
    temporal_windows: list[str] = []
    temporal_authorities: list[str] = []
    for window in time_series:
        if not isinstance(window, Mapping):
            raise ValueError("pipeline time_series entry must be an object")
        temporal_windows.append(_text(window.get("label"), "temporal label"))
        temporal_authorities.append(
            _text(
                window.get("temporal_authority", "UNKNOWN"),
                "temporal_authority",
            )
        )
    run_contract = pipeline_payload.get("run_evidence_contract")
    if not isinstance(run_contract, Mapping):
        raise ValueError("pipeline run_evidence_contract is missing")
    formula_definitions = run_contract.get("formula_definitions")
    if not isinstance(formula_definitions, list):
        raise ValueError("pipeline canonical formula_definitions are missing")
    formula_number = int(formula.get("number", 0))
    formula_name = _text(formula.get("name"), "formula name")
    canonical_definition_rows = tuple(
        row
        for row in formula_definitions
        if isinstance(row, Mapping)
        and int(row.get("number", -1)) == formula_number
        and _text(row.get("name"), "formula definition name") == formula_name
    )
    if len(canonical_definition_rows) != 1:
        raise ValueError(
            "pipeline canonical formula definition does not match the selected formula"
        )
    canonical_definition_sha256 = _text(
        canonical_definition_rows[0].get("sha256"),
        "formula definition sha256",
    )
    unknown_oav = tuple(
        _text(material.get("name"), "unknown OAV material")
        for material in materials
        if isinstance(material, Mapping) and material.get("oav") is None
    )
    return DepthFormulaEvidenceV1(
        formula_path=str(formula_path.resolve()),
        formula_file_sha256=hashlib.sha256(formula_path.read_bytes()).hexdigest(),
        formula_definition_sha256=canonical_definition_sha256,
        analysis_input_sha256=_text(
            run_contract.get("analysis_input_sha256"),
            "analysis_input_sha256",
        ),
        inventory_sha256=_text(
            run_contract.get("inventory_sha256"),
            "inventory_sha256",
        ),
        scientific_inputs_sha256=_text(
            run_contract.get("scientific_inputs_sha256"),
            "scientific_inputs_sha256",
        ),
        pipeline_source_sha256=_text(
            run_contract.get("pipeline_source_sha256"),
            "pipeline_source_sha256",
        ),
        formula_name=formula_name,
        formula_number=formula_number,
        roles=roles,
        total_raw_ul=float(state_raw_total),
        total_active_ul=float(state_active_total),
        temporal_windows=tuple(temporal_windows),
        headspace_basis=_text(state.get("headspace_basis"), "headspace_basis"),
        temporal_authority="; ".join(dict.fromkeys(temporal_authorities)),
        pipeline_overall=_text(pipeline_payload.get("overall"), "pipeline overall"),
        release_evidence_overall=_text(
            pipeline_payload.get("release_evidence_overall"),
            "release_evidence_overall",
        ),
        unknown_oav_materials=unknown_oav,
    )


_FORMULA_GATE_KIND = {
    DepthDimension.CONSTRUCTION_COMPLEXITY: DepthMechanismKind.FACET,
    DepthDimension.OBJECT_IDENTITY: DepthMechanismKind.ANCHOR,
    DepthDimension.INTERNAL_ANATOMY: DepthMechanismKind.FACET,
    DepthDimension.RELATIONAL_TOPOLOGY: DepthMechanismKind.BRIDGE,
    DepthDimension.CONTRAST_NEGATIVE_SPACE: DepthMechanismKind.CONTRAST,
    DepthDimension.TEXTURE_MATERIALITY: DepthMechanismKind.TEXTURE_MODULATION,
    DepthDimension.TEMPORAL_ARCHITECTURE: DepthMechanismKind.METAMORPHOSIS,
    DepthDimension.SPATIAL_PERFORMANCE: DepthMechanismKind.DIFFUSION_CARRIER,
    DepthDimension.HEDONIC_ARCHITECTURE: DepthMechanismKind.HEDONIC_TENSION_RELEASE,
    DepthDimension.NONLINEAR_INTERACTION: DepthMechanismKind.CONFIGURAL_BLEND,
    DepthDimension.PHYSICAL_CHEMISTRY: DepthMechanismKind.PHYSICAL_CONSTRAINT,
    DepthDimension.COGNITIVE_CONTEXT: DepthMechanismKind.FAMILIARITY_CUE,
    DepthDimension.ROBUSTNESS_ANTI_COLLAPSE: DepthMechanismKind.ANTI_COLLAPSE,
    DepthDimension.EVIDENCE_QUALITY: DepthMechanismKind.ANTI_COLLAPSE,
}

_FORMULA_GATE_PROBE = {
    DepthDimension.CONSTRUCTION_COMPLEXITY: DepthProbeType.ABLATION,
    DepthDimension.OBJECT_IDENTITY: DepthProbeType.ABLATION,
    DepthDimension.INTERNAL_ANATOMY: DepthProbeType.ABLATION,
    DepthDimension.RELATIONAL_TOPOLOGY: DepthProbeType.RECOMBINATION,
    DepthDimension.CONTRAST_NEGATIVE_SPACE: DepthProbeType.RATIO_SWEEP,
    DepthDimension.TEXTURE_MATERIALITY: DepthProbeType.TEXTURE,
    DepthDimension.TEMPORAL_ARCHITECTURE: DepthProbeType.TEMPORAL,
    DepthDimension.SPATIAL_PERFORMANCE: DepthProbeType.SPATIAL,
    DepthDimension.HEDONIC_ARCHITECTURE: DepthProbeType.HEDONIC_PREFERENCE,
    DepthDimension.NONLINEAR_INTERACTION: DepthProbeType.RECOMBINATION,
    DepthDimension.PHYSICAL_CHEMISTRY: DepthProbeType.PHYSICAL_DIAGNOSTIC,
    DepthDimension.COGNITIVE_CONTEXT: DepthProbeType.REFERENCE,
    DepthDimension.ROBUSTNESS_ANTI_COLLAPSE: DepthProbeType.ANTI_COLLAPSE,
    DepthDimension.EVIDENCE_QUALITY: DepthProbeType.REPEATABILITY,
}


def _formula_gate_arms(dimension: DepthDimension) -> tuple[str, ...]:
    if dimension is DepthDimension.TEMPORAL_ARCHITECTURE:
        return ("longitudinal coded application", "fresh coded application at each window")
    if dimension is DepthDimension.HEDONIC_ARCHITECTURE:
        return ("complete architecture", "constant-total reduced architecture")
    if dimension is DepthDimension.NONLINEAR_INTERACTION:
        return ("coupling low", "coupling target", "coupling high")
    if dimension is DepthDimension.PHYSICAL_CHEMISTRY:
        return ("as-dosed formula state", "stock-rebased active-equivalent audit")
    if dimension is DepthDimension.COGNITIVE_CONTEXT:
        return ("label-concealed coded candidate", "label revealed only after scoring")
    if dimension is DepthDimension.EVIDENCE_QUALITY:
        return ("session one", "session two", "session three")
    return ("complete architecture", f"carrier-matched {dimension.value.casefold()} ablation")


def _formula_gate_endpoints(dimension: DepthDimension) -> tuple[str, ...]:
    if dimension is DepthDimension.HEDONIC_ARCHITECTURE:
        return ("liking", "desire to re-smell", "comfort", "fatigue", "target identity")
    if dimension is DepthDimension.TEMPORAL_ARCHITECTURE:
        return ("target identity", "temporal transition", "recurrence", "adaptation divergence")
    if dimension is DepthDimension.PHYSICAL_CHEMISTRY:
        return ("ppm and OAV anomaly screen", "stock rebase integrity", "unknown OAV state")
    if dimension is DepthDimension.COGNITIVE_CONTEXT:
        return ("target identity", "familiarity", "label effect", "liking")
    if dimension is DepthDimension.EVIDENCE_QUALITY:
        return ("repeatability", "ties", "assessor heterogeneity", "order and carryover")
    return ("target identity", dimension.value.casefold().replace("_", " "))


def _formula_gate_probe_for(
    dimension: DepthDimension,
    *,
    evidence: DepthFormulaEvidenceV1,
    evidence_refs: tuple[str, ...],
) -> DepthProbeV1:
    constraints = (
        "constant total raw volume",
        "same application mass and carrier",
        f"exact formula definition hash {evidence.formula_definition_sha256}",
    )
    if dimension is DepthDimension.TEMPORAL_ARCHITECTURE:
        constraints = (
            *constraints,
            "fresh coded applications at each independent window control olfactory adaptation",
        )
    return DepthProbeV1(
        probe_id=f"formula_probe_{dimension.value.casefold()}",
        probe_type=_FORMULA_GATE_PROBE[dimension],
        changed_factor=f"formula-bound {dimension.value.casefold().replace('_', ' ')}",
        arms=_formula_gate_arms(dimension),
        constant_constraints=constraints,
        primary_endpoints=_formula_gate_endpoints(dimension),
        failure_endpoints=(
            "no repeatable target-linked difference",
            "target drift or genericization",
            "modeled diagnostics promoted into sensory truth",
        ),
        time_windows=evidence.temporal_windows,
        blinding_rule="opaque three-digit codes conceal formula and reference identity",
        order_rule="counterbalance order, record predecessor, permit ties, and repeat sessions",
        accept_rule="accept only a repeatable target-linked endpoint without forbidden drift",
        reject_rule="reject or hold for ties, discordance, target drift, or unsupported authority",
        evidence_refs=evidence_refs,
    )


def _reference_dimension_target(
    template: FamilyDepthTemplateV1,
    dimension: DepthDimension,
) -> str:
    if dimension is DepthDimension.CONSTRUCTION_COMPLEXITY:
        return (
            "reference construction burden is recorded without turning row count into "
            "depth, liking, luxury, or sensory authority"
        )
    values = {
        DepthDimension.OBJECT_IDENTITY: template.identity_questions,
        DepthDimension.INTERNAL_ANATOMY: template.anatomy_axes,
        DepthDimension.RELATIONAL_TOPOLOGY: template.relationship_mechanisms,
        DepthDimension.CONTRAST_NEGATIVE_SPACE: template.collapse_risks,
        DepthDimension.TEXTURE_MATERIALITY: template.texture_vocabulary,
        DepthDimension.TEMPORAL_ARCHITECTURE: template.temporal_questions,
        DepthDimension.SPATIAL_PERFORMANCE: template.spatial_questions,
        DepthDimension.HEDONIC_ARCHITECTURE: template.hedonic_questions,
        DepthDimension.NONLINEAR_INTERACTION: template.relationship_mechanisms,
        DepthDimension.PHYSICAL_CHEMISTRY: (
            "physical diagnostics constrain the declared reference without proving perception",
        ),
        DepthDimension.COGNITIVE_CONTEXT: (
            "reference labels and familiarity remain concealed until independent scoring is complete",
        ),
        DepthDimension.ROBUSTNESS_ANTI_COLLAPSE: template.collapse_risks,
        DepthDimension.EVIDENCE_QUALITY: (
            "blinding, repeats, ties, order, carryover, and assessor heterogeneity govern comparison",
        ),
    }[dimension]
    return "; ".join(values)


def _reference_probe_for(
    dimension: DepthDimension,
    *,
    temporal_windows: tuple[str, ...],
    evidence_refs: tuple[str, ...],
) -> DepthProbeV1:
    constraints = (
        "constant total raw volume",
        "same application mass and carrier",
        "bounded reference identity concealed until scoring is complete",
    )
    if dimension is DepthDimension.TEMPORAL_ARCHITECTURE:
        constraints = (
            *constraints,
            "fresh coded applications at each independent window control olfactory adaptation",
        )
    return DepthProbeV1(
        probe_id=f"reference_probe_{dimension.value.casefold()}",
        probe_type=_FORMULA_GATE_PROBE[dimension],
        changed_factor=f"bounded reference {dimension.value.casefold().replace('_', ' ')}",
        arms=_formula_gate_arms(dimension),
        constant_constraints=constraints,
        primary_endpoints=_formula_gate_endpoints(dimension),
        failure_endpoints=(
            "no repeatable target-linked difference",
            "reference-name bias or target incompatibility",
            "architecture overlap promoted into similarity or superiority",
        ),
        time_windows=temporal_windows,
        blinding_rule="opaque three-digit codes conceal candidate and reference identity",
        order_rule="counterbalance order, record predecessor, permit ties, and repeat sessions",
        accept_rule="retain only descriptive dimension evidence within the declared target",
        reject_rule="abstain from superiority, similarity, liking, or performance inference",
        evidence_refs=evidence_refs,
    )


def build_bounded_reference_depth_profile(
    *,
    profile_id: str,
    target_identity: str,
    family: PerfumeFamily,
    emotional_tone: str,
    realism_or_abstraction_target: str,
    forbidden_drift: tuple[str, ...],
    ideal_formula_ref: str,
    current_inventory_build_ref: str,
    construction_row_count: int,
    temporal_windows: tuple[str, ...],
    source_refs: tuple[str, ...],
    claim_ceiling: str,
) -> DepthArchitectureProfileV1:
    """Build a non-authoritative architecture control for non-scalar comparison."""

    template = family_depth_template(family)
    dimensions = (
        DepthDimension.CONSTRUCTION_COMPLEXITY,
        *template.required_dimensions,
    )
    probes = tuple(
        _reference_probe_for(
            dimension,
            temporal_windows=temporal_windows,
            evidence_refs=source_refs,
        )
        for dimension in dimensions
    )
    mechanisms = tuple(
        DepthMechanismV1(
            mechanism_id=f"reference_gate_{dimension.value.casefold()}",
            dimension=dimension,
            kind=_FORMULA_GATE_KIND[dimension],
            target_link=_reference_dimension_target(template, dimension),
            causal_hypothesis=(
                "the reference supplies a dimension-specific architecture question and "
                "controlled comparison, never a sensory answer key"
            ),
            participant_ids=("bounded reference architecture",),
            expected_contribution="; ".join(_formula_gate_endpoints(dimension)),
            failure_mode=(
                "the reference is used as a prestige label, formula template, sensory truth, "
                "or scalar superiority score"
            ),
            falsification_probe_id=f"reference_probe_{dimension.value.casefold()}",
            temporal_windows=temporal_windows,
            evidence_state=DepthEvidenceState.EXPERIMENT_DESIGN,
            evidence_refs=source_refs,
        )
        for dimension in dimensions
    )
    contracts = tuple(
        DepthDimensionContractV1(
            dimension=dimension,
            target_definition=_reference_dimension_target(template, dimension),
            required=dimension is not DepthDimension.CONSTRUCTION_COMPLEXITY,
            mechanism_ids=(f"reference_gate_{dimension.value.casefold()}",),
            observable_endpoints=_formula_gate_endpoints(dimension),
            failure_modes=(
                "reference architecture does not establish sensory similarity or superiority",
            ),
            probe_ids=(f"reference_probe_{dimension.value.casefold()}",),
            evidence_refs=source_refs,
        )
        for dimension in dimensions
    )
    return DepthArchitectureProfileV1(
        profile_id=profile_id,
        target_identity=target_identity,
        family=family,
        emotional_tone=emotional_tone,
        realism_or_abstraction_target=realism_or_abstraction_target,
        forbidden_drift=forbidden_drift,
        ideal_formula_ref=ideal_formula_ref,
        current_inventory_build_ref=current_inventory_build_ref,
        dimension_contracts=contracts,
        mechanisms=mechanisms,
        probes=probes,
        construction_row_count=construction_row_count,
        source_refs=source_refs,
        claim_ceiling=claim_ceiling,
    )


def adapt_floral_formula_depth_profile(
    request: FloralDesignRequestV1,
    *,
    profile_id: str,
    evidence_refs: tuple[str, ...],
    formula_path: str | Path,
    pipeline_payload: Mapping[str, object],
    current_build_heading: str,
) -> DepthArchitectureProfileV1:
    """Bind the universal floral profile to exact formula and pipeline ledgers."""

    path = Path(formula_path)
    if not path.is_file():
        raise ValueError("formula_path must identify an existing file")
    evidence = _formula_evidence_from_pipeline(
        formula_path=path,
        current_build_heading=current_build_heading,
        pipeline_payload=pipeline_payload,
    )
    base = adapt_floral_design_request(
        request,
        profile_id=profile_id,
        evidence_refs=evidence_refs,
    )
    bound_refs = tuple(
        dict.fromkeys(
            (
                *base.source_refs,
                *tuple(evidence_refs),
                f"formula-file-sha256:{evidence.formula_file_sha256}",
                f"formula-definition-sha256:{evidence.formula_definition_sha256}",
                f"pipeline-analysis-input-sha256:{evidence.analysis_input_sha256}",
            )
        )
    )
    dimensions = (
        DepthDimension.CONSTRUCTION_COMPLEXITY,
        *FORMULA_BOUND_REQUIRED_DIMENSIONS,
    )
    formula_probes = tuple(
        _formula_gate_probe_for(
            dimension,
            evidence=evidence,
            evidence_refs=bound_refs,
        )
        for dimension in dimensions
    )
    formula_mechanisms = tuple(
        DepthMechanismV1(
            mechanism_id=f"formula_gate_{dimension.value.casefold()}",
            dimension=dimension,
            kind=_FORMULA_GATE_KIND[dimension],
            target_link=_DIMENSION_TARGETS[dimension],
            causal_hypothesis=(
                "the exact parser-visible role ledger is interrogated through the bound "
                "controlled probe without using ingredient count as sensory evidence"
            ),
            participant_ids=evidence.role_ids,
            expected_contribution="; ".join(_formula_gate_endpoints(dimension)),
            failure_mode=(
                "the declared dimension has no repeatable target-linked effect or collapses "
                "into generic floral, generic wood, or unsupported modeled authority"
            ),
            falsification_probe_id=f"formula_probe_{dimension.value.casefold()}",
            temporal_windows=evidence.temporal_windows,
            evidence_state=DepthEvidenceState.EXPERIMENT_DESIGN,
            evidence_refs=bound_refs,
        )
        for dimension in dimensions
    )

    base_mechanisms = tuple(
        mechanism
        for mechanism in base.mechanisms
        if mechanism.dimension is not DepthDimension.TEMPORAL_ARCHITECTURE
    )
    existing_contracts = {
        contract.dimension: contract
        for contract in base.dimension_contracts
        if contract.dimension is not DepthDimension.TEMPORAL_ARCHITECTURE
    }
    formula_probe_by_dimension = {
        dimension: probe for dimension, probe in zip(dimensions, formula_probes, strict=True)
    }
    formula_mechanism_by_dimension = {
        dimension: mechanism
        for dimension, mechanism in zip(dimensions, formula_mechanisms, strict=True)
    }
    contracts: list[DepthDimensionContractV1] = []
    for dimension in dimensions:
        probe = formula_probe_by_dimension[dimension]
        mechanism = formula_mechanism_by_dimension[dimension]
        existing = existing_contracts.get(dimension)
        if existing is None:
            contracts.append(
                DepthDimensionContractV1(
                    dimension=dimension,
                    target_definition=_DIMENSION_TARGETS[dimension],
                    required=dimension is not DepthDimension.CONSTRUCTION_COMPLEXITY,
                    mechanism_ids=(mechanism.mechanism_id,),
                    observable_endpoints=probe.primary_endpoints,
                    failure_modes=(mechanism.failure_mode,),
                    probe_ids=(probe.probe_id,),
                    evidence_refs=bound_refs,
                )
            )
            continue
        contracts.append(
            replace(
                existing,
                required=True,
                mechanism_ids=tuple(
                    dict.fromkeys((*existing.mechanism_ids, mechanism.mechanism_id))
                ),
                observable_endpoints=tuple(
                    dict.fromkeys((*existing.observable_endpoints, *probe.primary_endpoints))
                ),
                failure_modes=tuple(
                    dict.fromkeys((*existing.failure_modes, mechanism.failure_mode))
                ),
                probe_ids=tuple(dict.fromkeys((*existing.probe_ids, probe.probe_id))),
                evidence_refs=tuple(
                    dict.fromkeys((*existing.evidence_refs, *bound_refs))
                ),
            )
        )
    contracts.sort(key=lambda item: tuple(DepthDimension).index(item.dimension))
    return replace(
        base,
        dimension_contracts=tuple(contracts),
        mechanisms=(*base_mechanisms, *formula_mechanisms),
        probes=(*base.probes, *formula_probes),
        construction_row_count=evidence.formula_row_count,
        source_refs=bound_refs,
        formula_evidence=evidence,
    )


__all__ = [
    "FamilyDepthTemplateV1",
    "adapt_floral_design_request",
    "adapt_floral_formula_depth_profile",
    "all_family_depth_templates",
    "build_bounded_reference_depth_profile",
    "family_depth_template",
]
