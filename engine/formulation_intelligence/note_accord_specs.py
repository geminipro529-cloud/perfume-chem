"""Cited note accords: a lead plus helpers, each helper with a job and a source.

A plain data table plus validation. The semantic brief adapter builds a named
covered note's accord from it.

Every node comes from ``construction_library_v1.json`` and quotes that node's own
"function" text. A lead or helper is admitted only when at least one of its
sources is a producer technical text or a paper (DOI or PMID). The kind is read
from the source's record in ``literature_v1.json`` (evidence class, DOI, URL),
never from the source id. Nodes whose only sources are marketed perfumes, and
materials Kenny does not own, are left out and listed in ``EXCLUDED``.

Every stock is bound to the stock the formula solver itself sees: exactly one
capability of ``material_capability_index.build_material_capability_index()``
with that identity name and stock fraction, design-ready and execution-ready
(a bottle Kenny can pipette). The index is built on first use, not at import.
A helper takes only its cited stocks, so the formula solver spares it the
support rules that read a stock off the prompt's words: the lead's odor match,
the family bucket of its own lead, and the refusal of a potent trace material
in a support place (the planner still holds its dose under the identity hard
cap and the IFRA cap).
At run time a spec that fails (a cited stock used up or no longer design-ready)
is left out, so its notes keep today's supports, and ``skipped_specs()`` says
why; the check over every spec at once is a test.

Every node is an untested design hypothesis (the library marks each one
SOURCE_DESCRIPTOR_TO_FUNCTION_HYPOTHESIS, with no numeric calibration). A job
is a design label for Kenny's nose to check, not a measured effect, and nothing
here says an accord smells deeper or better (docs/agents/failure-registry.md F12).
No source gives a dose: see ``SHARE_BASIS``.

This module never reads the benchmark duel file (data/benchmarks/opus_duel_v1.json)
or its reference cards.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from .construction_library import load_construction_library
from .source_review import source_record_hash

ROOT = Path(__file__).resolve().parents[2]
LITERATURE_PATH = ROOT / "data/formulation_knowledge/literature_v1.json"
SOURCE_REVIEWS_PATH = ROOT / "data/formulation_knowledge/source_reviews_v1.json"

# What each job means. "bridge" is not a job: role_reading.py already uses that
# word for something else, and no test stands behind it.
JOBS = MappingProxyType({
    "lift": "brings a lighter, more open facet over the lead",
    "round": "fills out the lead with a warmer, fuller body",
    "fix": "keeps the lead's character in the base (design intent; persistence is not measured)",
    "naturalise": "makes a single-material lead read as a fuller natural material",
    "shadow": "puts a darker, deeper facet under the lead",
    "contrast": "sets an opposite facet against the lead so the lead reads more clearly",
    "texture": "changes the lead's surface: powder, cream, dryness, transparency or mineral",
})

SHARE_BASIS = (
    "share_of_lead scales the lead role's design share into the helper role's share, "
    "as today's _ACCORD_SPLIT does for a note's same-query supports; the planner then "
    "turns shares into stock volumes as for every role, so a diluted stock gets more "
    "volume. The numbers are design defaults, not citations: no source gives a dose. "
    "They copy today's ratios (.23/.62 = .37 for the first helper, .15/.62 = .24 for "
    "the second), so wiring changes what a helper is and why, not how big its role "
    "is. Each helper's share stays below half the lead's and all helpers' together "
    "stay below the lead's. The planner holds each helper's active amount (stock "
    "volume x stock fraction) at or under its lead's (ACCORD_HELPER_ABOVE_LEAD), "
    "except beside a trace-level lead."
)
FIRST_HELPER_SHARE, SECOND_HELPER_SHARE = .37, .24

# Ingredient producers whose own pages are technical texts. Matched against the
# host of the source record's URL.
_PRODUCER_HOSTS = (
    "iff.com", "givaudan.com", "dsm-firmenich.com", "firmenich.com", "biolandes.com",
    "bontoux.com", "symrise.com", "bedoukian.com", "kao.com", "kaochemicals-eu.com",
    "robertet.com",
)
ADMITTED_SOURCE_KINDS = frozenset({"paper", "producer_text"})
_USABLE_REVIEW_STATES = frozenset({"LEGACY_ADVISORY", "REVIEWED_ADVISORY"})


@dataclass(frozen=True)
class StockRef:
    """An owned stock, by its capability ``identity_name`` and stock fraction.

    The name is exactly the identity name the solver's capability index gives,
    and the fraction separates bottles that share it (Ambrox Super neat, 25% and 10%).
    ``grade_differs`` marks a different grade of the cited material; ``note``
    then says how, in one line.
    """

    name: str
    fraction: float
    grade_differs: bool = False
    note: str = ""


@dataclass(frozen=True)
class NodeRef:
    package_id: str
    role_id: str
    function: str  # the node's own "function" text, quoted
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class Helper:
    job: str
    node: NodeRef
    stocks: tuple[StockRef, ...]
    share_of_lead: float


@dataclass(frozen=True)
class AccordSpec:
    note: str
    facet_ids: tuple[str, ...]
    # The accord applies only when the brief names one of these words, as
    # role_identity_requirement does for the lavender and iris leads.
    named_by: tuple[str, ...]
    lead: NodeRef
    lead_stocks: tuple[StockRef, ...]
    helpers: tuple[Helper, ...]
    # Brief words that put one of lead_stocks first, as (words, stock name);
    # the first entry whose word the brief names wins. The stocks stay the same.
    lead_first_when: tuple[tuple[tuple[str, ...], str], ...] = ()


SPECS: tuple[AccordSpec, ...] = (
    AccordSpec(
        note="lavender",
        facet_ids=("aromatic_lavender",),
        named_by=("lavender", "fougere", "fougère"),
        lead=NodeRef("AR_LAVENDER", "recognizer", "lavender identity", ("bontoux_lavender_products",)),
        lead_stocks=(
            StockRef("Lavender EO (BONTAUX SAS)", 1.0, note="the cited producer's lavender oil, neat as supplied"),
            StockRef("Lavender 40/42, Aroma&More", 1.0, True,
                     "Aroma&More 40/42 standardised lavender, not a Bontoux product"),
        ),
        helpers=(
            Helper("texture", NodeRef("AR_LAVENDER", "alternative_texture", "mineral support alternative",
                                      ("dsm_ambrox_super_description",)),
                   (StockRef("Ambrox Super", 1.0, note="crystals, neat as supplied"),
                    StockRef("Ambrox Super", .25, note="Kenny's 25% w/w solution in DPG + IPM + ethanol"),
                    StockRef("Ambrox Super", .1, note="Kenny's 10% w/w solution in ethanol + DPG")),
                   FIRST_HELPER_SHARE),
        ),
        # Kenny, 25 Oct 2026 ("Yes, fougère only"): fougère and barbershop briefs
        # lead with the 40/42 grade (lavandin camphor and cineole, the classic
        # fougère lavender); soft or floral lavender briefs keep the BONTAUX oil.
        lead_first_when=((("fougere", "fougère", "barbershop"), "Lavender 40/42, Aroma&More"),),
    ),
    AccordSpec(
        note="iris",
        facet_ids=("iris_violet", "iris_root", "iris_butter", "iris_cosmetic", "iris_transparent", "iris_woody"),
        named_by=("iris", "orris"),
        lead=NodeRef("FL_IRIS", "recognizer", "root/butter anchor", ("biolandes_orris",)),
        # FL_IRIS's negative space calls Orris Liquid held; Kenny cleared that hold on
        # 2026-10-08 (data/governance/inventory_compounding_holds.json has no records).
        lead_stocks=(
            StockRef("Orris Concrete Orris Butter", .1, True,
                     "PerfumersWorld orris concrete/butter 5IA07847 at 10% w/w in DPG, irone content not "
                     "recorded; not the Biolandes assay-specified butter"),
            StockRef("Orris Butter 50% in EtOH", .5, True,
                     "Kenny's 50% w/w solution in ethanol of MySkinRecipes orris butter, irone content "
                     "unknown; not the Biolandes assay-specified butter"),
            StockRef("Orris Liquid", .09, True,
                     "PerfumersWorld Orris Liquid 8IQ24653 at 9% in DEP, about 1-5% alpha-irone; a liquid "
                     "orris product, not the Biolandes assay-specified butter"),
        ),
        helpers=(
            Helper("texture", NodeRef("FL_IRIS", "bridge", "powder/wood support", ("iff_orivone",)),
                   (StockRef("Orivone", 1.0),), FIRST_HELPER_SHARE),
        ),
    ),
    AccordSpec(
        note="rose",
        facet_ids=("rose",),
        named_by=("rose", "rosy"),
        lead=NodeRef("FL_ROSE", "recognizer", "fresh-petal anchor", ("iff_rose_completion",)),
        # The cited product is a processed (low methyl eugenol) Turkish Rosa damascena
        # oil (claim iff_rose_completion_descriptor). Kenny owns no processed grade.
        lead_stocks=(
            StockRef("Rose Otto Bulgarian", .1, True,
                     "PerfumersWorld 5RR12478 Bulgarian Rosa damascena otto at 10% w/w in DPG; steam-distilled, "
                     "not IFF's processed low-methyl-eugenol Turkish product"),
            StockRef("Rose Essential Oil (Rosa Damascena, India)", 1.0, True,
                     "steam-distilled Rosa damascena oil from India, neat; not IFF's processed "
                     "low-methyl-eugenol Turkish product"),
            StockRef("Rose de Mai Absolute", .1, True,
                     "Rosa centifolia absolute at 10% w/w in DPG: another species and a solvent extract, "
                     "not a damascena oil"),
        ),
        helpers=(
            Helper("lift", NodeRef("FL_ROSE", "bridge", "transparent petal support", ("dsm_hedione_foundation",)),
                   (StockRef("Hedione", 1.0),), FIRST_HELPER_SHARE),
        ),
    ),
    AccordSpec(
        note="vetiver",
        facet_ids=("vetiver_root",),
        named_by=("vetiver",),
        lead=NodeRef("WO_VETIVER", "recognizer", "root anchor", ("iff_vetiver_completion",)),
        lead_stocks=(
            StockRef("Vetiver EO (Haiti)", 1.0, True,
                     "Haitian vetiver oil of unrecorded supplier, not IFF LMR Vetiver Oil Haiti"),
        ),
        helpers=(
            # WO_VETIVER's CONTROL_CORE pairs the root anchor with this socket, so it comes first.
            Helper("texture", NodeRef("WO_VETIVER", "alternative_texture", "transparent dry support",
                                      ("iff_iso_e_super_completion",)),
                   (StockRef("Iso E Super", 1.0),), FIRST_HELPER_SHARE),
            Helper("contrast", NodeRef("WO_VETIVER", "bridge", "citrus contrast", ("iff_bergamot_fcr_foundation",)),
                   (StockRef("Bergamot FCF Oil Sicilian", 1.0, True,
                             "FCF bergamot, not the cited FCR grade (claim bergamot_fcr_product_boundary)"),),
                   SECOND_HELPER_SHARE),
        ),
    ),
    AccordSpec(
        note="apricot",
        facet_ids=("apricot",),
        named_by=("apricot", "apricots"),
        lead=NodeRef("FR_STONE", "recognizer", "apricot/tea/leather bridge", ("iff_osmanthus_completion",)),
        lead_stocks=(
            StockRef("Osmanthus Absolute", .1, True,
                     "osmanthus absolute of unrecorded supplier at 10% w/w in DPG, not IFF LMR Osmanthus Absolute"),
        ),
        helpers=(
            Helper("texture", NodeRef("FR_STONE", "bridge", "creamy flesh socket",
                                      ("givaudan_methyl_laitone_completion",)),
                   (StockRef("Methyl Laitone", .2, True,
                             "20% v/v in ethanol, not the cited Givaudan 10%/DPG product"),),
                   FIRST_HELPER_SHARE),
        ),
    ),
    AccordSpec(
        note="sandalwood",
        facet_ids=("creamy_wood",),
        # creamy_wood also answers "creamy wood", "milky wood" and "soft wood"; the
        # sandalwood accord applies only when the brief names sandalwood.
        named_by=("sandalwood", "sandal"),
        lead=NodeRef("WO_SANDAL", "recognizer", "natural product anchor", ("iff_sandal_nc_completion",)),
        lead_stocks=(
            StockRef("Sandalwood EO", .1, True,
                     "PerfumersWorld sandalwood oil at 10% in DPG; CAS 84787-70-2 is the Santalum album CAS, but "
                     "the certificate names no species; not IFF's New Caledonian S. austrocaledonicum oil"),
        ),
        helpers=(
            # The producer describes warm sweet sandalwood (claim sandalwood_exact_register),
            # and CONTROL_CORE calls it a restrained synthetic support to the natural core.
            Helper("round", NodeRef("WO_SANDAL", "bridge", "synthetic sandal socket",
                                    ("givaudan_sandalore_foundation",)),
                   (StockRef("Sandalore", 1.0),), FIRST_HELPER_SHARE),
        ),
    ),
)

# Notes the brief asked for that have no spec, and why.
NOT_COVERED = MappingProxyType({
    "pear": (
        "No facet in semantic_brief_adapter.py is pear: pear is one word of the umbrella 'fruit' facet "
        "(with apple, peach, plum, berry, mango, pineapple), so a pear accord keyed by facet id would "
        "land on every fruit brief. FR_ORCHARD's floral-fruit socket cites only marketed perfumes."
    ),
})

# Nodes and stocks left out, and why. Ownership and readiness are as the solver's
# material_capability_index.build_material_capability_index() reports them.
EXCLUDED: tuple[Mapping[str, str], ...] = tuple(MappingProxyType(row) for row in (
    {"note": "lavender", "node": "AR_LAVENDER/bridge", "material": "Houbigant Fougere Royale structure",
     "reason": "only source is a marketed perfume page (houbigant_fougere_royale_extrait)"},
    {"note": "lavender", "node": "AR_FOUGERE/recognizer, AR_FOUGERE/alternative_texture",
     "material": "Fougere Royale, Guerlain Mitsouko structures",
     "reason": "only sources are marketed perfume pages"},
    {"note": "lavender", "node": "AR_FOUGERE/bridge", "material": "IFF Tonka Bean Absolute",
     "reason": "Tonka Bean Absolute 10% in DPG is owned and executable, but this is fougere structure, not the "
               "lavender note: AR_LAVENDER's negative space says not to equate lavender with tonka sweetness, "
               "and a fougere brief already gets coumarin/tonka from the fougere_coumarin facet"},
    {"note": "lavender", "node": "AR_LAVENDER/recognizer", "material": "Lavender EO (1% in DPG)",
     "reason": "a trace grade (stock fraction .01, below .05) and a stronger grade is owned: the neat BONTAUX oil "
               "leads. The 1% record does not say which lavender oil it was made from"},
    {"note": "lavender", "node": "AR_LAVENDER/recognizer", "material": "Lavandin Absolute, Spike Lavender EO",
     "reason": "owned but not design-ready in the capability index"},
    {"note": "iris", "node": "FL_IRIS/bridge", "material": "Meth Ionone Gamma Coeur",
     "reason": "depleted 2026-09-24; inventory says AIMI is not a substitute"},
    {"note": "iris", "node": "FL_IRIS/alternative_texture", "material": "Dihydro Beta Ionone",
     "reason": "FL_IRIS pairs the petal alternative with the bridge, never with the root anchor "
               "(ALTERNATIVE_SOCKET = bridge + alternative_texture): it replaces the lead, it does not help it"},
    {"note": "iris", "node": "FL_IRIS/recognizer", "material": "Iris Florentina Root Extract (5% in DPG)",
     "reason": "a MySkinRecipes PG scent extract of unasserted strength and irone content; it never stands "
               "for an orris absolute or butter"},
    {"note": "iris", "node": "FL_IRIS/recognizer", "material": "Alpha Irone (10% in DEP, 25% in IPM)",
     "reason": "an isolated irone, not a grade of orris butter: an irone dilution and an orris extract are "
               "distinct products (claim iris_extract_identity)"},
    {"note": "rose", "node": "FL_ROSE/alternative_texture", "material": "Meth Ionone Gamma Coeur",
     "reason": "depleted 2026-09-24"},
    {"note": "rose", "node": "FL_ROSE/recognizer", "material": "Cabbage Rose Extract (1% in DPG)",
     "reason": "a trace grade (stock fraction .01, below .05) of a MySkinRecipes Rosa centifolia extract of "
               "unasserted strength, and stronger natural rose grades are owned"},
    {"note": "rose", "node": "FL_ROSE/bridge", "material": "Hedione HC",
     "reason": "another grade of the cited Hedione, and owned but not design-ready; Hedione is used"},
    {"note": "vetiver", "node": "WO_VETIVER/recognizer", "material": "Haitian Vetiver EO (inventory.txt text row)",
     "reason": "design-ready text row with no pipettable bottle record (not execution-ready); the bottle is "
               "Vetiver EO (Haiti), which is used"},
    {"note": "sandalwood", "node": "WO_SANDAL/alternative_texture", "material": "Givaudan Javanol Super",
     "reason": "not owned. Kenny's neat Javanol is the other grade, which the producer describes as rosy/powdery "
               "where Javanol Super is woodier and lactonic (claim givaudan_javanol_super_completion_descriptor). "
               "The node is a grade contrast socket, so its job is that grade's own character, and WO_SANDAL's "
               "stop rule rejects rosy drift: another grade cannot fill it"},
    {"note": "sandalwood", "node": "WO_SANDAL/recognizer", "material": "Sandalwood Base X3",
     "reason": "a pre-blended sandalwood base of undisclosed composition, not a grade of the cited natural oil"},
    {"note": "apricot", "node": "FR_STONE/alternative_texture", "material": "IFF Davana Oil",
     "reason": "not owned"},
    {"note": "apricot", "node": "FR_STONE/recognizer", "material": "Osmanthus Absolute (volume grade), neat",
     "reason": "design-ready text row with no pipettable bottle record (not execution-ready); the 10% in DPG "
               "absolute is used"},
    {"note": "pear", "node": "FR_ORCHARD/alternative_texture", "material": "Pera Granita, English Pear & Freesia",
     "reason": "only sources are marketed perfume pages"},
))


def _pmid(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.hostname == "pubmed.ncbi.nlm.nih.gov":
        match = re.fullmatch(r"/(\d+)/?", parsed.path)
        return match.group(1) if match else None
    return None


def source_kind(record: Mapping[str, Any]) -> str:
    """'paper', 'producer_text' or 'other', from the source record itself."""
    url = str(record.get("url") or "")
    host = (urlparse(url).hostname or "").removeprefix("www.")
    if record.get("evidence_class") == "PRIMARY_RESEARCH" and (record.get("doi") or _pmid(url)):
        return "paper"
    if record.get("evidence_class") == "MANUFACTURER_DESCRIPTION" and any(
        host == known or host.endswith("." + known) for known in _PRODUCER_HOSTS
    ):
        return "producer_text"
    return "other"


def source_citation(record: Mapping[str, Any]) -> str:
    if record.get("doi"):
        return f"DOI {record['doi']}"
    pmid = _pmid(str(record.get("url") or ""))
    return f"PMID {pmid}" if pmid else str(record.get("url") or "")


@lru_cache(maxsize=1)
def source_records() -> tuple[Mapping[str, Mapping[str, Any]], Mapping[str, str]]:
    """literature_v1.json source records, and each one's source_reviews_v1.json review state."""
    with LITERATURE_PATH.open(encoding="utf-8") as handle:
        sources = {row["source_id"]: row for row in json.load(handle)["sources"]}
    with SOURCE_REVIEWS_PATH.open(encoding="utf-8") as handle:
        reviews = {row["source_id"]: row["review_state"] for row in json.load(handle)["records"]}
    return MappingProxyType(sources), MappingProxyType(reviews)


