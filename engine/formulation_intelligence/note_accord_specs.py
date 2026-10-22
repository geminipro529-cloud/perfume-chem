"""Cited note accords: a lead plus helpers, each helper with a job and a source.

A plain data table plus validation. Nothing here is wired into the composer yet.

Every node comes from ``construction_library_v1.json`` and quotes that node's own
"function" text. A lead or helper is admitted only when at least one of its
sources is a producer technical text or a paper (DOI or PMID). The kind is read
from the source's record in ``literature_v1.json`` (evidence class, DOI, URL),
never from the source id. Nodes whose only sources are marketed perfumes, and
materials Kenny does not own, are left out and listed in ``EXCLUDED``.

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
    "share_of_lead is the helper's active amount (stock volume x stock fraction) as a "
    "fraction of the lead's active amount. The numbers are design defaults, not "
    "citations: no source gives a dose. They copy today's _ACCORD_SPLIT ratios "
    "(.23/.62 = .37 for the first helper, .15/.62 = .24 for the second), so wiring "
    "changes what a helper is and why, not how big it is. Each helper stays below "
    "half the lead and all helpers together stay below the lead."
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
    """An owned stock, by its exact parsed inventory name and stock fraction.

    The fraction separates bottles that share a name (Lavender EO neat and 1%).
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


