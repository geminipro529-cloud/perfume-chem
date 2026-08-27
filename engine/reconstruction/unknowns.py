"""Unknown/captive material handling for perfume reconstruction.

Ports UNKNOWN_CAPTIVE_HANDLING.md.  Unknown materials are NOT forced into
familiar catalog names — they remain as UNKNOWN_* nodes in the target.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════════
# UnknownNode
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class UnknownNode:
    """A single unknown or captive material node in a reconstruction target.

    Parameters
    ----------
    unknown_id : str
        Unique identifier, e.g. ``"UNKNOWN_RADIANT_MUGUET_01"``.
    description : str
        Olfactive description — what this material smells like.
    time_windows : tuple[str, ...]
        Ordered sequence of time windows in which the material appears
        (e.g. ``("opening", "top", "heart")``).
    analytical_ri : float | None
        Gas-chromatographic retention index (e.g. Kovats or linear).
    analytical_ions : tuple[str, ...]
        Qualifier ions from mass spectrometry, e.g. ``("m/z 136", "m/z 121")``.
    gco_intensity : str
        GC-O odor intensity descriptor — one of ``"weak"``, ``"moderate"``,
        ``"strong"``.
    functional_neighbors : tuple[str, ...]
        Materials in the formula that this unknown interacts with or sits
        alongside.
    amount_median : float
        Median dose in *amount_unit*.
    amount_p05 : float
        5th percentile dose in *amount_unit*.
    amount_p95 : float
        95th percentile dose in *amount_unit*.
    amount_unit : str
        Unit for the amount fields (default ``"uL"``).
    candidate_builds : tuple[str, ...]
        Possible functional reconstruction strategies, e.g.
        ``("muguet base + salicylate lift", "Lilybelle + Hedione")``.
    presence_probability : float
        Probability (0.0–1.0) that this unknown is actually present in the
        target formula.  Default 1.0.
    """

    unknown_id: str = ""
    description: str = ""
    time_windows: tuple[str, ...] = ()
    analytical_ri: float | None = None
    analytical_ions: tuple[str, ...] = ()
    gco_intensity: str = ""
    functional_neighbors: tuple[str, ...] = ()
    amount_median: float = 0.0
    amount_p05: float = 0.0
    amount_p95: float = 0.0
    amount_unit: str = "uL"
    candidate_builds: tuple[str, ...] = ()
    presence_probability: float = 1.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UnknownNode:
        return cls(
            unknown_id=str(data.get("unknown_id", "")),
            description=str(data.get("description", "")),
            time_windows=tuple(data.get("time_windows", ())),
            analytical_ri=data.get("analytical_ri"),
            analytical_ions=tuple(data.get("analytical_ions", ())),
            gco_intensity=str(data.get("gco_intensity", "")),
            functional_neighbors=tuple(data.get("functional_neighbors", ())),
            amount_median=float(data.get("amount_median", 0.0)),
            amount_p05=float(data.get("amount_p05", 0.0)),
            amount_p95=float(data.get("amount_p95", 0.0)),
            amount_unit=str(data.get("amount_unit", "uL")),
            candidate_builds=tuple(data.get("candidate_builds", ())),
            presence_probability=float(data.get("presence_probability", 1.0)),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        d: dict[str, Any] = {
            "unknown_id": self.unknown_id,
            "description": self.description,
            "time_windows": list(self.time_windows),
            "analytical_ri": self.analytical_ri,
            "analytical_ions": list(self.analytical_ions),
            "gco_intensity": self.gco_intensity,
            "functional_neighbors": list(self.functional_neighbors),
            "amount_median": round(float(self.amount_median), 4),
            "amount_p05": round(float(self.amount_p05), 4),
            "amount_p95": round(float(self.amount_p95), 4),
            "amount_unit": self.amount_unit,
            "candidate_builds": list(self.candidate_builds),
            "presence_probability": round(float(self.presence_probability), 4),
        }
        return d


# ═══════════════════════════════════════════════════════════════════════════════
# UnknownRegistry
# ═══════════════════════════════════════════════════════════════════════════════


class UnknownRegistry:
    """Registry of unknown/captive material nodes.

    Thread-safe for read operations; writes are single-threaded by convention.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, UnknownNode] = {}

    def register(self, node: UnknownNode) -> None:
        """Register an unknown node.

        Parameters
        ----------
        node : UnknownNode
            The node to register.  Its *unknown_id* must be non-empty and
            unique within this registry.

        Raises
        ------
        ValueError
            If *unknown_id* is empty or already registered.
        """
        if not node.unknown_id:
            raise ValueError("UnknownNode.unknown_id must be non-empty")
        if node.unknown_id in self._nodes:
            raise ValueError(f"Duplicate unknown_id: {node.unknown_id!r}")
        self._nodes[node.unknown_id] = node

    def get(self, unknown_id: str) -> UnknownNode | None:
        """Look up an unknown node by its identifier.

        Parameters
        ----------
        unknown_id : str
            The identifier to look up.

        Returns
        -------
        UnknownNode or None
        """
        return self._nodes.get(unknown_id)

    def list_all(self) -> list[UnknownNode]:
        """Return all registered unknown nodes.

        Returns
        -------
        list[UnknownNode]
            Nodes in insertion order.
        """
        return list(self._nodes.values())

    def list_by_window(self, window: str) -> list[UnknownNode]:
        """Return nodes whose *time_windows* include *window*.

        Parameters
        ----------
        window : str
            Time-window label to filter by (e.g. ``"heart"``).

        Returns
        -------
        list[UnknownNode]
            Matching nodes in insertion order.
        """
        return [node for node in self._nodes.values() if window in node.time_windows]

    def suggest_functional_build(self, unknown_id: str) -> str:
        """Return the best candidate build for an unknown node.

        The "best" candidate is the first entry in *candidate_builds*.
        Returns an empty string if the node is not found or has no
        candidates.

        Parameters
        ----------
        unknown_id : str
            The identifier to look up.

        Returns
        -------
        str
            The first candidate build, or ``""``.
        """
        node = self._nodes.get(unknown_id)
        if node is None or not node.candidate_builds:
            return ""
        return node.candidate_builds[0]