@lru_cache(maxsize=1)
def _capability_index():
    """The formula solver's own capability index, built once on first use."""
    from .material_capability_index import build_material_capability_index

    return build_material_capability_index()


def _unbound_reason(name: str, fraction: float) -> str | None:
    """Why (name, fraction) is not one capability Kenny can pipette, or None when it is."""
    matches = [
        capability for capability in _capability_index().capabilities
        if capability.identity_name == name and abs(capability.candidate.stock.dilution - fraction) < 1e-9
    ]
    if len(matches) != 1:
        return f"{len(matches)} capabilities have that identity name and fraction"
    if not matches[0].design_ready:
        return "not design-ready"
    if not matches[0].execution_ready:
        return "not execution-ready (no pipettable bottle record)"
    return None


def _known_facet_ids() -> frozenset[str]:
    from . import semantic_brief_adapter as adapter

    return frozenset({facet.facet_id for facet in adapter._FACETS} | set(adapter._LITERATURE_FACETS))


def _check_node(ref: NodeRef, packages: Mapping[str, Mapping[str, Any]], where: str) -> Mapping[str, Any]:
    package = packages.get(ref.package_id)
    nodes = {node["role_id"]: node for node in package["functional_graph"]["nodes"]} if package else {}
    node = nodes.get(ref.role_id)
    if node is None:
        raise ValueError(f"{where}: no node {ref.package_id}/{ref.role_id} in the construction library")
    if node["function"] != ref.function:
        raise ValueError(f"{where}: function text {ref.function!r} is not the node's {node['function']!r}")
    if not ref.source_ids or not set(ref.source_ids) <= set(node["source_ids"]):
        raise ValueError(f"{where}: sources {ref.source_ids} are not the node's {node['source_ids']}")
    records, reviews = source_records()
    bound = {row["source_id"]: row["source_record_sha256"] for row in package["source_bindings"]}
    for source_id in ref.source_ids:
        if source_id not in records or source_id not in reviews:
            raise ValueError(f"{where}: source {source_id} has no reviewed source record")
        if reviews[source_id] not in _USABLE_REVIEW_STATES:
            raise ValueError(f"{where}: source {source_id} is under review state {reviews[source_id]}")
        if bound.get(source_id) != source_record_hash(records[source_id]):
            raise ValueError(f"{where}: source {source_id} is not bound to {ref.package_id} at its current record")
    if not any(source_kind(records[source_id]) in ADMITTED_SOURCE_KINDS for source_id in ref.source_ids):
        raise ValueError(f"{where}: no producer text or paper among {ref.source_ids}")
    return node


