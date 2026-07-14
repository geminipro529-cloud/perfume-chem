"""Shared material identity overrides for user-confirmed chemistry.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm, ODT in ppm/ppb, OAV = C/ODT (dimensionless).
- Every perceptibility claim must be backed by OAV.

This module is intentionally small and dependency-light so other parts of the
pipeline can import it without pulling in catalog generation or scoring code.

The goal is to keep a ground-truth mapping for labels that are ambiguous in
trade usage, especially the iris / orris stack.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any


_GREEK_MAP = str.maketrans({
    "α": "alpha",
    "β": "beta",
    "γ": "gamma",
    "δ": "delta",
    "’": "'",
})


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.translate(_GREEK_MAP)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("&", " and ").replace("/", " ")
    text = text.replace("*", " ")
    text = text.replace("—", " ").replace("–", " ").replace("-", " ")
    text = re.sub(r"\[[^\]]+\]\s*$", "", text)
    text = re.sub(r"\b\d+(?:\.\d+)?\s*%\b", " ", text)
    text = re.sub(r"\b\d+(?:\.\d+)?\s*(?:ml|ul|g)\b", " ", text)
    text = re.sub(r"\s*\([^)]*\)\s*$", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@dataclass(frozen=True)
class MaterialIdentity:
    """Ground-truth identity for one user-confirmed material."""

    label: str
    profile_name: str
    chemistry_name: str
    identity_key: str
    cas: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    note: str = ""

    def metadata(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "profile_name": self.profile_name,
            "chemistry_name": self.chemistry_name,
            "identity_key": self.identity_key,
            "cas": list(self.cas),
            "aliases": list(self.aliases),
            "note": self.note,
        }


_IRIS_IDENTITIES: tuple[MaterialIdentity, ...] = (
    MaterialIdentity(
        label="Alpha Irone",
        profile_name="Alpha Irone",
        chemistry_name="alpha-irone",
        identity_key="alpha irone",
        cas=("79-69-6", "28555-77-5"),
        aliases=("alpha-irone", "cis alpha irone", "cis-alpha-irone"),
        note="True orris identity / signature irone.",
    ),
    MaterialIdentity(
        label="Orivone",
        profile_name="Orivone",
        chemistry_name="orris hexanone",
        identity_key="orivone",
        cas=("16587-71-6",),
        aliases=("orris hexanone", "4-tert-pentylcyclohexanone", "4-tert-amylcyclohexanone", "isopentylcyclohexanone"),
        note="Buttery-metallic orris body.",
    ),
    MaterialIdentity(
        label="Alpha Isomethyl Ionone",
        profile_name="Alpha-Isomethyl Ionone",
        chemistry_name="alpha-isomethyl ionone",
        identity_key="alpha isomethyl ionone",
        cas=("127-51-5",),
        aliases=("aimi", "methyl ionone pure", "alpha-isomethyl ionone"),
        note="Powdery iris body; the user's AIMI and Methyl Ionone Pure labels resolve here.",
    ),
    MaterialIdentity(
        label="Ultralia",
        profile_name="Ultralia",
        chemistry_name="methyl ionone mixture",
        identity_key="ultralia",
        cas=("1335-46-2",),
        aliases=("iratia", "iralia", "isoraldeine"),
        note="Commercial methyl-ionone family material used as the airy iris halo.",
    ),
    MaterialIdentity(
        label="Irotyl",
        profile_name="Irotyl",
        chemistry_name="orris capronate / ethyl 2-ethylhexanoate",
        identity_key="irotyl",
        cas=("2983-37-1",),
        aliases=("orris capronate", "ethyl 2-ethylhexanoate"),
        note="Fresh dewy carroty-orris accent.",
    ),
    MaterialIdentity(
        label="Alpha Ionone",
        profile_name="Alpha Ionone",
        chemistry_name="alpha-ionone",
        identity_key="alpha ionone",
        cas=("127-41-3",),
        aliases=("alpha-ionone",),
        note="Bright violet lift.",
    ),
    MaterialIdentity(
        label="Beta Ionone",
        profile_name="Beta Ionone",
        chemistry_name="beta-ionone",
        identity_key="beta ionone",
        cas=("79-77-6",),
        aliases=("beta-ionone",),
        note="Darker woody-violet depth.",
    ),
    MaterialIdentity(
        label="Allyl Ionone (Cetone V)",
        profile_name="Allyl Ionone",
        chemistry_name="allyl-alpha-ionone",
        identity_key="allyl ionone",
        cas=("79-78-7",),
        aliases=("allyl ionone cetone v", "allyl ionone ketone v", "cetone v", "ketone v"),
        note="Warm woody-violet bridge.",
    ),
)


def _all_identities() -> tuple[MaterialIdentity, ...]:
    return _IRIS_IDENTITIES


_LOOKUP: dict[str, MaterialIdentity] = {}
for _identity in _IRIS_IDENTITIES:
    for _key in {
        _normalize_text(_identity.label),
        _normalize_text(_identity.profile_name),
        _normalize_text(_identity.chemistry_name),
        _normalize_text(_identity.identity_key),
        *(_normalize_text(alias) for alias in _identity.aliases),
        *(_normalize_text(cas) for cas in _identity.cas),
    }:
        if _key:
            _LOOKUP[_key] = _identity
del _identity, _key


def resolve_material_identity(name: str | None) -> MaterialIdentity | None:
    """Return the confirmed identity for a material label, alias, or CAS."""

    key = _normalize_text(name or "")
    if not key:
        return None
    if key in _LOOKUP:
        return _LOOKUP[key]
    for identity in _IRIS_IDENTITIES:
        if key == _normalize_text(identity.label):
            return identity
        if key == _normalize_text(identity.profile_name):
            return identity
        if key == _normalize_text(identity.identity_key):
            return identity
        if key == _normalize_text(identity.chemistry_name):
            return identity
    return None


def normalized_lookup(name: str | None) -> str | None:
    """Normalized key used for matching user labels to the override registry."""

    identity = resolve_material_identity(name)
    if identity is not None:
        return identity.identity_key
    key = _normalize_text(name or "")
    return key or None


def profile_canonical_name(name: str | None) -> str | None:
    """Return the canonical profile name used by the existing profile layer."""

    identity = resolve_material_identity(name)
    if identity is not None:
        return identity.profile_name
    key = _normalize_text(name or "")
    return key.title() if key else None


def catalog_identity_key(name: str | None) -> str | None:
    """Return the catalog grouping key for a material."""

    identity = resolve_material_identity(name)
    if identity is not None:
        return identity.identity_key
    key = _normalize_text(name or "")
    return key or None


def metadata(name: str | None) -> dict[str, Any] | None:
    """Return the override metadata payload for a material, if known."""

    identity = resolve_material_identity(name)
    if identity is None:
        return None
    return identity.metadata()


def cas_for(name: str | None) -> str | None:
    """Return the primary CAS number for a confirmed identity, if known."""

    identity = resolve_material_identity(name)
    if identity is None or not identity.cas:
        return None
    return identity.cas[0]


def known_aliases() -> dict[str, tuple[str, ...]]:
    """Return the alias map keyed by canonical identity key."""

    output: dict[str, tuple[str, ...]] = {}
    for identity in _IRIS_IDENTITIES:
        output[identity.identity_key] = identity.aliases
    return output
