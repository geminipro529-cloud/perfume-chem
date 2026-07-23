"""Synergy graph — weighted material interaction network.

Models pairwise and group synergies between materials as a graph where:
  - Nodes = materials (with fingerprint vectors)
  - Edges = synergy/clash weights between material pairs

Synergy sources (layered, highest confidence first):
  1. Expert-declared synergies from ingredient_intelligence.py
  2. Co-occurrence patterns from formula history (pattern_miner.py)
  3. Fingerprint-based similarity inference
  4. Chemical class interaction rules

Edge types:
  - SYNERGY: materials enhance each other (positive weight)
  - CLASH: materials fight or cancel each other (negative weight)
  - NEUTRAL: no significant interaction

Musk compatibility analysis:
  For any formula, identifies which musks from inventory would work,
  which would be too heavy, and which are missing from the mix.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from engine.fingerprint import (
    cosine_similarity,
    fingerprint_material,
)
from engine.ingredient_intelligence import (
    DIMENSIONS,
    get_all_profiles,
    get_profile,
)
from engine.name_utils import normalize_name
from engine.psychophysics import CROSS_ADAPTATION_GROUPS

# ═══════════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SynergyEdge:
    """A weighted edge between two materials."""
    material_a: str
    material_b: str
    weight: float          # -1.0 (hard clash) to +1.0 (perfect synergy)
    edge_type: str         # "synergy", "clash", "neutral"
    sources: list[str] = field(default_factory=list)  # why this edge exists
    confidence: float = 0.5  # 0-1 how certain we are

    @property
    def pair_key(self) -> tuple[str, str]:
        return tuple(sorted((self.material_a, self.material_b)))


@dataclass
class SynergyNode:
    """A material node in the synergy graph."""
    name: str
    note: str = "heart"
    role: str = "modifier"
    edges: dict[str, SynergyEdge] = field(default_factory=dict)  # keyed by other material name

    @property
    def synergy_partners(self) -> list[str]:
        return [name for name, edge in self.edges.items() if edge.weight > 0]

    @property
    def clash_partners(self) -> list[str]:
        return [name for name, edge in self.edges.items() if edge.weight < 0]

    @property
    def avg_synergy(self) -> float:
        positive = [e.weight for e in self.edges.values() if e.weight > 0]
        return sum(positive) / len(positive) if positive else 0.0


@dataclass
class SynergyStack:
    """A group of materials that synergize together as a unit."""
    name: str
    materials: list[str]
    total_synergy: float  # sum of pairwise synergies within the stack
    avg_synergy: float    # average pairwise synergy
    description: str = ""


@dataclass
class MuskCompatibility:
    """Musk compatibility analysis for a formula."""
    compatible: list[tuple[str, float, str]]     # (musk_name, score, reason)
    too_heavy: list[tuple[str, float, str]]       # (musk_name, score, reason)
    recommended: list[tuple[str, float, str]]     # (musk_name, score, reason)
    already_present: list[str]


# ═══════════════════════════════════════════════════════════════════════════════
# Chemical Class Interaction Rules
# ═══════════════════════════════════════════════════════════════════════════════

# Known interaction patterns between chemical/functional classes
_CLASS_INTERACTIONS: dict[tuple[str, str], float] = {
    # Strong positive synergies
    ("radiance", "fixative"): 0.7,    # Hedione + Benzyl Salicylate archetype
    ("radiance", "volume"): 0.6,      # Hedione + Iso E Super
    ("character", "fixative"): 0.5,   # Feature material + anchor
    ("character", "radiance"): 0.6,   # Feature material + amplifier
    ("modifier", "volume"): 0.4,      # Modifier textures + body
    ("bridge", "character"): 0.5,     # Bridge connects character materials
    ("trace", "volume"): 0.3,         # Trace detail over large volume
    ("trace", "fixative"): 0.3,       # Trace anchored by fixative

    # Weak/negative interactions
    ("trace", "trace"): -0.2,         # Two traces compete for attention
}

# Texture compatibility matrix
_TEXTURE_INTERACTIONS: dict[tuple[str, str], float] = {
    ("halo", "cocoon"): 0.6,          # Radiant halo over warm cocoon
    ("halo", "cushion"): 0.5,         # Halo lifted by cushion
    ("halo", "skin-effect"): 0.4,     # Intimate radiance
    ("lift", "cocoon"): 0.5,          # Top sparkle over base depth
    ("lift", "cushion"): 0.4,
    ("veil", "cocoon"): 0.5,          # Transparent layer over depth
    ("veil", "skin-effect"): 0.4,
    ("cushion", "cocoon"): 0.3,       # Soft on warm
    ("diffusion", "cocoon"): 0.4,     # Project from depth
    ("diffusion", "fixative"): 0.5,
    ("skin-effect", "cocoon"): 0.4,   # Intimate warmth

    # Same texture can indicate redundancy
    ("cocoon", "cocoon"): -0.1,
    ("cushion", "cushion"): -0.1,
}

# Musk classification by character
_MUSK_CLASSES = {
    "white_clean": ["Galaxolide", "Habanolide", "Zenolide", "Romandolide"],
    "warm_animalic": ["Ambrettolide", "Musk Ketone", "Macrolide"],
    "powdery": ["Ethylene Brassylate", "Musk Ketone", "Exaltolide"],
    "sheer_transparent": ["Habanolide", "Zenolide", "Romandolide"],
    "heavy_dense": ["Galaxolide", "Tonalide", "Exaltolide"],
}

# Formula archetypes that pair well with specific musk classes
_MUSK_AFFINITY = {
    "woody": {"white_clean": 0.8, "sheer_transparent": 0.7, "warm_animalic": 0.5, "heavy_dense": 0.3},
    "floral": {"white_clean": 0.9, "powdery": 0.7, "warm_animalic": 0.4, "heavy_dense": 0.4},
    "fresh": {"sheer_transparent": 0.9, "white_clean": 0.7, "powdery": 0.3, "heavy_dense": 0.1},
    "oriental": {"warm_animalic": 0.8, "powdery": 0.7, "heavy_dense": 0.6, "white_clean": 0.4},
    "green": {"sheer_transparent": 0.8, "white_clean": 0.6, "powdery": 0.3, "heavy_dense": 0.1},
    "smoky": {"warm_animalic": 0.7, "heavy_dense": 0.5, "white_clean": 0.3, "sheer_transparent": 0.2},
    "powdery": {"powdery": 0.8, "white_clean": 0.7, "warm_animalic": 0.5, "sheer_transparent": 0.4},
    "sweet": {"powdery": 0.6, "warm_animalic": 0.6, "white_clean": 0.5, "heavy_dense": 0.4},
}


# ═══════════════════════════════════════════════════════════════════════════════
# Synergy Graph Builder
# ═══════════════════════════════════════════════════════════════════════════════

class SynergyGraph:
    """Weighted material interaction graph."""

    def __init__(self):
        self.nodes: dict[str, SynergyNode] = {}
        self.edges: dict[tuple[str, str], SynergyEdge] = {}

    def build(self, material_names: list[str] | None = None) -> None:
        """Build the synergy graph from available data sources.

        If material_names is None, builds for all known materials.
        """
        all_profiles = get_all_profiles()
        names = material_names or list(all_profiles.keys())

        # Create nodes
        for name in names:
            profile = get_profile(name)
            if profile:
                self.nodes[name] = SynergyNode(
                    name=name, note=profile.note, role=profile.role,
                )

        # Layer 1: Expert-declared synergies (highest confidence)
        self._add_expert_synergies(names)

        # Layer 2: Expert-declared clashes
        self._add_expert_clashes(names)

        # Layer 3: Role-based interaction rules
        self._add_role_interactions(names)

        # Layer 4: Fingerprint similarity inference (lower confidence)
        self._add_fingerprint_synergies(names)

        # Layer 5: Cross-adaptation suppression (perceptual penalty)
        self._add_cross_adaptation_penalties(names)

    def _add_expert_synergies(self, names: list[str]) -> None:
        """Add edges from expert-declared synergy lists."""
        for name in names:
            profile = get_profile(name)
            if not profile or not profile.synergies:
                continue
            for partner in profile.synergies:
                if partner in self.nodes:
                    self._add_edge(name, partner, 0.8, "synergy",
                                   ["expert_declared"], confidence=0.9)

    def _add_expert_clashes(self, names: list[str]) -> None:
        """Add negative edges from expert-declared avoid lists."""
        for name in names:
            profile = get_profile(name)
            if not profile or not profile.avoid:
                continue
            for partner in profile.avoid:
                if partner in self.nodes:
                    self._add_edge(name, partner, -0.7, "clash",
                                   ["expert_declared"], confidence=0.9)

    def _add_role_interactions(self, names: list[str]) -> None:
        """Add edges based on functional role interaction rules."""
        for i, name_a in enumerate(names):
            profile_a = get_profile(name_a)
            if not profile_a:
                continue
            for name_b in names[i + 1:]:
                profile_b = get_profile(name_b)
                if not profile_b:
                    continue

                # Role interaction
                role_key = tuple(sorted((profile_a.role, profile_b.role)))
                role_weight = _CLASS_INTERACTIONS.get(role_key, 0.0)

                # Texture interaction
                if profile_a.texture and profile_b.texture:
                    tex_key = tuple(sorted((profile_a.texture, profile_b.texture)))
                    tex_weight = _TEXTURE_INTERACTIONS.get(tex_key, 0.0)
                else:
                    tex_weight = 0.0

                combined = (role_weight + tex_weight) / 2
                if abs(combined) > 0.05:
                    edge_type = "synergy" if combined > 0 else "clash"
                    key = tuple(sorted((name_a, name_b)))
                    # Only add if no expert edge exists already
                    if key not in self.edges:
                        self._add_edge(name_a, name_b, combined, edge_type,
                                       ["role_interaction"], confidence=0.5)

    def _add_fingerprint_synergies(self, names: list[str]) -> None:
        """Infer synergies from fingerprint similarity (complementary, not identical)."""
        fps = {name: fingerprint_material(name) for name in names}
        fps = {k: v for k, v in fps.items() if v is not None}

        for i, (name_a, fp_a) in enumerate(list(fps.items())):
            for name_b, fp_b in list(fps.items())[i + 1:]:
                key = tuple(sorted((name_a, name_b)))
                if key in self.edges:
                    continue  # Don't override higher-confidence edges

                sim = cosine_similarity(fp_a.vector, fp_b.vector)

                # Complementary materials (moderate similarity) synergize best
                # Too similar = redundancy, too different = clash potential
                if 0.3 <= sim <= 0.7:
                    weight = (sim - 0.3) * 0.5  # Scale to 0-0.2 range
                    self._add_edge(name_a, name_b, weight, "synergy",
                                   ["fingerprint_complementary"], confidence=0.3)
                elif sim > 0.9:
                    # Very similar = potential redundancy, mild negative
                    self._add_edge(name_a, name_b, -0.1, "neutral",
                                   ["fingerprint_redundant"], confidence=0.3)

    def _add_cross_adaptation_penalties(self, names: list[str]) -> None:
        """Apply cross-adaptation penalties for materials sharing receptor groups.

        Materials in the same cross-adaptation group compete for the same
        receptors — adapting to one reduces perception of the other.
        This applies a mild negative weight to the synergy edge.

        Penalty scales DOWN as group presence increases: intentional stacking
        (e.g. 4-musk chord, 5-wood palette) is a deliberate compositional
        choice, not a clash.  The perceptual cost is already scored in
        psychophysics/perceptual_clarity.  Here we only flag truly redundant
        overlap.
          2 present → -0.15 (normal pair, mild competition)
          3 present → -0.10 (intentional trio)
          4+ present → -0.05 (deliberate chord / palette)
        """
        from engine.name_utils import normalize_name
        names_norm = {normalize_name(n): n for n in names}
        for group_name, members in CROSS_ADAPTATION_GROUPS.items():
            present = []
            for m in members:
                matched = names_norm.get(normalize_name(m))
                if matched:
                    present.append(matched)
            if len(present) < 2:
                continue
            # Scale penalty by group size — larger chords are intentional
            if len(present) == 2:
                penalty = -0.15
            elif len(present) == 3:
                penalty = -0.10
            else:
                penalty = -0.05   # deliberate chord (4+ members)
            for i, name_a in enumerate(present):
                for name_b in present[i + 1:]:
                    key = tuple(sorted((name_a, name_b)))
                    existing = self.edges.get(key)
                    if existing:
                        new_weight = existing.weight + penalty
                        existing.weight = max(-1.0, new_weight)
                        existing.sources.append(f"cross_adapt_{group_name}")
                    else:
                        self._add_edge(
                            name_a, name_b, penalty, "neutral",
                            [f"cross_adapt_{group_name}"], confidence=0.6,
                        )

    def _add_edge(
        self,
        name_a: str,
        name_b: str,
        weight: float,
        edge_type: str,
        sources: list[str],
        confidence: float = 0.5,
    ) -> None:
        """Add or update an edge in the graph."""
        key = tuple(sorted((name_a, name_b)))

        if key in self.edges:
            existing = self.edges[key]
            # Higher-confidence source wins
            if confidence > existing.confidence:
                existing.weight = weight
                existing.edge_type = edge_type
                existing.confidence = confidence
            existing.sources.extend(s for s in sources if s not in existing.sources)
            return

        edge = SynergyEdge(
            material_a=key[0],
            material_b=key[1],
            weight=weight,
            edge_type=edge_type,
            sources=sources,
            confidence=confidence,
        )
        self.edges[key] = edge

        # Add to node adjacency
        if name_a in self.nodes:
            self.nodes[name_a].edges[name_b] = edge
        if name_b in self.nodes:
            self.nodes[name_b].edges[name_a] = edge

    # ── Query Methods ──

    def get_synergies(self, name: str, min_weight: float = 0.1) -> list[tuple[str, float]]:
        """Get all synergy partners for a material, sorted by weight."""
        node = self.nodes.get(name)
        if not node:
            return []
        pairs = [
            (partner, edge.weight)
            for partner, edge in node.edges.items()
            if edge.weight >= min_weight
        ]
        pairs.sort(key=lambda x: x[1], reverse=True)
        return pairs

    def get_clashes(self, name: str) -> list[tuple[str, float]]:
        """Get all clash partners for a material."""
        node = self.nodes.get(name)
        if not node:
            return []
        pairs = [
            (partner, edge.weight)
            for partner, edge in node.edges.items()
            if edge.weight < 0
        ]
        pairs.sort(key=lambda x: x[1])
        return pairs

    def pair_synergy(self, name_a: str, name_b: str) -> float:
        """Get synergy score between two specific materials."""
        key = tuple(sorted((name_a, name_b)))
        edge = self.edges.get(key)
        return edge.weight if edge else 0.0

    def formula_synergy_score(self, ingredients: list[str]) -> float:
        """Compute synergy score that doesn't penalise material count.

        Old method: average over C(n,2) pairs — dilutes toward 0 as n grows
        because most pairs have no edge (synergy=0).

        New method: average only over pairs that have a known edge (positive
        or negative).  This measures the *quality* of known interactions
        rather than punishing the formula for having pairs the knowledge
        graph simply hasn't characterised.  A 73-material formula with 200
        positive edges at avg 0.4 scores the same 0.4, not 0.4*200/2628.
        """
        total = 0.0
        edge_count = 0
        for i, a in enumerate(ingredients):
            for b in ingredients[i + 1:]:
                syn = self.pair_synergy(a, b)
                if syn != 0.0:       # only count characterised pairs
                    total += syn
                    edge_count += 1
        return total / edge_count if edge_count > 0 else 0.0

    def find_synergy_stacks(
        self,
        ingredients: list[str],
        min_stack_size: int = 3,
        min_avg_synergy: float = 0.2,
    ) -> list[SynergyStack]:
        """Identify groups of materials that mutually synergize within a formula.

        A stack is a subgroup where every pair has positive synergy above threshold.
        For large formulas (>20 ingredients), caps search at triplets to avoid
        combinatorial explosion — C(41,5) ≈ 750K is too slow in Python.
        """
        stacks = []
        n = len(ingredients)

        # Cap max stack size for large formulas to keep runtime reasonable.
        # C(20,5)=15K is fine; C(41,5)=750K hangs.
        if n > 20:
            max_stack = min_stack_size  # triplets only
        elif n > 12:
            max_stack = 4
        else:
            max_stack = 5

        # Check all possible subgroups of size min_stack_size to max_stack
        for size in range(min_stack_size, min(n + 1, max_stack + 1)):
            for start_combo in self._combinations(ingredients, size):
                # Check if all pairs in this group have positive synergy
                all_positive = True
                total_syn = 0.0
                pair_count = 0
                for i, a in enumerate(start_combo):
                    for b in start_combo[i + 1:]:
                        syn = self.pair_synergy(a, b)
                        if syn <= 0:
                            all_positive = False
                            break
                        total_syn += syn
                        pair_count += 1
                    if not all_positive:
                        break

                if all_positive and pair_count > 0:
                    avg = total_syn / pair_count
                    if avg >= min_avg_synergy:
                        # Determine stack character
                        dominant_dims = self._stack_character(start_combo)
                        desc = " + ".join(dominant_dims[:3]) if dominant_dims else ""
                        stacks.append(SynergyStack(
                            name=f"Stack({', '.join(start_combo)})",
                            materials=list(start_combo),
                            total_synergy=round(total_syn, 3),
                            avg_synergy=round(avg, 3),
                            description=desc,
                        ))

        # Deduplicate — keep largest stacks that subsume smaller ones
        stacks.sort(key=lambda s: (len(s.materials), s.avg_synergy), reverse=True)
        return stacks[:20]  # Cap at 20 to avoid explosion

    def _combinations(self, items: list[str], size: int):
        """Simple combination generator."""
        if size == 0:
            yield ()
            return
        for i, item in enumerate(items):
            for rest in self._combinations(items[i + 1:], size - 1):
                yield (item,) + rest

    def _stack_character(self, materials: Sequence[str]) -> list[str]:
        """Determine dominant character dimensions for a stack of materials."""
        dim_totals = {d: 0.0 for d in DIMENSIONS}
        count = 0
        for name in materials:
            profile = get_profile(name)
            if profile:
                for dim, val in profile.character.items():
                    dim_totals[dim] = dim_totals.get(dim, 0.0) + val
                count += 1
        if count == 0:
            return []
        dim_avgs = {d: v / count for d, v in dim_totals.items()}
        sorted_dims = sorted(dim_avgs.items(), key=lambda x: x[1], reverse=True)
        return [d for d, v in sorted_dims if v >= 3.0]

    # ── Musk Compatibility Analysis ──

    def analyze_musk_compatibility(
        self,
        formula_ingredients: dict[str, float],
    ) -> MuskCompatibility:
        """Analyze which musks work with a given formula.

        Returns compatibility scores for all musks in inventory.
        """
        all_profiles = get_all_profiles()
        all_musks = [
            name for name, p in all_profiles.items()
            if p and p.note == "base" and (
                "musk" in normalize_name(name) or
                p.role == "fixative" and any(
                    p.character.get(d, 0) > 0 for d in ["powdery", "animalic", "warmth"]
                ) and p.character.get("woody", 0) < 5
            )
        ]
        # Explicitly include known musks
        known_musks = {
            "Galaxolide", "Tonalide", "Habanolide", "Zenolide",
            "Romandolide", "Exaltolide", "Macrolide", "Musk Ketone",
            "Ethylene Brassylate", "Ambrettolide",
        }
        all_musks = list(set(all_musks) | {m for m in known_musks if m in all_profiles})

        # Determine formula character
        formula_character = self._formula_dominant_character(formula_ingredients)
        formula_total_mass = sum(formula_ingredients.values())
        existing_musk_mass = 0.0

        already_present = []
        for name in list(formula_ingredients.keys()):
            if name in all_musks:
                already_present.append(name)
                existing_musk_mass += formula_ingredients[name]

        existing_musk_mass / formula_total_mass if formula_total_mass > 0 else 0

        compatible = []
        too_heavy = []
        recommended = []

        for musk in all_musks:
            if musk in already_present:
                continue

            profile = get_profile(musk)
            if not profile:
                continue

            # Score based on character match with formula
            score = 0.0
            reasons = []

            # 1. Synergy with existing ingredients
            synergy_total = 0.0
            synergy_count = 0
            for ingredient in formula_ingredients:
                syn = self.pair_synergy(musk, ingredient)
                if syn != 0:
                    synergy_total += syn
                    synergy_count += 1
            if synergy_count > 0:
                syn_avg = synergy_total / synergy_count
                score += syn_avg * 0.4
                if syn_avg > 0.3:
                    reasons.append(f"strong synergy with formula ({syn_avg:.2f})")

            # 2. Musk class affinity with formula archetype
            for archetype, affinities in _MUSK_AFFINITY.items():
                if formula_character.get(archetype, 0) > 4.0:
                    for musk_class, class_affinity in affinities.items():
                        if musk in _MUSK_CLASSES.get(musk_class, []):
                            score += class_affinity * 0.3 * (formula_character[archetype] / 10.0)
                            reasons.append(f"{musk_class} musk fits {archetype} character")

            # 3. Complementary vs redundant with existing musks
            for existing_musk in already_present:
                sim = self.pair_synergy(musk, existing_musk)
                if sim > 0.5:
                    score += 0.1
                    reasons.append(f"complements {existing_musk}")
                elif sim < -0.1:
                    score -= 0.2
                    reasons.append(f"clashes with {existing_musk}")

            # 4. Weight/density check — too heavy for formula?
            musk_profile = get_profile(musk)
            if musk_profile:
                heaviness = (
                    musk_profile.character.get("warmth", 0) +
                    musk_profile.character.get("sweetness", 0) +
                    musk_profile.character.get("animalic", 0)
                ) / 3.0

                formula_lightness = (
                    formula_character.get("freshness", 0) +
                    formula_character.get("green", 0)
                ) / 2.0

                if heaviness > 5.0 and formula_lightness > 5.0:
                    score -= 0.3
                    reasons.append("too heavy for this formula's fresh character")

            reason_str = "; ".join(reasons[:3]) if reasons else "no strong interaction"

            if score > 0.3:
                recommended.append((musk, round(score, 3), reason_str))
            elif score < -0.1:
                too_heavy.append((musk, round(score, 3), reason_str))
            else:
                compatible.append((musk, round(score, 3), reason_str))

        # Sort by score
        recommended.sort(key=lambda x: x[1], reverse=True)
        compatible.sort(key=lambda x: x[1], reverse=True)
        too_heavy.sort(key=lambda x: x[1])

        return MuskCompatibility(
            compatible=compatible,
            too_heavy=too_heavy,
            recommended=recommended,
            already_present=already_present,
        )

    def _formula_dominant_character(self, ingredients: dict[str, float]) -> dict[str, float]:
        """Compute weighted average character vector for a formula."""
        totals = {d: 0.0 for d in DIMENSIONS}
        total_mass = sum(ingredients.values())
        if total_mass <= 0:
            return totals

        for name, amount in ingredients.items():
            profile = get_profile(name)
            if not profile:
                continue
            weight = amount / total_mass
            for dim, val in profile.character.items():
                totals[dim] = totals.get(dim, 0.0) + val * weight

        return totals

    # ── Summary / Export ──

    def summary(self) -> dict:
        """Return graph statistics."""
        positive = sum(1 for e in self.edges.values() if e.weight > 0)
        negative = sum(1 for e in self.edges.values() if e.weight < 0)
        neutral = sum(1 for e in self.edges.values() if e.weight == 0)
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "synergy_edges": positive,
            "clash_edges": negative,
            "neutral_edges": neutral,
            "avg_synergy": round(
                sum(e.weight for e in self.edges.values() if e.weight > 0) / max(positive, 1),
                3,
            ),
        }
