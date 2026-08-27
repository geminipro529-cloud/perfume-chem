"""Evidence ledger for perfume reconstruction.

Stores what sources claim, weighted by authority, with contradiction detection.
Each claim is traceable to a source, and sources are classified by a letter-grade
authority scale (A = authenticated formula through J = AI inference).

Usage::

    from engine.evidence.ledger import EvidenceLedger, EvidenceSource, EvidenceClaim

    ledger = EvidenceLedger()
    src = EvidenceSource(
        source_id="550e8400-e29b-41d4-a716-446655440000",
        source_class="A",
        doi="10.1000/xyz123",
    )
    ledger.add_source(src)
    ledger.add_claim(EvidenceClaim(
        claim_id="660e8400-e29b-41d4-a716-446655440001",
        source_id=src.source_id,
        reference_product_id="chanel_no_5",
        claim_type="identity_presence",
        subject_material_name="Bergamot",
    ))
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.domain_errors import LegacyWriteProhibitedError

# ── Source authority classes ────────────────────────────────────────────────────

A = "Authenticated formula or manufacturer dossier"
B = "Calibrated quantitative analytical result"
C = "Identity confirmed by authentic standard and retention evidence"
D = "Probable analytical identity"
E = "Official package ingredient or allergen evidence"
F = "Official brand note and product description"
G = "Patent, supplier demo, or perfumer interview"
H = "Secondary ranked identity roster"
I = "Community sensory evidence"  # noqa: E741 - public authority-grade constant
J = "AI inference"

SOURCE_CLASSES: tuple[str, ...] = (A, B, C, D, E, F, G, H, I, J)
"""All source-class constants in authority order (highest to lowest)."""

SOURCE_CLASS_LETTERS: dict[str, str] = {
    "A": A,
    "B": B,
    "C": C,
    "D": D,
    "E": E,
    "F": F,
    "G": G,
    "H": H,
    "I": I,
    "J": J,
}
"""Mapping from single-letter key to full description."""


# ── Dataclasses ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class EvidenceSource:
    """A single source of evidence about a perfume's composition.

    Parameters
    ----------
    source_id:
        UUID string identifying this source.
    source_class:
        Authority letter (``"A"`` through ``"J"``). See module-level constants.
    url:
        Web location of the source, if available.
    doi:
        Digital Object Identifier, if available.
    title:
        Human-readable title or description of the source.
    access_date:
        ISO 8601 date string when the source was accessed.
    rights:
        Usage / redistribution rights statement.
    permitted_excerpt:
        Verbatim excerpt that may be reproduced under the rights granted.
    """

    source_id: str
    source_class: str
    url: str | None = None
    doi: str | None = None
    title: str = ""
    access_date: str | None = None
    rights: str = ""
    permitted_excerpt: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_class": self.source_class,
            "url": self.url,
            "doi": self.doi,
            "title": self.title,
            "access_date": self.access_date,
            "rights": self.rights,
            "permitted_excerpt": self.permitted_excerpt,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceSource:
        return cls(
            source_id=str(data["source_id"]),
            source_class=str(data["source_class"]),
            url=str(data["url"]) if data.get("url") else None,
            doi=str(data["doi"]) if data.get("doi") else None,
            title=str(data.get("title") or ""),
            access_date=str(data["access_date"]) if data.get("access_date") else None,
            rights=str(data.get("rights") or ""),
            permitted_excerpt=str(data.get("permitted_excerpt") or ""),
        )


@dataclass(frozen=True, slots=True)
class EvidenceClaim:
    """A single claim extracted from a source about a perfume's composition.

    Parameters
    ----------
    claim_id:
        UUID string identifying this claim.
    source_id:
        UUID string referencing the :class:`EvidenceSource` this claim came from.
    reference_product_id:
        Identifier for the perfume this claim is about.
    claim_type:
        Kind of claim. One of ``"identity_presence"``, ``"rank"``, ``"amount"``,
        ``"functional_role"``, ``"sensory"``, ``"gcms_peak"``, ``"gco_event"``.
    subject_material_id:
        Resolved material UUID, if known.
    subject_material_name:
        Raw material name as it appears in the source.
    reported_value:
        Numeric value reported (e.g. amount, peak area).
    reported_unit:
        Unit for ``reported_value`` (e.g. ``"%"``, ``"ppm"``, ``"area_pct"``).
    rank:
        Position in a ranked list (1-indexed).
    independence_group:
        Groups claims that originate from the same underlying data to prevent
        duplicate internet sources from inflating confidence. Claims sharing
        the same group are treated as dependent.
    identity_confidence:
        How confident the source is about material identity (0.0 – 1.0).
    quantity_confidence:
        How confident the source is about the reported quantity (0.0 – 1.0).
    exact_excerpt:
        Verbatim quote from the source supporting this claim.
    interpretation:
        AI or human interpretation of what the excerpt means.
    """

    claim_id: str
    source_id: str
    reference_product_id: str
    claim_type: str
    subject_material_id: str | None = None
    subject_material_name: str = ""
    reported_value: float | None = None
    reported_unit: str | None = None
    rank: int | None = None
    independence_group: str = ""
    identity_confidence: float = 0.0
    quantity_confidence: float = 0.0
    exact_excerpt: str = ""
    interpretation: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "source_id": self.source_id,
            "reference_product_id": self.reference_product_id,
            "claim_type": self.claim_type,
            "subject_material_id": self.subject_material_id,
            "subject_material_name": self.subject_material_name,
            "reported_value": self.reported_value,
            "reported_unit": self.reported_unit,
            "rank": self.rank,
            "independence_group": self.independence_group,
            "identity_confidence": self.identity_confidence,
            "quantity_confidence": self.quantity_confidence,
            "exact_excerpt": self.exact_excerpt,
            "interpretation": self.interpretation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceClaim:
        return cls(
            claim_id=str(data["claim_id"]),
            source_id=str(data["source_id"]),
            reference_product_id=str(data["reference_product_id"]),
            claim_type=str(data["claim_type"]),
            subject_material_id=str(data["subject_material_id"])
            if data.get("subject_material_id")
            else None,
            subject_material_name=str(data.get("subject_material_name") or ""),
            reported_value=_optional_float(data.get("reported_value")),
            reported_unit=str(data["reported_unit"]) if data.get("reported_unit") else None,
            rank=_optional_int(data.get("rank")),
            independence_group=str(data.get("independence_group") or ""),
            identity_confidence=float(data.get("identity_confidence") or 0.0),
            quantity_confidence=float(data.get("quantity_confidence") or 0.0),
            exact_excerpt=str(data.get("exact_excerpt") or ""),
            interpretation=str(data.get("interpretation") or ""),
        )


@dataclass(frozen=True, slots=True)
class ContradictionReport:
    """Records a detected contradiction between two or more claims.

    Parameters
    ----------
    contradiction_group:
        Unique identifier for this contradiction (e.g. ``"contra_001"``).
    claims:
        The conflicting claims.
    subject_material:
        The material name that the contradiction revolves around.
    resolution:
        How the contradiction was resolved (e.g. which claim was preferred
        and why).
    expected_loss:
        What is lost by choosing one claim over another (e.g. accuracy,
        precision, source authority).
    """

    contradiction_group: str
    claims: tuple[EvidenceClaim, ...]
    subject_material: str
    resolution: str = ""
    expected_loss: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "contradiction_group": self.contradiction_group,
            "claims": [c.as_dict() for c in self.claims],
            "subject_material": self.subject_material,
            "resolution": self.resolution,
            "expected_loss": list(self.expected_loss),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContradictionReport:
        return cls(
            contradiction_group=str(data["contradiction_group"]),
            claims=tuple(
                EvidenceClaim.from_dict(c) if isinstance(c, dict) else c
                for c in data.get("claims", [])
            ),
            subject_material=str(data["subject_material"]),
            resolution=str(data.get("resolution") or ""),
            expected_loss=tuple(str(x) for x in data.get("expected_loss") or []),
        )


# ── Ledger ──────────────────────────────────────────────────────────────────────


class EvidenceLedger:
    """In-memory evidence ledger for one or more perfumes.

    Stores :class:`EvidenceSource` and :class:`EvidenceClaim` records and
    provides query methods for material-level and product-level lookups,
    independence filtering, and contradiction detection.
    """

    def __init__(self) -> None:
        self._sources: dict[str, EvidenceSource] = {}
        self._claims: list[EvidenceClaim] = []

    # ── mutation ────────────────────────────────────────────────────────────

    def add_source(self, source: EvidenceSource) -> None:
        """Reject writes to the deprecated in-memory duplicate store."""
        del source
        raise LegacyWriteProhibitedError(
            "EvidenceLedger is read-only; persist evidence through LabService"
        )

    def add_claim(self, claim: EvidenceClaim) -> None:
        """Reject writes to the deprecated in-memory duplicate store."""
        del claim
        raise LegacyWriteProhibitedError(
            "EvidenceLedger is read-only; persist evidence through LabService"
        )

    # ── queries ─────────────────────────────────────────────────────────────

    def get_claims_for_material(self, material_name: str) -> list[EvidenceClaim]:
        """Return all claims whose ``subject_material_name`` matches (case-insensitive)."""
        mn = material_name.casefold()
        return [c for c in self._claims if c.subject_material_name.casefold() == mn]

    def get_claims_for_product(self, product_id: str) -> list[EvidenceClaim]:
        """Return all claims for a given product."""
        return [c for c in self._claims if c.reference_product_id == product_id]

    def get_independent_claims(self, product_id: str) -> list[EvidenceClaim]:
        """Return one claim per independence group for a product.

        When multiple claims share the same ``independence_group``, only the
        claim from the highest-authority source (lowest letter A–J) is kept.
        Claims with an empty ``independence_group`` are each treated as
        independent.
        """
        product_claims = self.get_claims_for_product(product_id)

        # Group by independence_group; empty string → each claim is its own group.
        groups: dict[str, list[EvidenceClaim]] = {}
        for c in product_claims:
            key = c.independence_group or c.claim_id
            groups.setdefault(key, []).append(c)

        result: list[EvidenceClaim] = []
        for group_key, group_claims in groups.items():
            best = _pick_highest_authority(group_claims, self._sources)
            result.append(best)

        return result

    def find_contradictions(self, product_id: str) -> list[ContradictionReport]:
        """Detect contradictions among claims for a given product.

        A contradiction is defined as two or more claims about the same
        material that disagree on ``reported_value``, ``rank``, or
        ``claim_type`` in a way that cannot both be true.

        Returns a list of :class:`ContradictionReport` objects, one per
        detected contradiction.
        """
        product_claims = self.get_claims_for_product(product_id)

        # Group claims by material name.
        by_material: dict[str, list[EvidenceClaim]] = {}
        for c in product_claims:
            key = c.subject_material_name.casefold() if c.subject_material_name else "__unnamed__"
            by_material.setdefault(key, []).append(c)

        contradictions: list[ContradictionReport] = []
        contra_idx = 0

        for material_name, claims in by_material.items():
            if len(claims) < 2:
                continue

            # Check for value contradictions (same claim_type, different reported_value).
            value_claims: dict[str, list[EvidenceClaim]] = {}
            for c in claims:
                if c.reported_value is not None and c.claim_type:
                    value_claims.setdefault(c.claim_type, []).append(c)

            for claim_type, vc in value_claims.items():
                if len(vc) < 2:
                    continue
                values = {c.reported_value for c in vc if c.reported_value is not None}
                if len(values) > 1:
                    contra_idx += 1
                    contradictions.append(
                        ContradictionReport(
                            contradiction_group=f"contra_{contra_idx:04d}",
                            claims=tuple(vc),
                            subject_material=material_name,
                            resolution="",
                            expected_loss=(),
                        )
                    )

            # Check for rank contradictions.
            rank_claims = [c for c in claims if c.rank is not None]
            if len(rank_claims) >= 2:
                ranks = {c.rank for c in rank_claims}
                if len(ranks) > 1:
                    contra_idx += 1
                    contradictions.append(
                        ContradictionReport(
                            contradiction_group=f"contra_{contra_idx:04d}",
                            claims=tuple(rank_claims),
                            subject_material=material_name,
                            resolution="",
                            expected_loss=(),
                        )
                    )

        return contradictions

    def build_documentary_matrix(self, product_id: str) -> dict[str, list[EvidenceClaim]]:
        """Return claims grouped by ``subject_material_name`` for a product.

        The returned dict maps each material name (as reported in the source)
        to the list of claims about that material.
        """
        product_claims = self.get_claims_for_product(product_id)
        matrix: dict[str, list[EvidenceClaim]] = {}
        for c in product_claims:
            key = c.subject_material_name or "__unnamed__"
            matrix.setdefault(key, []).append(c)
        return matrix

    # ── serialisation helpers ───────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialise the entire ledger to a JSON-compatible dict."""
        return {
            "sources": [s.as_dict() for s in self._sources.values()],
            "claims": [c.as_dict() for c in self._claims],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceLedger:
        """Reconstruct a ledger from a dict produced by :meth:`to_dict`."""
        return cls.from_records(
            sources=[
                EvidenceSource.from_dict(source)
                for source in data.get("sources", [])
            ],
            claims=[
                EvidenceClaim.from_dict(claim)
                for claim in data.get("claims", [])
            ],
        )

    @classmethod
    def from_records(
        cls,
        *,
        sources: list[EvidenceSource],
        claims: list[EvidenceClaim],
    ) -> EvidenceLedger:
        """Hydrate a read-only projection without invoking public mutators."""
        ledger = cls()
        ledger._sources = {source.source_id: source for source in sources}
        ledger._claims = list(claims)
        return ledger


# ── Internal helpers ────────────────────────────────────────────────────────────


def _pick_highest_authority(
    claims: list[EvidenceClaim],
    sources: dict[str, EvidenceSource],
) -> EvidenceClaim:
    """Return the claim from the highest-authority source (lowest letter A–J).

    If multiple claims share the same authority level, the first encountered
    is returned.
    """
    authority_order = {letter: idx for idx, letter in enumerate("ABCDEFGHIJ")}

    def _authority_index(claim: EvidenceClaim) -> int:
        src = sources.get(claim.source_id)
        if src is None:
            return 99  # unknown source → lowest priority
        return authority_order.get(src.source_class.upper(), 99)

    return min(claims, key=_authority_index)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


__all__ = [
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "SOURCE_CLASSES",
    "SOURCE_CLASS_LETTERS",
    "EvidenceSource",
    "EvidenceClaim",
    "ContradictionReport",
    "EvidenceLedger",
]