SPECS: tuple[AccordSpec, ...] = (
    AccordSpec(
        note="lavender",
        facet_ids=("aromatic_lavender",),
        named_by=("lavender", "fougere", "fougère"),
        lead=NodeRef("AR_LAVENDER", "recognizer", "lavender identity", ("bontoux_lavender_products",)),
        lead_stocks=(
            StockRef("Lavender EO", 1.0),  # inventory.txt "Lavender EO (BONTAUX SAS)", the cited producer's oil
            StockRef("Lavender 40/42, Aroma&More", 1.0, True,
                     "Aroma&More 40/42 standardised lavender, not a Bontoux product"),
        ),
        helpers=(
            Helper("texture", NodeRef("AR_LAVENDER", "alternative_texture", "mineral support alternative",
                                      ("dsm_ambrox_super_description",)),
                   (StockRef("Ambrox Super Crystals", 1.0),), FIRST_HELPER_SHARE),
        ),
    ),
    AccordSpec(
        note="iris",
        facet_ids=("iris_violet", "iris_root", "iris_butter", "iris_cosmetic", "iris_transparent", "iris_woody"),
        named_by=("iris", "orris"),
        lead=NodeRef("FL_IRIS", "recognizer", "root/butter anchor", ("biolandes_orris",)),
        # FL_IRIS's negative space calls Orris Liquid held; Kenny cleared that hold on
        # 2026-10-08 (data/governance/inventory_compounding_holds.json has no records).
        lead_stocks=(
            StockRef("Orris Liquid", .09, True,
                     "PerfumersWorld Orris Liquid 8IQ24653 at 9% in DEP, not the Biolandes assay-specified butter"),
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
        lead_stocks=(
            StockRef("Rose Essential Oil", 1.0, True,
                     "steam-distilled Rosa damascena (India), not IFF Rose Essential Low ME For Life"),
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
            StockRef("Haitian Vetiver EO", 1.0, True,
                     "Haitian vetiver oil of unrecorded supplier, not IFF LMR Vetiver Oil Haiti"),
        ),
        helpers=(
            # WO_VETIVER's CONTROL_CORE pairs the root anchor with this socket, so it comes first.
            Helper("texture", NodeRef("WO_VETIVER", "alternative_texture", "transparent dry support",
                                      ("iff_iso_e_super_completion",)),
                   (StockRef("Iso E Super", 1.0),), FIRST_HELPER_SHARE),
            Helper("contrast", NodeRef("WO_VETIVER", "bridge", "citrus contrast", ("iff_bergamot_fcr_foundation",)),
                   (StockRef("Bergamot FCF oil Sicilian", 1.0, True,
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
            StockRef("Osmanthus Absolute", 1.0, True,
                     "volume-grade osmanthus absolute (lower beta-ionone), not IFF LMR Osmanthus Absolute"),
        ),
        helpers=(
            Helper("texture", NodeRef("FR_STONE", "bridge", "creamy flesh socket",
                                      ("givaudan_methyl_laitone_completion",)),
                   (StockRef("Methyl Laitone", .2, True,
                             "20% v/v in ethanol, not the cited Givaudan 10%/DPG product"),),
                   FIRST_HELPER_SHARE),
        ),
    ),
)

# Notes the brief asked for that have no spec, and why.
NOT_COVERED = MappingProxyType({
    "sandalwood": (
        "WO_SANDAL is natural-oil-led ('natural product anchor'), and Kenny's only sandalwood oil, "
        "Sandalwood EO 10% in DPG, is not design-ready in the parsed inventory; Sandalwood Base 3X is a "
        "pre-blended accord, not the cited oil. Without the anchor the 'synthetic sandal socket' "
        "(Sandalore) has nothing to support, and the 'grade contrast socket' (Javanol Super) is not owned."
    ),
    "pear": (
        "No facet in semantic_brief_adapter.py is pear: pear is one word of the umbrella 'fruit' facet "
        "(with apple, peach, plum, berry, mango, pineapple), so a pear accord keyed by facet id would "
        "land on every fruit brief. FR_ORCHARD's floral-fruit socket cites only marketed perfumes."
    ),
})

# Nodes and stocks left out, and why. Ownership and design-readiness are as
# composition_planner._cached_legacy_inventory(sha, include_unavailable=False)
# parses inventory.txt, with engine.inventory_completions.effective_design_ready.
EXCLUDED: tuple[Mapping[str, str], ...] = tuple(MappingProxyType(row) for row in (
    {"note": "lavender", "node": "AR_LAVENDER/bridge", "material": "Houbigant Fougere Royale structure",
     "reason": "only source is a marketed perfume page (houbigant_fougere_royale_extrait)"},
    {"note": "lavender", "node": "AR_FOUGERE/recognizer, AR_FOUGERE/alternative_texture",
     "material": "Fougere Royale, Guerlain Mitsouko structures",
     "reason": "only sources are marketed perfume pages"},
    {"note": "lavender", "node": "AR_FOUGERE/bridge", "material": "IFF Tonka Bean Absolute",
     "reason": "fougere structure, not the lavender note: AR_LAVENDER's negative space says not to equate "
               "lavender with tonka sweetness, and a fougere brief already gets coumarin/tonka from the "
               "fougere_coumarin facet"},
    {"note": "lavender", "node": "AR_LAVENDER/recognizer", "material": "Lavender EO (1%)",
     "reason": "owned but not design-ready; the neat Bontaux oil is preferred"},
    {"note": "lavender", "node": "AR_LAVENDER/alternative_texture", "material": "Ambrox Super (25% w/w)",
     "reason": "owned but not design-ready; Ambrox Super Crystals is used"},
    {"note": "iris", "node": "FL_IRIS/bridge", "material": "Meth Ionone Gamma Coeur",
     "reason": "depleted 2026-09-24; inventory says AIMI is not a substitute"},
    {"note": "iris", "node": "FL_IRIS/alternative_texture", "material": "Dihydro Beta Ionone",
     "reason": "FL_IRIS pairs the petal alternative with the bridge, never with the root anchor "
               "(ALTERNATIVE_SOCKET = bridge + alternative_texture): it replaces the lead, it does not help it"},
    {"note": "iris", "node": "FL_IRIS/recognizer", "material": "Orris Concrete Orris Butter (10% in DPG)",
     "reason": "owned but not design-ready"},
    {"note": "rose", "node": "FL_ROSE/alternative_texture", "material": "Meth Ionone Gamma Coeur",
     "reason": "depleted 2026-09-24"},
    {"note": "rose", "node": "FL_ROSE/recognizer", "material": "Rose de Mai Absolute 10%, Rose Otto Bulgarian 10%",
     "reason": "owned but not design-ready"},
    {"note": "sandalwood", "node": "WO_SANDAL/alternative_texture", "material": "Givaudan Javanol Super",
     "reason": "not owned; Javanol is a different grade described as rosy/powdery rather than woody/lactonic "
               "(claim givaudan_javanol_super_completion_descriptor), and the node is a grade contrast"},
    {"note": "apricot", "node": "FR_STONE/alternative_texture", "material": "IFF Davana Oil",
     "reason": "not owned"},
    {"note": "apricot", "node": "FR_STONE/recognizer", "material": "Osmanthus Absolute (10% in DPG)",
     "reason": "owned but not design-ready; the volume-grade neat absolute is used"},
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


def _owned_design_ready(name: str, fraction: float) -> bool:
    from engine.inventory_completions import effective_design_ready
    from engine.research.composition_planner import _cached_legacy_inventory, _inventory_text_sha256

    rows = [
        stock for stock in _cached_legacy_inventory(_inventory_text_sha256(), False)
        if stock.name == name and abs(stock.dilution - fraction) < 1e-9
    ]
    return len(rows) == 1 and effective_design_ready(rows[0])


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
        if not _owned_design_ready(stock.name, stock.fraction):
            raise ValueError(f"{where}: {stock.name} at {stock.fraction} is not one owned, design-ready stock")


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
def _validated() -> Mapping[str, AccordSpec]:
    validate_specs(SPECS)
    return MappingProxyType({facet_id: spec for spec in SPECS for facet_id in spec.facet_ids})


def accord_spec_for(facet_id: str) -> AccordSpec | None:
    """The cited accord for a facet, or None when the facet has none."""
    return _validated().get(facet_id)


def covered_facets() -> frozenset[str]:
    return frozenset(_validated())
