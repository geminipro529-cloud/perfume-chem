"""Recognizer scoring for chassis partition decisions.

Scores each material's importance to perfume identity and computes
mobility / anchor-floor values that drive core-vs-module allocation.
"""

from __future__ import annotations

from engine.domain_errors import ReconstructionInputError

# ═══════════════════════════════════════════════════════════════════════════════
# Core scoring
# ═══════════════════════════════════════════════════════════════════════════════


def recognizer_score(
    material_name: str,
    role: str,
    note: str,
    dose_ul: float,
    total_ul: float,
) -> float:
    """Compute how central a material is to the perfume's identity.

    Factors
    -------
    - **Role weight**: maps the material's functional role to a base
      importance score.
    - **Dose fraction bonus**: materials that occupy a larger share of
      the total formula are more likely to be identity-defining.

    Parameters
    ----------
    material_name : str
        Material name (informational, not used in scoring).
    role : str
        Functional role label (see the role-weight mapping).
    note : str
        Olfactive note (informational, not used in scoring).
    dose_ul : float
        Dose of this material in µL.
    total_ul : float
        Total formula volume in µL.

    Returns
    -------
    float
        Score in [0.0, 1.0].  Higher = more central to identity.
    """
    role_weights: dict[str, float] = {
        "character": 0.4,
        "signature": 0.5,
        "modifier": 0.2,
        "fixative": 0.15,
        "bridge": 0.1,
        "radiance": 0.25,
        "volume": 0.1,
        "trace": 0.05,
    }

    role_weight = role_weights.get(role, 0.1)

    dose_fraction = dose_ul / total_ul if total_ul > 0.0 else 0.0
    dose_bonus = dose_fraction * 0.3

    raw = role_weight + dose_bonus
    return max(0.0, min(1.0, raw))


def interface_centrality(
    material_name: str,
    connected_materials: list[str],
    total_materials: int,
) -> float:
    """Compute how central a material is in the accord interaction graph.

    A material that connects to many other materials is more central
    and harder to remove without disrupting the accord structure.

    Parameters
    ----------
    material_name : str
        Material name (informational, not used in scoring).
    connected_materials : list[str]
        List of other materials this material interacts with.
    total_materials : int
        Total number of materials in the formula.

    Returns
    -------
    float
        Centrality in [0.0, 1.0].  Higher = more connected.
    """
    if total_materials <= 1:
        return 0.0
    return len(connected_materials) / total_materials


def mobility_score(
    material_name: str,
    recognizer: float,
    centrality: float,
    is_signature: bool,
) -> float:
    """Compute how suitable a material is for the module socket.

    High mobility = good candidate to move to the module.
    Low mobility = must stay in the core.

    Formula::

        (1.0 - recognizer) * (1.0 - centrality) * (0.5 if is_signature else 1.0)

    Signature materials are penalised by 50 % because they are more
    tightly coupled to the perfume's identity even when their raw
    recognizer score is moderate.

    Parameters
    ----------
    material_name : str
        Material name (informational, not used in scoring).
    recognizer : float
        Recognizer score from ``recognizer_score()``.
    centrality : float
        Interface centrality from ``interface_centrality()``.
    is_signature : bool
        Whether this material is labelled as a signature material.

    Returns
    -------
    float
        Mobility score in [0.0, 1.0].  Higher = more mobile.
    """
    signature_penalty = 0.5 if is_signature else 1.0
    return (1.0 - recognizer) * (1.0 - centrality) * signature_penalty


def compute_anchor_floor(
    material_name: str,
    recognizer: float,
) -> float:
    """Compute the minimum fraction of a material's dose that must stay
    in the core.

    Higher recognizer scores demand a larger anchor floor.

    Thresholds
    ----------
    recognizer >= 0.8 : 0.90 (90 % must stay)
    recognizer >= 0.6 : 0.75
    recognizer >= 0.4 : 0.50
    recognizer >= 0.2 : 0.25
    else              : 0.10 (10 % floor minimum)

    Parameters
    ----------
    material_name : str
        Material name (informational, not used in scoring).
    recognizer : float
        Recognizer score from ``recognizer_score()``.

    Returns
    -------
    float
        Minimum fraction of the target dose that must remain in the core.
    """
    if recognizer >= 0.8:
        return 0.90
    if recognizer >= 0.6:
        return 0.75
    if recognizer >= 0.4:
        return 0.50
    if recognizer >= 0.2:
        return 0.25
    return 0.10


# ═══════════════════════════════════════════════════════════════════════════════
# Batch scoring
# ═══════════════════════════════════════════════════════════════════════════════


def score_all_materials(materials: list[dict]) -> list[dict]:
    """Score every material in a list and append recognizer, centrality,
    mobility, and anchor_floor fields.

    Parameters
    ----------
    materials : list[dict]
        Each dict must contain at least:
            ``name``, ``role``, ``note``, ``dose_ul``, ``connected_count``
        The total formula volume is inferred as the sum of all ``dose_ul``
        values.

    Returns
    -------
    list[dict]
        New dicts with the original keys plus:
            ``recognizer``, ``centrality``, ``mobility``, ``anchor_floor``
    """
    if not materials:
        raise ReconstructionInputError("recognizer material roster cannot be empty")

    total_ul = sum(m.get("dose_ul", 0.0) for m in materials)
    total_count = len(materials)

    results: list[dict] = []
    for m in materials:
        name = m.get("name", "")
        role = m.get("role", "")
        note = m.get("note", "")
        dose_ul = float(m.get("dose_ul", 0.0))
        connected_count = int(m.get("connected_count", 0))

        # Build a dummy connected list of the right length.
        connected = [""] * connected_count

        rec = recognizer_score(name, role, note, dose_ul, total_ul)
        cent = interface_centrality(name, connected, total_count)
        is_sig = role == "signature"
        mob = mobility_score(name, rec, cent, is_sig)
        floor = compute_anchor_floor(name, rec)

        entry = dict(m)
        entry["recognizer"] = round(rec, 4)
        entry["centrality"] = round(cent, 4)
        entry["mobility"] = round(mob, 4)
        entry["anchor_floor"] = round(floor, 4)
        results.append(entry)

    return results


__all__ = [
    "compute_anchor_floor",
    "interface_centrality",
    "mobility_score",
    "recognizer_score",
    "score_all_materials",
]