def _check_stocks(stocks: Sequence[StockRef], where: str) -> None:
    if not stocks:
        raise ValueError(f"{where}: no owned stock")
    for stock in stocks:
        if stock.grade_differs and not stock.note.strip():
            raise ValueError(f"{where}: {stock.name} differs in grade but has no note")
        reason = _unbound_reason(stock.name, stock.fraction)
        if reason:
            raise ValueError(
                f"{where}: {stock.name} at {stock.fraction} is not one owned, design-ready stock "
                f"Kenny can pipette: {reason}"
            )


def validate_specs(specs: Sequence[AccordSpec]) -> None:
    """Raise ValueError on the first spec that breaks a rule in the module docstring."""
    packages = {row["package_id"]: row for row in load_construction_library()["packages"]}
    known_facets, seen_facets = _known_facet_ids(), set()
    for spec in specs:
        where = f"{spec.note} accord"
        if not spec.facet_ids or not set(spec.facet_ids) <= known_facets:
            raise ValueError(f"{where}: unknown facet ids {set(spec.facet_ids) - known_facets}")
        if seen_facets & set(spec.facet_ids):
            raise ValueError(f"{where}: facet already has a spec")
        seen_facets |= set(spec.facet_ids)
        _check_node(spec.lead, packages, f"{where} lead")
        _check_stocks(spec.lead_stocks, f"{where} lead")
        if not spec.helpers:
            raise ValueError(f"{where}: no helper")
        architectures = packages[spec.lead.package_id]["architectures"]
        names = [(stock.name, stock.fraction) for stock in spec.lead_stocks]
        for helper in spec.helpers:
            part = f"{where} helper {helper.node.package_id}/{helper.node.role_id}"
            if "bridge" in JOBS or helper.job not in JOBS:
                raise ValueError(f"{part}: job {helper.job!r} is not one of {sorted(JOBS)}")
            if helper.node.package_id != spec.lead.package_id or not any(
                {spec.lead.role_id, helper.node.role_id} <= set(row["roles"]) for row in architectures
            ):
                raise ValueError(f"{part}: no architecture in {spec.lead.package_id} pairs it with the lead")
            _check_node(helper.node, packages, part)
            _check_stocks(helper.stocks, part)
            if not 0 < helper.share_of_lead <= .5:
                raise ValueError(f"{part}: share {helper.share_of_lead} is not clearly below the lead")
            names += [(stock.name, stock.fraction) for stock in helper.stocks]
        if sum(helper.share_of_lead for helper in spec.helpers) >= 1:
            raise ValueError(f"{where}: helpers together reach the lead's share")
        if len(names) != len(set(names)):
            raise ValueError(f"{where}: a stock fills two parts of the accord")


@lru_cache(maxsize=1)
def _validated() -> tuple[Mapping[str, AccordSpec], Mapping[str, str]]:
    """The specs that pass ``validate_specs``, by facet id, and each left-out
    spec's note with the reason."""

    usable: list[AccordSpec] = []
    skipped: dict[str, str] = {}
    for spec in SPECS:
        try:
            validate_specs((*usable, spec))
        except ValueError as error:
            skipped[spec.note] = str(error)
        else:
            usable.append(spec)
    return (
        MappingProxyType({facet_id: spec for spec in usable for facet_id in spec.facet_ids}),
        MappingProxyType(skipped),
    )


def accord_spec_for(facet_id: str) -> AccordSpec | None:
    """The cited accord for a facet, or None when the facet has none or its spec is left out."""
    return _validated()[0].get(facet_id)


def covered_facets() -> frozenset[str]:
    return frozenset(_validated()[0])


def skipped_specs() -> Mapping[str, str]:
    """Each spec left out at run time, by note, with the reason."""
    return _validated()[1]