# ═══════════════════════════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════════════════════════

_COUNTER: dict[str, int] = {}


def create_unknown_node(
    description: str,
    functional_neighbors: list[str],
    amount_range: tuple[float, float, float] = (0.0, 0.0, 0.0),
    time_windows: list[str] | None = None,
    candidate_builds: list[str] | None = None,
) -> UnknownNode:
    """Factory: build an ``UnknownNode`` with an auto-generated ID.

    The ID is generated as ``UNKNOWN_<DESCRIPTOR>_<counter>`` where
    *DESCRIPTOR* is derived from the first few words of *description*
    (uppercased, spaces replaced by underscores) and *counter* is a
    module-level monotonic counter per descriptor.

    Parameters
    ----------
    description : str
        Olfactive description — what this material smells like.
    functional_neighbors : list[str]
        Materials it interacts with.
    amount_range : tuple[float, float, float]
        Three-element tuple ``(p05, median, p95)``.  Default ``(0, 0, 0)``.
    time_windows : list[str] | None
        Time windows in which the material appears.  Default empty.
    candidate_builds : list[str] | None
        Possible functional reconstruction strategies.  Default empty.

    Returns
    -------
    UnknownNode
    """
    # Build a descriptor from the first 3 words of description
    words = description.strip().upper().split()
    if not words:
        descriptor = "UNKNOWN"
    else:
        descriptor = "_".join(words[:3])

    global _COUNTER  # noqa: PLW0603
    _COUNTER[descriptor] = _COUNTER.get(descriptor, 0) + 1
    counter = _COUNTER[descriptor]

    unknown_id = f"UNKNOWN_{descriptor}_{counter:02d}"

    p05, median, p95 = amount_range

    return UnknownNode(
        unknown_id=unknown_id,
        description=description,
        time_windows=tuple(time_windows or ()),
        analytical_ri=None,
        analytical_ions=(),
        gco_intensity="",
        functional_neighbors=tuple(functional_neighbors),
        amount_median=median,
        amount_p05=p05,
        amount_p95=p95,
        amount_unit="uL",
        candidate_builds=tuple(candidate_builds or ()),
        presence_probability=1.0,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Chassis classification
# ═══════════════════════════════════════════════════════════════════════════════


def chassis_classify_unknown(
    node: UnknownNode,
    is_central_bridge: bool = False,
    is_persistent_family_marker: bool = False,
    is_shared_across_flankers: bool = False,
    is_required_by_omission: bool = False,
) -> str:
    """Classify an unknown node for chassis placement.

    Returns ``"UNKNOWN_PROTECTED"`` if *any* of the boolean flags is
    ``True`` — the node must stay in the core chassis and cannot be
    moved to a module socket.  Returns ``"UNKNOWN_MODULE_CANDIDATE"``
    otherwise — the node *may* enter a socket.

    Parameters
    ----------
    node : UnknownNode
        The node to classify (used for logging / future heuristics).
    is_central_bridge : bool
        True if this unknown bridges two structural sections.
    is_persistent_family_marker : bool
        True if this unknown is a persistent marker of the fragrance
        family across flankers.
    is_shared_across_flankers : bool
        True if this unknown appears in multiple flankers of the same
        line.
    is_required_by_omission : bool
        True if omitting this unknown breaks the recognisable character
        of the target.

    Returns
    -------
    str
        ``"UNKNOWN_PROTECTED"`` or ``"UNKNOWN_MODULE_CANDIDATE"``.
    """
    if any(
        [
            is_central_bridge,
            is_persistent_family_marker,
            is_shared_across_flankers,
            is_required_by_omission,
        ]
    ):
        return "UNKNOWN_PROTECTED"
    return "UNKNOWN_MODULE_CANDIDATE"


# ═══════════════════════════════════════════════════════════════════════════════
# Evidence checklist
# ═══════════════════════════════════════════════════════════════════════════════

_EVIDENCE_CHECKLIST: list[str] = [
    "Authentic standard comparison",
    "Co-injection with known reference",
    "Dual-column retention index verification",
    "High-resolution mass spectrometry",
    "GC-O alignment with known odor events",
    "Supplier disclosure or technical dossier",
    "Authenticated formula evidence",
]


def evidence_needed_to_resolve(node: UnknownNode) -> list[str]:
    """Return the evidence checklist for resolving an unknown node.

    Every unknown requires the same set of evidence types to be
    considered resolved.  The *node* parameter is accepted for future
    extension (e.g. returning a subset based on node properties).

    Parameters
    ----------
    node : UnknownNode
        The node to resolve (currently unused, reserved for future
        heuristics).

    Returns
    -------
    list[str]
        Ordered list of evidence descriptions.
    """
    return list(_EVIDENCE_CHECKLIST)


__all__ = [
    "UnknownNode",
    "UnknownRegistry",
    "chassis_classify_unknown",
    "create_unknown_node",
    "evidence_needed_to_resolve",
]
