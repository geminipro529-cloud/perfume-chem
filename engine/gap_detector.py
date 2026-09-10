"""Knowledge gap detection and prioritization.

Implements Perplexity recommendation: "The system automatically identifies
and quantifies its own knowledge gaps" — inspired by pharma CADD
applicability-domain analysis.

Detects:
  - Materials referenced in rules but missing from material_properties
  - Partial profiles (MW but no VP, CLP, ODT)
  - Under-represented SAR classes (<3 materials)
  - Uncharted odor families (no synergy rules)
  - Theory framework roles with no assigned materials
  - Overall data quality score

Prioritizes gaps by impact: "If we knew X, it would unlock Y% more formulas."
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from engine.ingredient_intelligence import get_all_profiles
from engine.optimizer.models import (
    _lookup_material,
    get_materials_db,
    get_pairing_rules,
    get_synergy_rules,
    get_theory_rules,
    material_jellinek_quadrant_key,
    material_roudnitska_roles,
)


@dataclass
class Gap:
    """A single knowledge gap."""
    category: str       # "missing_material", "partial_profile", etc.
    severity: str       # "critical", "high", "medium", "low"
    description: str
    impact_score: float  # 0-100: how much fixing this would help
    resolution_hint: str  # What to do about it


@dataclass
class GapReport:
    """Full gap analysis report."""
    gaps: list[Gap] = field(default_factory=list)
    data_quality_score: float = 0.0  # 0-100 overall health
    stats: dict = field(default_factory=dict)
    synergistic_fillers: list[dict] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for g in self.gaps if g.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for g in self.gaps if g.severity == "high")


# Fields considered important for a "complete" material profile
IMPORTANT_FIELDS = [
    "mw", "bp", "vp", "clp", "odt",
    "odor_family", "odor_profile", "sar_class",
    "carles_position", "roudnitska_function", "jellinek_quadrant",
]

_ABSTRACT_RULE_TERMS = {
    "musks", "florals", "woods", "citrus", "amber", "rose", "jasmine",
    "bergamot", "vanilla", "vetiver", "cedarwood", "patchouli", "lavender",
    "other ionones", "iris materials", "powdery accords", "marine notes",
    "dirty animalics", "heavy musks", "floral bouquets", "oxygen", "iris",
    "animalic", "heavy_oriental_base", "aldehydes", "everything",
    "everything — universal enhancer", "everything — invisible additive",
    "everything — the universal citrus top", "everything. musks", "radiance",
    "structure", "transparency", "volume", "duo", "amplify", "clean duo",
    "amine", "amines", "ester", "phenol", "marine", "moisture",
    "oxygen+light", "alkaline water", "base", "fresh_green",
    "resinous_base", "clean_base", "aquatic_base",
}

_SAR_LOW_VALUE_HINTS = (
    "functional",
    "accord",
    "complex",
    "family",
    "base",
    "blend",
    "pre-blended",
    "preblended",
    "solvent",
    "carrier",
    "diluent",
    "vehicle",
    "denaturant",
    "concentrate",
    "reconstitution",
    "reconstituted",
    "placeholder",
    "universal",
    "not an odorant",
    "natural ",
    "synthetic ",
    "analogues",
    "homologues",
    "derivatives",
)

_PROFILE_LOW_VALUE_HINTS = (
    "accord",
    "base",
    "blend",
    "core",
    "fo",
    "f.o.",
    "pre-blended",
    "preblended",
)


class GapDetector:
    """Automatically detect and prioritize knowledge gaps."""

    def _is_supplemental_material(self, mat: dict) -> bool:
        return mat.get("source") in (
            "ingredient_intelligence_fallback",
            "ingredient_catalog",
        )

    def _normalize_sar_class(self, sar_class: str) -> str:
        text = str(sar_class).strip()
        if not text:
            return ""
        text = text.replace("–", "-").replace("—", "-").replace("−", "-")
        parts = re.split(r"\s+-\s+", text, maxsplit=1)
        if len(parts) > 1:
            text = parts[0]
        text = re.sub(r"\s*\([^)]*\)\s*$", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.lower().strip()

    def _is_low_value_sar_class(self, sar_class: str) -> bool:
        low = self._normalize_sar_class(sar_class)
        if not low:
            return True
        return any(hint in low for hint in _SAR_LOW_VALUE_HINTS)

    def _is_low_value_profile(self, mat: dict) -> bool:
        name = str(mat.get("name") or "").strip().lower()
        if not name:
            return False
        if any(hint in name for hint in _PROFILE_LOW_VALUE_HINTS):
            return True
        odor_profile = str(mat.get("odor_profile") or "").lower()
        if any(hint in odor_profile for hint in ("accord", "blend", "base")):
            return True
        return False

    def analyze(self, formula_materials: list[str] | None = None) -> GapReport:
        """Run full gap analysis across the knowledge graph.

        Args:
            formula_materials: Optional list of material names in the current
                formula. When provided, ``synergistic_fillers`` is populated
                with materials that both fill identified gaps and synergize
                with the existing palette.
        """
        report = GapReport()

        materials = get_materials_db()
        pairing_rules = get_pairing_rules()
        synergy_rules = get_synergy_rules()
        theory = get_theory_rules()

        # Collect all material names used in rules
        rule_materials = set()
        for r in pairing_rules:
            rule_materials.add(r["material_a"].lower().strip())
            b = r["material_b"].lower().strip()
            if not b.startswith("__"):
                rule_materials.add(b)
        for r in synergy_rules:
            rule_materials.add(r["material_a"].lower().strip())
            rule_materials.add(r["material_b"].lower().strip())

        known_materials = set(materials.keys())

        # 1. Missing materials (in rules but not in KG)
        self._detect_missing_materials(
            rule_materials, known_materials, pairing_rules,
            synergy_rules, report,
        )

        # 2. Partial profiles
        self._detect_partial_profiles(materials, report)

        # 3. Under-represented SAR classes
        self._detect_thin_sar_classes(materials, report)

        # 4. Uncharted odor families
        self._detect_uncharted_odors(
            materials, synergy_rules, report,
        )

        # 5. Theory framework gaps
        self._detect_theory_gaps(materials, theory, report)

        # 6. Compute overall data quality score
        report.data_quality_score = self._compute_quality_score(
            materials, rule_materials, known_materials, report,
        )

        # Sort gaps by impact_score (highest first)
        report.gaps.sort(key=lambda g: g.impact_score, reverse=True)

        # Populate synergistic fillers when formula context is available
        if formula_materials:
            gap_families = list({
                g.category for g in report.gaps
                if g.category and g.impact_score >= 5.0
            })
            report.synergistic_fillers = self.suggest_synergistic_fillers(
                formula_materials, gap_families or None
            )

        return report

    def suggest_synergistic_fillers(
        self,
        current_materials: list[str],
        gap_families: list[str] | None = None,
    ) -> list[dict]:
        """Suggest materials that fill gaps AND synergize with existing palette.

        Uses ingredient_intelligence synergy lists to find materials
        that both fill an olfactive gap and have declared synergies
        with materials already in the formula.

        Every suggestion carries ``gap_family_basis``. A basis of
        ``"character_evidence_unavailable"`` marks an unknown family
        question (no numeric character vector), not a negative verdict;
        ``"character"``/``"note"`` mark the evidence that matched.
        """
        existing_lower = {m.lower().strip() for m in current_materials}
        all_profiles = get_all_profiles()
        suggestions = []

        for name, profile in all_profiles.items():
            if name.lower().strip() in existing_lower:
                continue
            if not profile.synergies:
                continue

            # Count synergies with existing materials
            synergy_hits = [
                s for s in profile.synergies
                if s.lower().strip() in existing_lower
            ]
            if not synergy_hits:
                continue

            # Check if this material fills a gap family. Unavailable numeric
            # character evidence is unknown, never a negative judgment.
            family_match = True
            family_basis = "not_evaluated"
            if gap_families:
                numeric_character = profile.numeric_character
                character_available = numeric_character is not None
                mat_dims = {
                    dim.lower()
                    for dim, val in (numeric_character or {}).items()
                    if val >= 0.5
                }
                note_lower = (profile.note or "").lower()
                dim_match = any(f.lower() in mat_dims for f in gap_families)
                note_match = any(f.lower() in note_lower for f in gap_families)
                if dim_match:
                    family_match, family_basis = True, "character"
                elif note_match:
                    family_match, family_basis = True, "note"
                elif not character_available:
                    # No numeric vector: the family question is undecidable.
                    # Keep the candidate and label it unknown instead of
                    # silently treating it as a non-match.
                    family_match, family_basis = True, "character_evidence_unavailable"
                else:
                    family_match, family_basis = False, "no_evidence"

            if family_match:
                suggestions.append({
                    "material": name,
                    "synergy_partners": synergy_hits,
                    "synergy_count": len(synergy_hits),
                    "role": profile.role,
                    "note": profile.note,
                    "gap_family_basis": family_basis,
                    "character_evidence_status": profile.character_status.value,
                })

        suggestions.sort(key=lambda s: s["synergy_count"], reverse=True)
        return suggestions[:10]

    def _is_abstract_rule_reference(self, name: str) -> bool:
        low = name.lower().strip()
        if not low or low.startswith("__"):
            return True
        if low in _ABSTRACT_RULE_TERMS:
            return True
        if any(token in low for token in (" accords", " accord", " notes", " materials", " bouquets")):
            return True
        return False

    def _detect_missing_materials(
        self, rule_mats, known_mats, pairing_rules, synergy_rules, report
    ):
        orphans = set()
        for name in rule_mats - known_mats:
            if self._is_abstract_rule_reference(name):
                continue
            # Do not report shorthand/generic refs that already resolve to a concrete KG material.
            if _lookup_material(name) is not None:
                continue
            orphans.add(name)
        # Count how many rules reference each orphan
        ref_counts = Counter()
        for r in pairing_rules:
            a = r["material_a"].lower().strip()
            b = r["material_b"].lower().strip()
            if a in orphans:
                ref_counts[a] += 1
            if b in orphans:
                ref_counts[b] += 1
        for r in synergy_rules:
            a = r["material_a"].lower().strip()
            b = r["material_b"].lower().strip()
            if a in orphans:
                ref_counts[a] += 1
            if b in orphans:
                ref_counts[b] += 1

        report.stats["orphan_materials"] = len(orphans)

        # Top orphans by reference count
        for name, count in ref_counts.most_common(20):
            severity = "critical" if count >= 5 else "high" if count >= 2 else "medium"
            report.gaps.append(Gap(
                category="missing_material",
                severity=severity,
                description=(
                    f"'{name}' referenced in {count} rule(s) "
                    f"but missing from material_properties"
                ),
                impact_score=min(count * 15, 100),
                resolution_hint=(
                    f"Add '{name}' to material_properties.json "
                    f"with at least MW, VP, odor_family, carles_position"
                ),
            ))

    def _detect_partial_profiles(self, materials, report):
        partial_count = 0
        suppressed_count = 0
        seen = set()
        for key, mat in materials.items():
            name = mat.get("name", key)
            norm = name.upper().strip()
            if norm in seen:
                continue
            seen.add(norm)
            if self._is_supplemental_material(mat):
                continue
            if self._is_low_value_profile(mat):
                suppressed_count += 1
                continue

            missing = [f for f in IMPORTANT_FIELDS if mat.get(f) is None]
            completeness = 1 - len(missing) / len(IMPORTANT_FIELDS)

            if 0 < completeness < 0.7:
                partial_count += 1
                # Only report the worst ones
                if completeness < 0.4:
                    report.gaps.append(Gap(
                        category="partial_profile",
                        severity="high",
                        description=(
                            f"'{name}' is only "
                            f"{completeness * 100:.0f}% complete. "
                            f"Missing: {', '.join(missing[:5])}"
                        ),
                        impact_score=round((1 - completeness) * 60, 1),
                        resolution_hint=(
                            f"Add missing fields for '{name}': "
                            f"{', '.join(missing[:3])}"
                    ),
                ))

        report.stats["partial_profiles"] = partial_count
        report.stats["suppressed_partial_profiles"] = suppressed_count

    def _detect_thin_sar_classes(self, materials, report):
        sar_counts = Counter()
        representatives = {}
        suppressed = 0
        seen = set()
        for key, mat in materials.items():
            name = mat.get("name", key)
            norm = name.upper().strip()
            if norm in seen:
                continue
            seen.add(norm)
            if self._is_supplemental_material(mat):
                continue
            sc = mat.get("sar_class")
            if sc:
                canonical = self._normalize_sar_class(sc)
                if not canonical:
                    continue
                sar_counts[canonical] += 1
                representatives.setdefault(canonical, str(sc).strip())

        actionable = {
            cls: count
            for cls, count in sar_counts.items()
            if count == 2 and not self._is_low_value_sar_class(cls)
        }
        suppressed = sum(1 for cls, count in sar_counts.items() if count < 3) - len(actionable)
        report.stats["thin_sar_classes"] = len(actionable)
        report.stats["suppressed_thin_sar_classes"] = max(0, suppressed)
        report.stats["sar_class_buckets"] = len(sar_counts)

        for cls, count in sorted(actionable.items(), key=lambda x: (x[1], x[0])):
            label = representatives.get(cls, cls)
            report.gaps.append(Gap(
                category="thin_sar_class",
                severity="medium",
                description=(
                    f"SAR class '{label}' has only {count} material(s) — "
                    f"too few for reliable class-based predictions"
                ),
                impact_score=round((3 - count) * 20, 1),
                resolution_hint=(
                    f"Add more materials with sar_class='{label}' "
                    f"to improve class coverage"
                ),
            ))

    def _detect_uncharted_odors(self, materials, synergy_rules, report):
        # Odor families present in materials
        odor_families = set()
        seen = set()
        for key, mat in materials.items():
            name = mat.get("name", key)
            norm = name.upper().strip()
            if norm in seen:
                continue
            seen.add(norm)
            if self._is_supplemental_material(mat):
                continue
            of = mat.get("odor_family")
            if of:
                odor_families.add(of.lower().strip())

        # Odor families mentioned in synergy rules
        synergy_families = set()
        for r in synergy_rules:
            for k in ["material_a", "material_b"]:
                mat = materials.get(r[k].lower().strip())
                if mat and mat.get("odor_family"):
                    synergy_families.add(mat["odor_family"].lower().strip())

        uncharted = odor_families - synergy_families
        report.stats["uncharted_odor_families"] = len(uncharted)

        for fam in sorted(uncharted):
            report.gaps.append(Gap(
                category="uncharted_odor_family",
                severity="medium",
                description=(
                    f"Odor family '{fam}' has materials "
                    f"but no synergy rules — interactions unknown"
                ),
                impact_score=30,
                resolution_hint=(
                    f"Research synergy/conflict interactions for "
                    f"'{fam}' family materials"
                ),
            ))

    def _detect_theory_gaps(self, materials, theory, report):
        # Check Roudnitska roles coverage
        roud_roles = theory.get("roudnitska_roles", {}).get("roles", {})
        roles_with_materials = set()
        seen = set()
        for key, mat in materials.items():
            name = mat.get("name", key)
            norm = name.upper().strip()
            if norm in seen:
                continue
            seen.add(norm)
            if self._is_supplemental_material(mat):
                continue
            roles_with_materials.update(material_roudnitska_roles(name))

        empty_roles = set(roud_roles.keys()) - roles_with_materials
        report.stats["empty_roudnitska_roles"] = len(empty_roles)
        for role in empty_roles:
            report.gaps.append(Gap(
                category="empty_theory_role",
                severity="low",
                description=(
                    f"Roudnitska role '{role}' has no materials assigned"
                ),
                impact_score=15,
                resolution_hint=(
                    f"Assign roudnitska_function='{role}' to appropriate "
                    f"materials"
                ),
            ))

        # Check Jellinek quadrants
        jellinek = theory.get("jellinek_map", {}).get("quadrants", {})
        quads_with_materials = set()
        seen = set()
        for key, mat in materials.items():
            name = mat.get("name", key)
            norm = name.upper().strip()
            if norm in seen:
                continue
            seen.add(norm)
            if self._is_supplemental_material(mat):
                continue
            qk = material_jellinek_quadrant_key(name)
            if qk:
                quads_with_materials.add(qk)

        empty_quads = set(jellinek.keys()) - quads_with_materials
        report.stats["empty_jellinek_quadrants"] = len(empty_quads)

    def _compute_quality_score(
        self, materials, rule_mats, known_mats, report
    ) -> float:
        # Factors: material coverage, profile completeness, rule coverage
        if not rule_mats:
            return 50.0

        # 1. Material coverage (what % of rule-referenced mats exist?)
        coverage = len(known_mats & rule_mats) / len(rule_mats) * 100

        # 2. Average profile completeness
        completeness_scores = []
        seen = set()
        for key, mat in materials.items():
            name = mat.get("name", key)
            norm = name.upper().strip()
            if norm in seen:
                continue
            seen.add(norm)
            if self._is_supplemental_material(mat):
                continue
            filled = sum(
                1 for f in IMPORTANT_FIELDS if mat.get(f) is not None
            )
            completeness_scores.append(filled / len(IMPORTANT_FIELDS) * 100)

        avg_completeness = (
            sum(completeness_scores) / len(completeness_scores)
            if completeness_scores else 0
        )

        # 3. Gap severity penalty
        critical_penalty = report.critical_count * 5
        high_penalty = report.high_count * 2

        quality = (
            coverage * 0.4
            + avg_completeness * 0.4
            + max(0, 100 - critical_penalty - high_penalty) * 0.2
        )

        return round(min(100, max(0, quality)), 1)
