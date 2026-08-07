"""Functional accord graph for perfume formulation.

Materials are nodes; edges represent reinforcement, temporal handoff,
masking, contrast, accord membership, diffusion support, texture support,
and core-to-module relationships.

Provides graph construction, query, and export utilities plus heuristic
edge inference from material properties.
"""

from __future__ import annotations

import math
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════════
# Edge type constants
# ═══════════════════════════════════════════════════════════════════════════════

REINFORCEMENT = "reinforcement"
TEMPORAL_HANDOFF = "temporal_handoff"
MASKING = "masking"
CONTRAST = "contrast"
ACCORD_MEMBERSHIP = "accord_membership"
DIFFUSION_SUPPORT = "diffusion_support"
TEXTURE_SUPPORT = "texture_support"
CORE_TO_MODULE = "core_to_module"

_EDGE_TYPES: frozenset[str] = frozenset(
    {
        REINFORCEMENT,
        TEMPORAL_HANDOFF,
        MASKING,
        CONTRAST,
        ACCORD_MEMBERSHIP,
        DIFFUSION_SUPPORT,
        TEXTURE_SUPPORT,
        CORE_TO_MODULE,
    }
)

# ═══════════════════════════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class AccordNode:
    """A material node in the functional accord graph."""

    node_id: str
    material_name: str
    role: str
    note: str
    dose_ul: float
    active_ul: float
    vp_pa: float
    time_windows: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict representation."""
        return {
            "node_id": self.node_id,
            "material_name": self.material_name,
            "role": self.role,
            "note": self.note,
            "dose_ul": self.dose_ul,
            "active_ul": self.active_ul,
            "vp_pa": self.vp_pa,
            "time_windows": list(self.time_windows),
        }


@dataclass(frozen=True, slots=True)
class AccordEdge:
    """A directed edge between two accord nodes."""

    edge_id: str
    from_node: str
    to_node: str
    edge_type: str
    weight: float  # 0.0–1.0
    description: str

    def __post_init__(self) -> None:
        """Validate edge type and weight range."""
        if self.edge_type not in _EDGE_TYPES:
            msg = f"Unknown edge type {self.edge_type!r}. Must be one of {sorted(_EDGE_TYPES)}"
            raise ValueError(msg)
        if not 0.0 <= self.weight <= 1.0:
            msg = f"Edge weight must be in [0.0, 1.0], got {self.weight}"
            raise ValueError(msg)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict representation."""
        return {
            "edge_id": self.edge_id,
            "from_node": self.from_node,
            "to_node": self.to_node,
            "edge_type": self.edge_type,
            "weight": self.weight,
            "description": self.description,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Graph class
# ═══════════════════════════════════════════════════════════════════════════════


class AccordGraph:
    """Functional accord graph for perfume formulation.

    Nodes are materials; edges encode functional relationships such as
    reinforcement, temporal handoff, masking, contrast, accord membership,
    diffusion support, texture support, and core-to-module links.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, AccordNode] = {}
        self._edges: list[AccordEdge] = []
        self._adjacency: dict[str, set[str]] = defaultdict(set)

    # ── Mutation ──────────────────────────────────────────────────────────

    def add_node(self, node: AccordNode) -> None:
        """Add a node to the graph."""
        self._nodes[node.node_id] = node

    def add_edge(self, edge: AccordEdge) -> None:
        """Add a directed edge to the graph."""
        self._edges.append(edge)
        self._adjacency[edge.from_node].add(edge.to_node)

    # ── Query ─────────────────────────────────────────────────────────────

    @property
    def nodes(self) -> dict[str, AccordNode]:
        """Read-only view of all nodes keyed by node_id."""
        return dict(self._nodes)

    @property
    def edges(self) -> list[AccordEdge]:
        """Read-only view of all edges."""
        return list(self._edges)

    def get_node(self, node_id: str) -> AccordNode | None:
        """Look up a node by its id."""
        return self._nodes.get(node_id)

    def get_neighbors(self, node_id: str) -> set[str]:
        """Return the set of node_ids directly reachable from *node_id*."""
        return set(self._adjacency.get(node_id, set()))

    def get_edges_of_type(self, edge_type: str) -> list[AccordEdge]:
        """Return all edges matching *edge_type*."""
        if edge_type not in _EDGE_TYPES:
            msg = f"Unknown edge type {edge_type!r}"
            raise ValueError(msg)
        return [e for e in self._edges if e.edge_type == edge_type]

    # ── Path finding ──────────────────────────────────────────────────────

    def find_path(self, from_id: str, to_id: str) -> list[str] | None:
        """BFS shortest path from *from_id* to *to_id*.

        Returns a list of node_ids (including both endpoints) or None if
        no path exists.
        """
        if from_id not in self._nodes or to_id not in self._nodes:
            return None
        if from_id == to_id:
            return [from_id]

        visited: set[str] = {from_id}
        queue: deque[tuple[str, list[str]]] = deque()
        queue.append((from_id, [from_id]))

        while queue:
            current, path = queue.popleft()
            for neighbor in self._adjacency.get(current, set()):
                if neighbor == to_id:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return None

    # ── Centrality ────────────────────────────────────────────────────────

    def centrality(self, node_id: str) -> float:
        """Normalised degree centrality for *node_id*.

        Returns degree / max_degree, or 0.0 if the graph has no edges or
        the node does not exist.
        """
        if node_id not in self._nodes:
            return 0.0
        if not self._nodes:
            return 0.0

        degree = len(self._adjacency.get(node_id, set()))
        max_degree = max(
            (len(adj) for adj in self._adjacency.values()),
            default=0,
        )
        if max_degree == 0:
            return 0.0
        return degree / max_degree

    # ── Interface nodes ───────────────────────────────────────────────────

    def interface_nodes(self) -> list[AccordNode]:
        """Nodes that have edges to both top-tier and base-tier materials.

        A node is an interface node if it connects (via outgoing edges) to
        at least one material whose ``note`` is ``"top"`` and at least one
        whose ``note`` is ``"base"``.
        """
        results: list[AccordNode] = []
        for node_id, node in self._nodes.items():
            neighbors = self._adjacency.get(node_id, set())
            has_top = False
            has_base = False
            for nid in neighbors:
                neighbor = self._nodes.get(nid)
                if neighbor is None:
                    continue
                if neighbor.note == "top":
                    has_top = True
                elif neighbor.note == "base":
                    has_base = True
                if has_top and has_base:
                    results.append(node)
                    break
        return results

    # ── Temporal chain ────────────────────────────────────────────────────

    def temporal_chain(self, start_node_id: str) -> list[AccordNode]:
        """Follow TEMPORAL_HANDOFF edges from *start_node_id*.

        Returns the ordered list of nodes visited (including the start).
        Stops when no further TEMPORAL_HANDOFF edges exist from the
        current node.
        """
        chain: list[AccordNode] = []
        current = start_node_id
        visited: set[str] = set()

        while current is not None and current not in visited:
            node = self._nodes.get(current)
            if node is None:
                break
            visited.add(current)
            chain.append(node)

            # Find the next node via a TEMPORAL_HANDOFF edge
            next_id: str | None = None
            for edge in self._edges:
                if edge.from_node == current and edge.edge_type == TEMPORAL_HANDOFF:
                    next_id = edge.to_node
                    break
            current = next_id

        return chain

    # ── Export ─────────────────────────────────────────────────────────────

    def to_cytoscape(self) -> dict[str, list[dict[str, Any]]]:
        """Export graph for Cytoscape.js visualisation.

        Returns ``{"nodes": [...], "edges": [...]}`` where each element
        follows the Cytoscape.js element format.
        """
        cy_nodes: list[dict[str, Any]] = []
        for node in self._nodes.values():
            cy_nodes.append(
                {
                    "data": {
                        "id": node.node_id,
                        "material_name": node.material_name,
                        "role": node.role,
                        "note": node.note,
                        "dose_ul": node.dose_ul,
                        "active_ul": node.active_ul,
                        "vp_pa": node.vp_pa,
                        "time_windows": list(node.time_windows),
                    },
                }
            )

        cy_edges: list[dict[str, Any]] = []
        for edge in self._edges:
            cy_edges.append(
                {
                    "data": {
                        "id": edge.edge_id,
                        "source": edge.from_node,
                        "target": edge.to_node,
                        "edge_type": edge.edge_type,
                        "weight": edge.weight,
                        "description": edge.description,
                    },
                }
            )

        return {"nodes": cy_nodes, "edges": cy_edges}


# ═══════════════════════════════════════════════════════════════════════════════
# Heuristic graph builder
# ═══════════════════════════════════════════════════════════════════════════════

# ── Note-tier helpers ─────────────────────────────────────────────────────

_CITRUS_FRUIT_KEYWORDS: frozenset[str] = frozenset(
    {
        "citrus",
        "bergamot",
        "lemon",
        "grapefruit",
        "orange",
        "mandarin",
        "cedrat",
        "lime",
        "fruit",
        "berry",
        "cassis",
        "blackcurrant",
        "peach",
        "apple",
        "pineapple",
        "melon",
    }
)
_FLORAL_SPICE_KEYWORDS: frozenset[str] = frozenset(
    {
        "floral",
        "rose",
        "jasmine",
        "muguet",
        "lily",
        "violet",
        "iris",
        "gardenia",
        "tuberose",
        "ylang",
        "narcissus",
        "carnation",
        "spice",
        "cinnamon",
        "clove",
        "cardamom",
        "pepper",
        "saffron",
        "nutmeg",
        "ginger",
    }
)
_WOOD_MUSK_AMBER_KEYWORDS: frozenset[str] = frozenset(
    {
        "wood",
        "cedar",
        "sandalwood",
        "vetiver",
        "patchouli",
        "oakmoss",
        "musk",
        "amber",
        "labdanum",
        "benzoin",
        "vanilla",
        "coumarin",
        "tonka",
        "leather",
        "incense",
        "oud",
        "cashmeran",
    }
)

# ── Character-family heuristics ───────────────────────────────────────────

_CHARACTER_FAMILY_MAP: list[tuple[frozenset[str], str]] = [
    (_CITRUS_FRUIT_KEYWORDS, "citrus"),
    (_FLORAL_SPICE_KEYWORDS, "floral"),
    (_WOOD_MUSK_AMBER_KEYWORDS, "woody"),
]


def _infer_time_suggestion(note_name: str) -> str:
    """Infer time window from a note name."""
    lower = note_name.lower()
    for keywords, suggestion in [
        (_CITRUS_FRUIT_KEYWORDS, "opening"),
        (_FLORAL_SPICE_KEYWORDS, "heart"),
        (_WOOD_MUSK_AMBER_KEYWORDS, "drydown"),
    ]:
        if any(kw in lower for kw in keywords):
            return suggestion
    return "heart"


def _infer_character_family(note_name: str) -> str:
    """Infer character family from a note name."""
    lower = note_name.lower()
    for keywords, family in _CHARACTER_FAMILY_MAP:
        if any(kw in lower for kw in keywords):
            return family
    return "other"


def _vp_tier(vp_pa: float) -> str:
    """Classify a material's volatility tier from vapour pressure."""
    if vp_pa > 2.0:
        return "top"
    if vp_pa >= 0.1:
        return "heart"
    return "base"


def _complementary_roles(role_a: str, role_b: str) -> bool:
    """Return True if two roles are complementary (not the same)."""
    return role_a != role_b


def _shared_accord_keywords(note_a: str, note_b: str) -> bool:
    """Return True if two notes share accord-family keywords."""
    lower_a = note_a.lower()
    lower_b = note_b.lower()
    for group in (_CITRUS_FRUIT_KEYWORDS, _FLORAL_SPICE_KEYWORDS, _WOOD_MUSK_AMBER_KEYWORDS):
        a_match = any(kw in lower_a for kw in group)
        b_match = any(kw in lower_b for kw in group)
        if a_match and b_match:
            return True
    return False


def build_functional_graph(materials: list[dict[str, Any]]) -> AccordGraph:
    """Build a functional accord graph from a list of material dicts.

    Each dict must contain at minimum:
        ``name``, ``role``, ``note``, ``dose_ul``, ``vp_pa``, ``time_windows``

    Optional keys:
        ``active_ul`` (defaults to ``dose_ul``)

    Auto-creates edges based on heuristics:

    - **Same time window + complementary roles** → ``REINFORCEMENT``
    - **Adjacent time windows** → ``TEMPORAL_HANDOFF``
    - **Shared accord keywords** → ``ACCORD_MEMBERSHIP``
    - **Low VP structural + high VP character** → ``DIFFUSION_SUPPORT``
    - **Overlapping character dimensions** → ``REINFORCEMENT``
    """
    graph = AccordGraph()

    # ── Create nodes ──────────────────────────────────────────────────
    node_ids: dict[str, str] = {}
    for mat in materials:
        node_id = str(uuid.uuid4())
        node_ids[mat["name"]] = node_id

        node = AccordNode(
            node_id=node_id,
            material_name=mat["name"],
            role=mat.get("role", "modifier"),
            note=mat.get("note", "heart"),
            dose_ul=mat.get("dose_ul", 0.0),
            active_ul=mat.get("active_ul", mat.get("dose_ul", 0.0)),
            vp_pa=mat.get("vp_pa", 0.1),
            time_windows=tuple(mat.get("time_windows", [])),
        )
        graph.add_node(node)

    # ── Create edges via heuristics ───────────────────────────────────
    names = list(node_ids.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            name_a = names[i]
            name_b = names[j]
            id_a = node_ids[name_a]
            id_b = node_ids[name_b]

            mat_a = _as_dict(materials, name_a)
            mat_b = _as_dict(materials, name_b)

            tw_a: list[str] = mat_a.get("time_windows", [])
            tw_b: list[str] = mat_b.get("time_windows", [])
            role_a: str = mat_a.get("role", "modifier")
            role_b: str = mat_b.get("role", "modifier")
            note_a: str = mat_a.get("note", "heart")
            note_b: str = mat_b.get("note", "heart")
            vp_a: float = mat_a.get("vp_pa", 0.1)
            vp_b: float = mat_b.get("vp_pa", 0.1)

            edges_created: set[str] = set()

            # ── Same time window + complementary roles → REINFORCEMENT
            shared_tw = set(tw_a) & set(tw_b)
            if shared_tw and _complementary_roles(role_a, role_b):
                if REINFORCEMENT not in edges_created:
                    graph.add_edge(
                        AccordEdge(
                            edge_id=str(uuid.uuid4()),
                            from_node=id_a,
                            to_node=id_b,
                            edge_type=REINFORCEMENT,
                            weight=0.7,
                            description=(
                                f"Complementary roles ({role_a}/{role_b}) "
                                f"in shared time window {min(shared_tw)}"
                            ),
                        )
                    )
                    edges_created.add(REINFORCEMENT)

            # ── Adjacent time windows → TEMPORAL_HANDOFF
            _add_temporal_handoff(graph, id_a, id_b, tw_a, tw_b, edges_created)

            # ── Shared accord keywords → ACCORD_MEMBERSHIP
            if _shared_accord_keywords(note_a, note_b):
                if ACCORD_MEMBERSHIP not in edges_created:
                    graph.add_edge(
                        AccordEdge(
                            edge_id=str(uuid.uuid4()),
                            from_node=id_a,
                            to_node=id_b,
                            edge_type=ACCORD_MEMBERSHIP,
                            weight=0.6,
                            description=f"Shared accord character ({note_a}/{note_b})",
                        )
                    )
                    edges_created.add(ACCORD_MEMBERSHIP)

            # ── Low VP structural + high VP character → DIFFUSION_SUPPORT
            _add_diffusion_support(graph, id_a, id_b, vp_a, vp_b, role_a, role_b, edges_created)

            # ── Overlapping character dimensions → REINFORCEMENT
            if _overlapping_character(note_a, note_b):
                if REINFORCEMENT not in edges_created:
                    graph.add_edge(
                        AccordEdge(
                            edge_id=str(uuid.uuid4()),
                            from_node=id_a,
                            to_node=id_b,
                            edge_type=REINFORCEMENT,
                            weight=0.5,
                            description=(f"Overlapping character dimensions ({note_a}/{note_b})"),
                        )
                    )
                    edges_created.add(REINFORCEMENT)

    return graph


def _as_dict(materials: list[dict[str, Any]], name: str) -> dict[str, Any]:
    """Return the material dict for *name* from the materials list."""
    for m in materials:
        if m.get("name") == name:
            return m
    return {}


def _add_temporal_handoff(
    graph: AccordGraph,
    id_a: str,
    id_b: str,
    tw_a: list[str],
    tw_b: list[str],
    edges_created: set[str],
) -> None:
    """Add TEMPORAL_HANDOFF edges if time windows are adjacent."""
    time_order = ["opening", "top", "heart", "late_heart", "drydown"]
    for t_a in tw_a:
        for t_b in tw_b:
            if t_a in time_order and t_b in time_order:
                idx_a = time_order.index(t_a)
                idx_b = time_order.index(t_b)
                if abs(idx_a - idx_b) == 1:
                    if TEMPORAL_HANDOFF not in edges_created:
                        graph.add_edge(
                            AccordEdge(
                                edge_id=str(uuid.uuid4()),
                                from_node=id_a,
                                to_node=id_b,
                                edge_type=TEMPORAL_HANDOFF,
                                weight=0.8,
                                description=f"Temporal handoff {t_a} → {t_b}",
                            )
                        )
                        edges_created.add(TEMPORAL_HANDOFF)
                    return


def _add_diffusion_support(
    graph: AccordGraph,
    id_a: str,
    id_b: str,
    vp_a: float,
    vp_b: float,
    role_a: str,
    role_b: str,
    edges_created: set[str],
) -> None:
    """Add DIFFUSION_SUPPORT edge if one material is low-VP structural
    and the other is high-VP character."""
    structural_roles = {"fixative", "base", "bridge", "support"}
    character_roles = {"core", "character", "lift", "modifier", "top"}

    a_is_structural = role_a in structural_roles and vp_a < 0.1
    b_is_character = role_b in character_roles and vp_b > 2.0
    if a_is_structural and b_is_character:
        if DIFFUSION_SUPPORT not in edges_created:
            graph.add_edge(
                AccordEdge(
                    edge_id=str(uuid.uuid4()),
                    from_node=id_a,
                    to_node=id_b,
                    edge_type=DIFFUSION_SUPPORT,
                    weight=0.75,
                    description=(
                        f"Low-VP structural ({role_a}, {vp_a:.3f} Pa) "
                        f"supports high-VP character ({role_b}, {vp_b:.1f} Pa)"
                    ),
                )
            )
            edges_created.add(DIFFUSION_SUPPORT)
        return

    b_is_structural = role_b in structural_roles and vp_b < 0.1
    a_is_character = role_a in character_roles and vp_a > 2.0
    if b_is_structural and a_is_character:
        if DIFFUSION_SUPPORT not in edges_created:
            graph.add_edge(
                AccordEdge(
                    edge_id=str(uuid.uuid4()),
                    from_node=id_b,
                    to_node=id_a,
                    edge_type=DIFFUSION_SUPPORT,
                    weight=0.75,
                    description=(
                        f"Low-VP structural ({role_b}, {vp_b:.3f} Pa) "
                        f"supports high-VP character ({role_a}, {vp_a:.1f} Pa)"
                    ),
                )
            )
            edges_created.add(DIFFUSION_SUPPORT)


def _overlapping_character(note_a: str, note_b: str) -> bool:
    """Return True if two notes share character keywords."""
    return _shared_accord_keywords(note_a, note_b)


# ═══════════════════════════════════════════════════════════════════════════════
# Perceptual note decomposition
# ═══════════════════════════════════════════════════════════════════════════════


def decompose_perceptual_notes(notes_text: str) -> list[dict[str, str]]:
    """Parse a paragraph of official perfume notes into structured entries.

    Splits by commas, semicolons, and newlines.  For each note returns::

        {"note_name": str, "time_suggestion": str, "character_family": str}

    Time suggestion heuristics:
        citrus/fruit keywords → ``"opening"``
        floral/spice keywords → ``"heart"``
        wood/musk/amber keywords → ``"drydown"``
        otherwise → ``"heart"``

    Character family heuristics:
        citrus/fruit → ``"citrus"``
        floral/spice → ``"floral"``
        wood/musk/amber → ``"woody"``
        otherwise → ``"other"``
    """
    import re

    # Split on commas, semicolons, or newlines
    raw_parts = re.split(r"[,;\n]+", notes_text)
    results: list[dict[str, str]] = []

    for part in raw_parts:
        note_name = part.strip()
        if not note_name:
            continue

        results.append(
            {
                "note_name": note_name,
                "time_suggestion": _infer_time_suggestion(note_name),
                "character_family": _infer_character_family(note_name),
            }
        )

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Rich role vector
# ═══════════════════════════════════════════════════════════════════════════════


def rich_role_vector(
    material_name: str,
    role: str,
    note: str,
    dose_ul: float,
    vp_pa: float,
) -> dict[str, float]:
    """Compute a multi-dimensional role vector for a material.

    Returns a dict of 0–1 scores across these dimensions:

    **Texture dimensions**
        ``texture_diffusion`` — how well the material diffuses in air
        ``texture_tenacity`` — how long it persists on skin
        ``texture_cushion`` — volume / fullness contribution
        ``texture_lift`` — top-note radiance / sparkle

    **Temporal dimensions**
        ``temporal_top`` — strength as a top note
        ``temporal_heart`` — strength as a heart note
        ``temporal_base`` — strength as a base note

    **Functional dimensions**
        ``function_recognizer`` — recognisability / signature character
        ``function_interface`` — bridges between note tiers
        ``function_bridge`` — connects disparate accord sections
        ``function_volume`` — structural mass / fixative contribution

    At least 4 dimensions are always populated.
    """
    vector: dict[str, float] = {}

    # ── Texture dimensions ────────────────────────────────────────────
    # Diffusion: higher VP → better diffusion
    vp_clipped = max(vp_pa, 0.001)
    vector["texture_diffusion"] = min(1.0, math.log10(vp_clipped + 1.0) / 3.0)

    # Tenacity: lower VP → longer persistence
    vector["texture_tenacity"] = 1.0 - min(1.0, math.log10(vp_clipped + 1.0) / 4.0)

    # Cushion: fixative / base roles contribute volume
    cushion_roles = {"fixative", "base", "support", "bridge"}
    vector["texture_cushion"] = 0.7 if role in cushion_roles else 0.3

    # Lift: top / lift roles contribute sparkle
    lift_roles = {"lift", "top", "modifier", "core"}
    vector["texture_lift"] = 0.8 if role in lift_roles else 0.2

    # ── Temporal dimensions ───────────────────────────────────────────
    tier = _vp_tier(vp_pa)
    vector["temporal_top"] = 0.9 if tier == "top" else (0.3 if note == "top" else 0.1)
    vector["temporal_heart"] = 0.9 if tier == "heart" else (0.5 if note == "heart" else 0.2)
    vector["temporal_base"] = 0.9 if tier == "base" else (0.3 if note == "base" else 0.1)

    # ── Functional dimensions ─────────────────────────────────────────
    # Recognizer: core / character roles are most recognisable
    vector["function_recognizer"] = 0.85 if role in {"core", "character"} else 0.4

    # Interface: materials with moderate VP bridge tiers
    vector["function_interface"] = 0.7 if 0.05 <= vp_pa <= 2.0 else 0.2

    # Bridge: bridge role explicitly
    vector["function_bridge"] = 0.9 if role == "bridge" else 0.3

    # Volume: fixative / base roles contribute structural mass
    vector["function_volume"] = 0.8 if role in {"fixative", "base"} else 0.3

    # ── Dose adjustment ───────────────────────────────────────────────
    # Scale texture_cushion and function_volume by dose fraction
    # (assumes a typical max dose of 500 µL for normalisation)
    dose_fraction = min(1.0, dose_ul / 500.0)
    vector["texture_cushion"] = min(1.0, vector["texture_cushion"] * (0.5 + 0.5 * dose_fraction))
    vector["function_volume"] = min(1.0, vector["function_volume"] * (0.5 + 0.5 * dose_fraction))

    return vector


__all__ = [
    "ACCORD_MEMBERSHIP",
    "AccordEdge",
    "AccordGraph",
    "AccordNode",
    "CONTRAST",
    "CORE_TO_MODULE",
    "DIFFUSION_SUPPORT",
    "MASKING",
    "REINFORCEMENT",
    "TEMPORAL_HANDOFF",
    "TEXTURE_SUPPORT",
    "build_functional_graph",
    "decompose_perceptual_notes",
    "rich_role_vector",
]
