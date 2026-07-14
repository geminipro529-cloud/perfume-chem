"""Fuckup detector — checks new formulas against known failure patterns.

Run this BEFORE mixing. It cross-references a formula's materials, doses, and
intended character against every pattern learned from historical fuckups.

The detector is intentionally aggressive: false positives (flagging something
that's actually fine) are cheaper than false negatives (missing a repeat fuckup).
"""

from __future__ import annotations

from typing import Any, Mapping

from engine.name_utils import normalize_name

from .models import DetectionWarning
from .patterns import (
    MaterialRule,
    CombinationRule,
    DoseRule,
    get_all_material_rules,
    get_all_combination_rules,
    get_all_dose_rules,
)


class FuckupDetector:
    """Scans a formula draft against all known failure patterns."""

    def __init__(self) -> None:
        self._material_rules = get_all_material_rules()
        self._combination_rules = get_all_combination_rules()
        self._dose_rules = get_all_dose_rules()

    def scan(
        self,
        materials: Mapping[str, float],
        dilutions: Mapping[str, float] | None = None,
        intended_character: str = "",
        target_family: str = "",
        active_doses: Mapping[str, float] | None = None,
        oav_data: Mapping[str, float] | None = None,
    ) -> list[DetectionWarning]:
        """Run all detection rules against a formula draft.

        Args:
            materials: {material_name: raw_dose_ul}
            dilutions: {material_name: dilution_pct} (e.g. 10 for 10%, 100 for neat)
            intended_character: free-text description of what the formula is supposed to be
            target_family: fragrance family (e.g. 'fruity_chypre', 'aromatic_fougere')
            active_doses: {material_name: active_ul} for active-dose rules
            oav_data: {material_name: oav} for OAV-based rules

        Returns:
            List of DetectionWarning objects. Empty list = clean.
        """
        warnings: list[DetectionWarning] = []

        # Normalize all material names for matching
        norm_materials: dict[str, float] = {}
        for name, dose in materials.items():
            norm_materials[normalize_name(name)] = dose

        norm_active: dict[str, float] = {}
        if active_doses:
            for name, dose in active_doses.items():
                norm_active[normalize_name(name)] = dose

        norm_oav: dict[str, float] = {}
        if oav_data:
            for name, oav in oav_data.items():
                norm_oav[normalize_name(name)] = oav

        # Build context keywords from intended character + target family
        context_keywords = self._build_context(intended_character, target_family)

        # --- Phase 1: Single-material out-of-context rules ---
        for rule in self._material_rules:
            for rule_name in rule.material_names:
                norm_rule = normalize_name(rule_name)
                if norm_rule not in norm_materials:
                    continue

                dose = norm_materials[norm_rule]
                active = norm_active.get(norm_rule, 0)
                oav = norm_oav.get(norm_rule, 0)

                # Check dose threshold
                if rule.dose_threshold_ul > 0 and dose < rule.dose_threshold_ul:
                    continue
                if rule.active_threshold_ul > 0 and active < rule.active_threshold_ul:
                    continue
                if rule.oav_threshold > 0 and oav < rule.oav_threshold:
                    continue

                # Check context restrictions
                if self._context_matches(rule.forbidden_in_contexts, context_keywords):
                    warnings.append(
                        DetectionWarning(
                            pattern_name=f"{rule_name.title()} in wrong context",
                            severity="high",
                            matched_rule=rule.reason,
                            violated_by=(rule_name,),
                            fuckup_reference="cassis_iris_smoke_2026-07-05",
                            recommendation=self._format_recommendation(rule_name, rule),
                        )
                    )
                    continue

                # Check forbidden-when-present co-occurrence
                if rule.forbidden_when_present:
                    for forbidden in rule.forbidden_when_present:
                        if normalize_name(forbidden) in norm_materials:
                            warnings.append(
                                DetectionWarning(
                                    pattern_name=f"{rule_name.title()} co-occurs with {forbidden}",
                                    severity="moderate",
                                    matched_rule=rule.reason,
                                    violated_by=(rule_name, forbidden),
                                    fuckup_reference="cassis_iris_smoke_2026-07-05",
                                    recommendation=self._format_recommendation(
                                        rule_name, rule
                                    ),
                                )
                            )
                            break

                # Check family restrictions
                if rule.forbidden_in_families:
                    if target_family.lower() in {
                        f.lower() for f in rule.forbidden_in_families
                    }:
                        warnings.append(
                            DetectionWarning(
                                pattern_name=f"{rule_name.title()} in {target_family} family",
                                severity="high",
                                matched_rule=rule.reason,
                                violated_by=(rule_name,),
                                fuckup_reference="cassis_iris_smoke_2026-07-05",
                                recommendation=self._format_recommendation(
                                    rule_name, rule
                                ),
                            )
                        )

        # --- Phase 2: Combination rules ---
        for rule in self._combination_rules:
            matched: set[str] = set()
            for mat in rule.materials:
                norm_mat = normalize_name(mat)
                if norm_mat in norm_materials:
                    matched.add(norm_mat)

            min_needed = rule.min_count if rule.min_count > 0 else len(rule.materials)
            if len(matched) < min_needed:
                continue

            # Check context
            if rule.context and not self._context_matches(
                (rule.context,), context_keywords
            ):
                continue

            warnings.append(
                DetectionWarning(
                    pattern_name=rule.name,
                    severity=rule.severity,
                    matched_rule=rule.effect,
                    violated_by=tuple(matched),
                    fuckup_reference=rule.fuckup_reference,
                    recommendation=rule.recommendation,
                )
            )

        # --- Phase 3: Dose ceiling rules ---
        for rule in self._dose_rules:
            norm_mat = normalize_name(rule.material_name)
            if norm_mat not in norm_materials:
                continue

            dose = norm_materials[norm_mat]
            active = norm_active.get(norm_mat, 0)
            oav = norm_oav.get(norm_mat, 0)

            # Check context
            if rule.context and rule.context != "universal":
                if not self._context_matches((rule.context,), context_keywords):
                    continue

            violated = False
            detail = ""

            if rule.max_dose_ul > 0 and dose > rule.max_dose_ul:
                violated = True
                detail = f"dose {dose:.0f} µL exceeds ceiling {rule.max_dose_ul:.0f} µL"
            elif rule.max_active_ul > 0 and active > rule.max_active_ul:
                violated = True
                detail = f"active {active:.0f} µL exceeds ceiling {rule.max_active_ul:.0f} µL"
            elif rule.max_oav > 0 and oav > rule.max_oav:
                violated = True
                detail = f"OAV {oav:.0f} exceeds ceiling {rule.max_oav:.0f}"

            if violated:
                warnings.append(
                    DetectionWarning(
                        pattern_name=f"{rule.material_name.title()} overdosed",
                        severity=rule.severity,
                        matched_rule=f"{detail}. {rule.effect}",
                        violated_by=(rule.material_name,),
                        fuckup_reference=rule.fuckup_reference,
                        recommendation=rule.recommendation,
                    )
                )

        # Sort by severity: catastrophic > high > moderate > low
        severity_rank = {"catastrophic": 0, "high": 1, "moderate": 2, "low": 3}
        warnings.sort(key=lambda w: severity_rank.get(w.severity, 99))

        return warnings

    def _build_context(self, intended_character: str, target_family: str) -> list[str]:
        """Build a list of context keywords from formula metadata."""
        keywords: list[str] = []

        char_lower = intended_character.lower()
        family_lower = target_family.lower()

        # Detect whether formula claims Aventus DNA
        if any(
            word in char_lower
            for word in (
                "aventus",
                "aventus-adjacent",
                "aventus style",
                "aventus dna",
                "fruity chypre",
                "modern chypre",
                "pineapple",
                "birch tar",
            )
        ):
            keywords.append("aventus")

        # Detect whether formula is an iris fragrance
        if any(
            word in char_lower
            for word in (
                "iris",
                "orris",
                "violet",
                "ionone",
                "irone",
            )
        ):
            keywords.append("iris")

        # Detect whether formula is non-iris
        if "iris" not in keywords:
            keywords.append("non-iris")

        # Detect fougère / aromatic
        if any(
            word in char_lower
            for word in (
                "fougere",
                "fougère",
                "aromatic",
                "lavender",
                "fern",
            )
        ):
            keywords.append("fougere")

        # Detect oriental / gourmand
        if any(
            word in char_lower
            for word in (
                "oriental",
                "gourmand",
                "vanilla",
                "amber",
                "balsamic",
            )
        ):
            keywords.append("oriental")

        # Detect chypre
        if (
            any(
                word in char_lower
                for word in (
                    "chypre",
                    "oakmoss",
                    "mossy",
                )
            )
            or "aventus" in keywords
        ):
            keywords.append("chypre")

        # Detect woody
        if any(
            word in char_lower
            for word in (
                "woody",
                "cedar",
                "sandalwood",
                "vetiver",
            )
        ):
            keywords.append("woody")

        # Detect modern/transparent
        if any(
            word in char_lower
            for word in (
                "modern",
                "transparent",
                "skin scent",
                "molecular",
                "ellena",
            )
        ):
            keywords.append("modern")

        # Add family as keyword
        if family_lower:
            keywords.append(family_lower)

        return keywords

    @staticmethod
    def _context_matches(
        forbidden_contexts: tuple[str, ...], present_keywords: list[str]
    ) -> bool:
        """Check if any forbidden context keyword appears in present keywords.

        Handles negation: "non-iris" means "iris" must NOT be present.
        Uses word-boundary matching via set intersection on tokenized keywords.
        """
        import re

        for forbidden in forbidden_contexts:
            f_lower = forbidden.lower()

            # Normalize "non-X" / "non X" → "NEG:X" for tokenization
            normalized = re.sub(r"\bnon[-\s]+(\w+)", r"NEG:\1", f_lower)

            negated: set[str] = set()
            positive: set[str] = set()

            for token in normalized.replace("-", " ").split():
                token = token.strip()
                if not token:
                    continue
                if token.startswith("NEG:"):
                    negated.add(token[4:])  # strip "NEG:"
                else:
                    positive.add(token)

            kw_set = set(present_keywords)

            # If any negated word is present, this context does NOT match
            if negated and (negated & kw_set):
                continue

            # If positive words specified, at least one must be present
            if positive:
                if positive & kw_set:
                    return True
            # If no meaningful tokens extracted, do substring fallback
            elif any(kw in f_lower or f_lower in kw for kw in present_keywords):
                return True

        return False

    @staticmethod
    def _format_recommendation(material_name: str, rule: MaterialRule) -> str:
        """Generate a recommendation string for a material rule violation."""
        if rule.dose_threshold_ul > 0:
            return (
                f"Reduce {material_name} to ≤{rule.dose_threshold_ul} µL "
                f"or remove entirely in this context."
            )
        if rule.active_threshold_ul > 0:
            return (
                f"Reduce {material_name} active dose to ≤{rule.active_threshold_ul} µL "
                f"or remove entirely in this context."
            )
        return f"Remove {material_name} from this formula — it contradicts the intended character."


# Convenience function
def scan_formula(
    materials: Mapping[str, float],
    dilutions: Mapping[str, float] | None = None,
    intended_character: str = "",
    target_family: str = "",
    active_doses: Mapping[str, float] | None = None,
    oav_data: Mapping[str, float] | None = None,
) -> list[DetectionWarning]:
    """Scan a formula against all known failure patterns. Convenience wrapper.

    Returns empty list if clean, or list of DetectionWarning objects.
    """
    detector = FuckupDetector()
    return detector.scan(
        materials=materials,
        dilutions=dilutions,
        intended_character=intended_character,
        target_family=target_family,
        active_doses=active_doses,
        oav_data=oav_data,
    )
