"""When two stock records are one material, and when they can be one bottle.

The Stock page projection (``engine/personal_inventory.py``) and the Lab's "What's
missing" list (``engine/formulation_intelligence/hold_reasons.py``) both match a line of
Kenny's hand-kept ``inventory.txt`` to the gate's own stock list. They share these rules
so the two never disagree about whether a line and a record are the same bottle.

Read-only: nothing here changes a stock record.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from engine.name_utils import normalize_name

GOVERNANCE_DIR = Path(__file__).resolve().parents[1] / "data" / "governance"
OVERLAY_GLOB = "inventory_user_authority_overlay_*.json"
# Every dated overlay recording Kenny's own word carries this authority prefix.
USER_WORD_AUTHORITY = "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"
# How sure a match is; "probable" and "none" are never treated as the same material.
CONFIDENT_KINDS = frozenset({"alias", "identity", "name"})


def is_user_word(stock: Any) -> bool:
    """True for a record from one of Kenny's dated overlays (his own word on the bottle)."""

    return str(getattr(stock, "authority", "") or "").startswith(USER_WORD_AUTHORITY)


def overlay_aliases(directory: Path | None = None) -> dict[str, str]:
    """Each alias in Kenny's dated overlays, normalised, to its record's canonical name.

    Read again whenever an overlay file is added or changed, as the gate's own stock list is.
    """

    stamps = []
    for path in sorted((directory or GOVERNANCE_DIR).glob(OVERLAY_GLOB)):
        try:
            stamps.append((str(path), path.stat().st_mtime_ns))
        except OSError:
            continue
    return _overlay_aliases_from(tuple(stamps))


@lru_cache(maxsize=4)
def _overlay_aliases_from(stamps: tuple[tuple[str, int], ...]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for path_text, _stamp in stamps:
        path = Path(path_text)
        try:
            records = json.loads(path.read_text(encoding="utf-8")).get("records") or []
        except (OSError, ValueError, AttributeError):
            continue
        for record in records if isinstance(records, list) else []:
            canonical = str(record.get("canonical_name") or "") if isinstance(record, dict) else ""
            for alias in (record.get("aliases") or []) if canonical else []:
                key = normalize_name(str(alias))
                if key and key != normalize_name(canonical):
                    aliases[key] = canonical
    return aliases


def qualified(name: str) -> bool:
    """A name carrying a note in brackets other than its strength, form or CAS number ("Vetiver EO (Haiti)")."""

    notes = re.findall(r"\(([^)]*)\)|\[([^\]]*)\]", name)
    plain = r"\s*(neat|[\d.]+\s*%.*|\d{2,7}-\d{2}-\d|crystals?|powder|solid|liquid|as supplied)\s*"
    return any(not re.fullmatch(plain, round_note or square_note, re.IGNORECASE) for round_note, square_note in notes)


def base_key(name: str) -> str:
    """A name without notes in brackets or a strength: "Rosemary EO (French oil) (neat)" -> "rosemary eo"."""

    text = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", name)
    text = re.sub(r"\b\d+(?:\.\d+)?\s*%(?:\s*(?:w/w|v/v|w/v))?(?:\s+in\s+[\w+ ]+)?", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bneat\b", " ", text, flags=re.IGNORECASE)
    return normalize_name(text)


def twin_match(
    stock: Any, governed: Sequence[Any], aliases: Mapping[str, str] | None = None
) -> tuple[list[Any], str]:
    """The checks' owned stocks of the same material, and how sure the match is.

    The same material is one identity reached by Kenny's overlay alias ("alias"), by the
    same normalised identity ("identity"), or by the same name once notes in brackets and
    strengths are set aside ("name"). When only one of the two names carries such a note
    ("Cedarwood EO" and "Cedarwood EO (China)") the match is a guess ("probable"); when
    both do, they are never matched (so "Lavender EO (BONTAUX SAS)" never meets "Lavender
    EO (Bulgaria)"). Two or more identities make the match ambiguous, so none is claimed.
    """

    own = str(stock.identity_name or stock.name)
    own_keys = {normalize_name(own), normalize_name(str(stock.name))}
    alias_target = (overlay_aliases() if aliases is None else aliases).get(normalize_name(own))
    owned = [g for g in governed if str(g.status).casefold() == "owned"]
    by_alias = [
        g for g in owned
        if alias_target and normalize_name(alias_target) in {
            normalize_name(str(g.identity_name or g.name)), normalize_name(str(g.name)),
        }
    ]
    if by_alias:
        return by_alias, "alias"
    kind = "identity"
    same = [g for g in owned if normalize_name(str(g.identity_name or g.name)) in own_keys]
    if same and qualified(own) and not any(normalize_name(str(g.identity_name or g.name)) == normalize_name(own) for g in same):
        # Matched only by a display name without the note ("Tuberose Absolute" for
        # "Tuberose Absolute (volume grade)"): another grade may be another material.
        kind = "probable"
    if not same:
        base = base_key(own)
        same = [
            g for g in owned
            if base and base_key(str(g.identity_name or g.name)) == base
            and not (qualified(own) and qualified(str(g.identity_name or g.name)))
        ]
        noted = qualified(own) or any(qualified(str(g.identity_name or g.name)) for g in same)
        kind = "probable" if noted else "name"
    identities = {normalize_name(str(g.identity_name or g.name)) for g in same}
    return (same, kind) if len(identities) == 1 else ([], "none")


_SOLVENT_ABBREVIATIONS = frozenset({"dpg", "dep", "ipm", "tec", "mct", "ipa", "tpm", "bb", "peg", "dmso"})


def carrier_text(carrier: str) -> str:
    """A solvent as written on a label: "ethanol + dep" -> "ethanol + DEP"."""

    return " ".join(
        word.upper() if word.casefold() in _SOLVENT_ABBREVIATIONS else word for word in str(carrier or "").split()
    )


def carrier_key(carrier: Any) -> str:
    """A solvent for comparing two records: "DPG w/w" and "dpg" are the same solvent."""

    text = re.sub(r"\b(w/w|v/v|w/v)\b", " ", str(carrier or "").casefold())
    text = " ".join(text.split())
    return "" if text in {"", "none", "neat", "-"} else text


# A starting-charge tincture's strength is a mass fraction as built; inventory.txt writes it as a plain %.
BASIS_KEYS = {
    "mass_fraction": "mass", "mass_fraction_starting_charge": "mass", "volume_fraction": "volume",
    "mass_per_volume": "mass_per_volume",
}


def same_form(one: Any, other: Any) -> bool:
    """Two records of one strength that can be one bottle: no solvent or basis that disagrees."""

    if float(one.dilution or 0) <= 0 or float(other.dilution or 0) <= 0:
        return False  # no strength written down on one side: nothing says they are one bottle
    if abs(float(one.dilution or 0) - 1.0) < 1e-9:
        return True
    carriers = {carrier_key(one.carrier), carrier_key(other.carrier)} - {""}
    bases = {BASIS_KEYS.get(str(one.fraction_basis or "")), BASIS_KEYS.get(str(other.fraction_basis or ""))} - {None}
    return len(carriers) <= 1 and len(bases) <= 1


def same_strength(one: Any, other: Any) -> bool:
    return abs(float(one.dilution or 0) - float(other.dilution or 0)) < 1e-9
