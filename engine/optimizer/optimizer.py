"""Core optimizer: Carles grid search, constrained optimization, and suggestion engine."""

import re

from ..chemical_data_validator import is_blocked_chemical
from ..inventory_parser import inventory_names
from .models import (
    FormulaVector,
    ObjectiveWeights,
    OptimizationConstraints,
    OptimizationResult,
    _lookup_material,
    classify_note,
    find_missing_rule_partners,
    get_accord_library,
    get_theory_rules,
    material_identity_key,
    materials_match,
)
from .scoring import FormulaScorer

_SPECIFICITY_BONUS_TOKENS = (
    "absolute", "base", "fcf", "ftec", "oil", "resinoid", "super",
    "ambrofix", "orchid", "musk", "ionone", "irone", "jasmine",
    "rose", "vetiver", "sandal", "amber", "oud", "cedar", "iris",
)

_SUGGESTION_CONTEXTS = {
    "pre_mix": "pre_mix",
    "pre-mix": "pre_mix",
    "pre mix": "pre_mix",
    "post_mix": "post_mix",
    "post-mix": "post_mix",
    "post mix": "post_mix",
    "between_mix": "between_mix",
    "between-mix": "between_mix",
    "between mix": "between_mix",
}

_STYLE_ADDITIONS = {
    "classical": {
        "top": ("Bergamot FCF oil Sicilian", "Cedrat FCF oil Sicilian", "Aldehyde C10"),
        "heart": ("Hedione", "Nympheal", "Florol"),
        "base": ("Ambrox Super", "Benzoin Sumatra Resinoid", "Labdanum Absolute"),
    },
    "cologne": {
        "top": ("Bergamot FCF oil Sicilian", "Cedrat FCF oil Sicilian", "Aldehyde C10"),
        "heart": ("Hedione", "Neroli", "Orange Blossom"),
        "base": ("Ambrox Super", "Galaxolide", "Iso E Super"),
    },
    "skin_scent": {
        "top": ("Bergamot FCF oil Sicilian", "Aldehyde C10", "Linalool"),
        "heart": ("Hedione", "Florol", "Nympheal"),
        "base": ("Ambrox Super", "Galaxolide", "Habanolide"),
    },
    "oriental": {
        "top": ("Bergamot FCF oil Sicilian", "Cedrat FCF oil Sicilian", "Cardamom Oil"),
        "heart": ("Jasmine Absolute", "Rose Absolute", "Hedione"),
        "base": ("Benzoin Sumatra Resinoid", "Labdanum Absolute", "Vanillin"),
    },
    "soliflore": {
        "top": ("Bergamot FCF oil Sicilian", "Linalool", "Aldehyde C10"),
        "heart": ("Hedione", "Florol", "Peonile"),
        "base": ("Ambrox Super", "Musk Ketone", "Habanolide"),
    },
    "fougere": {
        "top": ("Bergamot FCF oil Sicilian", "Lavender Oil", "Aldehyde C10"),
        "heart": ("Coumarin 20%", "Linalool", "Hedione"),
        "base": ("Oakmoss Base", "Tonka Bean Absolute", "Ambrox Super"),
    },
    "chypre": {
        "top": ("Bergamot FCF oil Sicilian", "Cedrat FCF oil Sicilian", "Aldehyde C10"),
        "heart": ("Rose Absolute", "Patchouli EO", "Jasmine Absolute"),
        "base": ("Labdanum Absolute", "Patchouli EO", "Oakmoss Base"),
    },
}


def _load_inventory() -> list[str]:
    """Load available materials from inventory.txt."""
    return [
        name
        for name in inventory_names(
            unique=True,
            include_solvents=False,
            include_unavailable=False,
        )
        if not is_blocked_chemical(name)
    ]


def _specificity_score(name: str) -> tuple[int, int, str]:
    low = name.lower()
    token_count = len(re.findall(r"[a-z0-9]+", low))
    bonus = sum(1 for token in _SPECIFICITY_BONUS_TOKENS if token in low)
    return (token_count + bonus, len(low), low)


def _best_inventory_match(name: str, inventory: list[str]) -> str | None:
    matches = [item for item in inventory if materials_match(name, item)]
    if not matches:
        return None
    return max(matches, key=_specificity_score)


def _concrete_inventory_name(name: str, inventory: list[str]) -> str | None:
    """Resolve a theory/example label to the most concrete owned material."""
    match = _best_inventory_match(name, inventory)
    if match is not None:
        return match
    return name


def _normalize_suggestion_context(context: str | None) -> str:
    if context is None:
        return "pre_mix"
    normalized = context.strip().lower().replace("-", "_")
    return _SUGGESTION_CONTEXTS.get(normalized, "pre_mix")


def _unique_ordered(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        key = material_identity_key(item)
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def _owned_candidates(candidates: tuple[str, ...], inventory: list[str]) -> list[str]:
    owned = []
    for candidate in candidates:
        resolved = _best_inventory_match(candidate, inventory)
        if resolved is not None:
            owned.append(resolved)
    return _unique_ordered(owned)


def _prefix_for_context(context: str) -> str:
    if context == "post_mix":
        return "Post-mix add-only nudge"
    if context == "between_mix":
        return "Before the next remix"
    return "Pre-mix suggestion"


class FormulaOptimizer:
    """Multi-stage formula optimizer."""

    def __init__(self, weights: ObjectiveWeights | None = None,
                 constraints: OptimizationConstraints | None = None):
        self.scorer = FormulaScorer(weights)
        self.constraints = constraints or OptimizationConstraints()
        self._inventory: list[str] | None = None

    @property
    def inventory(self) -> list[str]:
        if self._inventory is None:
            self._inventory = _load_inventory()
        return self._inventory

    # ── Stage 1: Carles Grid Search (accord-library-based) ──

    def carles_grid_search(self, star_material: str,
                           n_results: int = 5) -> list[OptimizationResult]:
        """Carles method: trial the star material against library accords.

        Follows Jean Carles' method steps (theory_rules.json):
        1. Choose a characterizing material (star)
        2. Build from accord library (perfume_accord_library.txt)
        3. Trial star against each available accord
        4. Add note modifiers to fill pyramid gaps
        5. Rank by theory-first scoring

        Returns the top N formula candidates.
        """
        # Classify available materials by note
        tops, hearts, bases = [], [], []
        for name in self.inventory:
            note = classify_note(name)
            if note == "top":
                tops.append(name)
            elif note == "heart":
                hearts.append(name)
            else:
                bases.append(name)

        # Load accord library filtered to available inventory
        library_accords = self._load_library_accords()

        results = []
        star_note = classify_note(star_material)
        star_pct = {"top": 5.0, "heart": 10.0, "base": 8.0}.get(star_note, 8.0)

        for accord_name, accord_ings in library_accords:
            fv = FormulaVector()
            # Star material at Carles prominence percentage
            fv.ingredients[star_material] = star_pct

            # Add accord ingredients at library-defined ratios
            # Scale accord to ~50-60% of total formula weight
            accord_total = sum(accord_ings.values())
            target_pct = 55.0
            scale = target_pct / accord_total if accord_total > 0 else 1.0

            for mat, pct in accord_ings.items():
                if mat != star_material:
                    fv.ingredients[mat] = round(pct * scale, 1)

            # Fill pyramid gaps from inventory (Carles step 5: add modifiers)
            dist = fv.note_distribution()
            remaining = 100.0 - fv.total_pct

            if dist.get("heart", 0) < 25 and remaining > 5:
                for hmat in hearts:
                    if hmat not in fv.ingredients and hmat != star_material:
                        add = min(6.0, remaining / 2)
                        fv.ingredients[hmat] = round(add, 1)
                        remaining -= add
                        break

            if dist.get("top", 0) < 10 and remaining > 3:
                for tmat in tops:
                    if tmat not in fv.ingredients and tmat != star_material:
                        add = min(4.0, remaining / 2)
                        fv.ingredients[tmat] = round(add, 1)
                        remaining -= add
                        break

            scores = self.scorer.score(fv)
            results.append(OptimizationResult(
                formula=fv,
                scores=scores,
                total_score=scores["total"],
                suggestions=[],
                reasoning=[f"Carles grid: {star_material} × {accord_name}"],
            ))

        # Sort by total score descending
        results.sort(key=lambda r: r.total_score, reverse=True)
        return results[:n_results]

    def _load_library_accords(self) -> list[tuple[str, dict[str, float]]]:
        """Load accord library filtered to inventory-available materials.

        Returns accords where >= 60% of ingredients (by weight) are available.
        Falls back to keyword-based accords if library is empty.
        """
        library = get_accord_library()

        if not library:
            return self._generate_fallback_accords()

        accords = []
        for lib_accord in library:
            name = lib_accord["name"]
            available = {}
            total_original = sum(lib_accord["ingredients"].values())

            for mat_name, pct in lib_accord["ingredients"].items():
                # Strip dilution suffix: "Ambrox Super — 30%" → "Ambrox Super"
                clean = re.sub(r'\s*[\u2014\u2013-]\s*\d+%\s*$', '', mat_name).strip()
                # Match against inventory
                matched = None
                for inv_mat in self.inventory:
                    if materials_match(clean, inv_mat):
                        matched = inv_mat
                        break

                if matched:
                    available[matched] = pct

            total_available = sum(available.values())
            coverage = total_available / total_original if total_original > 0 else 0

            if coverage >= 0.6 and len(available) >= 3:
                # Rescale to maintain proportional ratios
                s = 100.0 / total_available if total_available > 0 else 1.0
                scaled = {k: round(v * s, 1) for k, v in available.items()}
                accords.append((name, scaled))

        return accords if accords else self._generate_fallback_accords()

    def _generate_fallback_accords(self) -> list[tuple[str, dict[str, float]]]:
        """Keyword-based accord generation when library is unavailable."""
        bases = [m for m in self.inventory if classify_note(m) == "base"]
        woody = [m for m in bases if any(w in m.lower() for w in
                 ["cedar", "sandal", "vetiver", "patchouli", "guaiac", "oud"])]
        amber = [m for m in bases if any(w in m.lower() for w in
                 ["amber", "labdanum", "benzoin", "vanill", "coumarin", "tonka"])]
        musk = [m for m in bases if any(w in m.lower() for w in
                ["musk", "galaxolide", "habanolide", "exaltolide", "cashmeran",
                 "iso e super", "ambrox"])]

        accords = []
        if woody:
            accords.append(("woody", {m: round(100 / len(woody[:3]), 1) for m in woody[:3]}))
        if amber:
            accords.append(("amber", {m: round(100 / len(amber[:3]), 1) for m in amber[:3]}))
        if musk:
            accords.append(("musk", {m: round(100 / len(musk[:3]), 1) for m in musk[:3]}))
        if woody and amber:
            combo = woody[:2] + amber[:1]
            accords.append(("woody-amber", {m: round(100 / len(combo), 1) for m in combo}))
        if not accords and bases:
            accords.append(("mixed-base", {m: round(100 / len(bases[:3]), 1) for m in bases[:3]}))

        return accords

    # ── Stage 2: Optimize existing formula ──

    def optimize(self, formula: FormulaVector) -> OptimizationResult:
        """Optimize an existing formula by iteratively trying improvements."""
        best_fv = FormulaVector(
            ingredients=dict(formula.ingredients),
            dilutions=dict(formula.dilutions),
        )
        best_scores = self.scorer.score(best_fv)
        best_total = best_scores["total"]
        reasoning = ["Starting optimization from provided formula"]

        # Try adjusting percentages
        for name in list(best_fv.ingredients.keys()):
            for delta in [2.0, -2.0, 5.0, -3.0]:
                test_fv = FormulaVector(
                    ingredients=dict(best_fv.ingredients),
                    dilutions=dict(best_fv.dilutions),
                )
                new_pct = test_fv.ingredients[name] + delta
                if 0.5 <= new_pct <= 40.0:
                    test_fv.ingredients[name] = new_pct
                    test_scores = self.scorer.score(test_fv)
                    if test_scores["total"] > best_total:
                        best_fv = test_fv
                        best_scores = test_scores
                        best_total = test_scores["total"]
                        reasoning.append(
                            f"Adjusted {name}: {delta:+.1f}% → total {best_total:.1f}"
                        )

        # Try adding materials from inventory that aren't in formula
        for candidate in self.inventory:
            if candidate in best_fv.ingredients:
                continue
            if len(best_fv.ingredients) >= self.constraints.max_ingredients:
                break
            test_fv = FormulaVector(
                ingredients=dict(best_fv.ingredients),
                dilutions=dict(best_fv.dilutions),
            )
            test_fv.ingredients[candidate] = 3.0
            test_scores = self.scorer.score(test_fv)
            if test_scores["total"] > best_total + 1.0:  # meaningful improvement
                best_fv = test_fv
                best_scores = test_scores
                best_total = test_scores["total"]
                reasoning.append(f"Added {candidate} at 3% → total {best_total:.1f}")

        suggestions = self.suggest(best_fv)

        return OptimizationResult(
            formula=best_fv,
            scores=best_scores,
            total_score=best_total,
            suggestions=suggestions,
            reasoning=reasoning,
        )

    # ── Stage 3: Suggestion Engine ──

    def suggest(
        self,
        fv: FormulaVector,
        context: str = "pre_mix",
        observations: dict | None = None,
    ) -> list[str]:
        """Generate improvement suggestions for a formula.

        Backward compatible with the legacy pre-mix behavior when no context
        is supplied. Use `context=` for post-mix or between-mix routing.
        """
        mode = _normalize_suggestion_context(context)
        if mode == "post_mix":
            return self._suggest_post_mix(fv, observations=observations)
        if mode == "between_mix":
            return self._suggest_between_mix(fv, observations=observations)
        return self._suggest_pre_mix(fv, observations=observations)

    def _suggest_pre_mix(
        self,
        fv: FormulaVector,
        observations: dict | None = None,
    ) -> list[str]:
        suggestions = []
        dist = fv.note_distribution()
        scores = self.scorer.score(fv)
        style = self.scorer.detect_style(fv)

        # 1. Missing synergy pairs
        self._suggest_synergy_pairs(fv, suggestions, context="pre_mix")

        # 2. Weak note layers
        self._suggest_note_balance(dist, suggestions, context="pre_mix", style=style)

        # 3. Redundant materials (same Carles position + same SAR class)
        self._suggest_redundancies(fv, suggestions, context="pre_mix")

        # 4. Theory gaps
        self._suggest_theory_gaps(fv, suggestions, context="pre_mix")

        # 5. Low-scoring areas
        self._suggest_low_score_actions(scores, suggestions, context="pre_mix", style=style)

        return suggestions

    def _suggest_post_mix(
        self,
        fv: FormulaVector,
        observations: dict | None = None,
    ) -> list[str]:
        suggestions = []
        dist = fv.note_distribution()
        scores = self.scorer.score(fv)
        style = self.scorer.detect_style(fv)

        # Post-mix is add-only and conservative: only use safe nudges.
        self._suggest_synergy_pairs(fv, suggestions, context="post_mix")
        self._suggest_note_balance(
            dist,
            suggestions,
            context="post_mix",
            style=style,
            conservative=True,
        )
        self._suggest_low_score_actions(
            scores,
            suggestions,
            context="post_mix",
            style=style,
            conservative=True,
        )

        if observations:
            issue = str(observations.get("issue", "")).strip().lower()
            if issue in {"flat", "thin", "dull"} and not any("Post-mix" in s for s in suggestions):
                suggestions.append(
                    "Post-mix add-only nudge: Hedione is the safest first test if you want "
                    "a little more diffusion without changing the bottle's identity."
                )

        return suggestions[:4]

    def _suggest_between_mix(
        self,
        fv: FormulaVector,
        observations: dict | None = None,
    ) -> list[str]:
        suggestions = []
        dist = fv.note_distribution()
        scores = self.scorer.score(fv)
        style = self.scorer.detect_style(fv)

        self._suggest_synergy_pairs(fv, suggestions, context="between_mix")
        self._suggest_note_balance(dist, suggestions, context="between_mix", style=style)
        self._suggest_redundancies(fv, suggestions, context="between_mix")
        self._suggest_theory_gaps(fv, suggestions, context="between_mix")
        self._suggest_low_score_actions(scores, suggestions, context="between_mix", style=style)

        if observations:
            focus = str(observations.get("target_axis", "")).strip().lower()
            if focus in {"top", "heart", "base"}:
                suggestions.insert(
                    0,
                    f"Before the next remix, prioritize the {focus} layer that is already weak in the current bottle.",
                )

        return suggestions[:5]

    def _suggest_synergy_pairs(
        self,
        fv: FormulaVector,
        suggestions: list,
        context: str = "pre_mix",
    ):
        """Find synergy partners for existing materials that aren't in the formula."""
        filtered_partners: list[tuple[str, str]] = []
        seen_partners: set[str] = set()
        present = fv.ingredient_list()

        for source_rule_name, partner_rule_name in find_missing_rule_partners(present):
            source_display = _best_inventory_match(source_rule_name, present)
            partner_display = _best_inventory_match(partner_rule_name, self.inventory)
            if source_display is None or partner_display is None:
                continue
            if any(materials_match(partner_display, ingredient) for ingredient in present):
                continue

            partner_key = material_identity_key(partner_display)
            if partner_key in seen_partners:
                continue
            seen_partners.add(partner_key)
            filtered_partners.append((source_display, partner_display))

        if filtered_partners:
            top_partners = filtered_partners[:5]
            if context == "post_mix":
                prefix = "Post-mix add-only nudge"
                partner_strs = [
                    f"{source} → test a micro-add of {partner}"
                    for source, partner in top_partners
                ]
            elif context == "between_mix":
                prefix = "Before the next remix"
                partner_strs = [
                    f"{source} → test {partner} in the next adjustment"
                    for source, partner in top_partners
                ]
            else:
                prefix = "Missing synergy partners"
                partner_strs = [f"{source} → add {partner}" for source, partner in top_partners]
            suggestions.append(
                prefix + ": " + "; ".join(partner_strs)
            )

    def _suggest_note_balance(
        self,
        dist: dict,
        suggestions: list,
        context: str = "pre_mix",
        style: str | None = None,
        conservative: bool = False,
    ):
        target_top = self.constraints.target_top_pct
        target_heart = self.constraints.target_heart_pct
        target_base = self.constraints.target_base_pct
        tol = self.constraints.note_tolerance

        roster = _STYLE_ADDITIONS.get(style or "", _STYLE_ADDITIONS["classical"])

        def _pick(axis: str) -> list[str]:
            candidates = roster.get(axis, ())
            owned = _owned_candidates(candidates, self.inventory)
            return owned[:1] if conservative else owned[:3]

        if dist["top"] < target_top - tol:
            picks = _pick("top")
            if picks:
                suggestions.append(
                    f"{_prefix_for_context(context)}: top notes are underrepresented "
                    f"({dist['top']:.0f}% vs target {target_top:.0f}%). "
                    f"{'Try ' if conservative else 'Consider adding '}"
                    f"{', '.join(picks)}."
                )
        if dist["heart"] < target_heart - tol:
            picks = _pick("heart")
            if picks:
                suggestions.append(
                    f"{_prefix_for_context(context)}: heart notes are underrepresented "
                    f"({dist['heart']:.0f}% vs target {target_heart:.0f}%). "
                    f"{'Try ' if conservative else 'Consider adding '}"
                    f"{', '.join(picks)}."
                )
        if dist["base"] < target_base - tol:
            picks = _pick("base")
            if picks:
                suggestions.append(
                    f"{_prefix_for_context(context)}: base notes are underrepresented "
                    f"({dist['base']:.0f}% vs target {target_base:.0f}%). "
                    f"{'Try ' if conservative else 'Consider adding '}"
                    f"{', '.join(picks)}."
                )

    def _suggest_low_score_actions(
        self,
        scores: dict[str, float],
        suggestions: list,
        context: str = "pre_mix",
        style: str | None = None,
        conservative: bool = False,
    ):
        if scores.get("longevity", 0) < 40:
            picks = _owned_candidates(
                _STYLE_ADDITIONS.get(style or "", _STYLE_ADDITIONS["classical"])["base"],
                self.inventory,
            )
            picks = picks[:1] if conservative else picks[:3]
            if picks:
                suggestions.append(
                    f"{_prefix_for_context(context)}: longevity is low. "
                    f"{'Try ' if conservative else 'Consider adding '}"
                    f"{', '.join(picks)} to reinforce the drydown."
                )
        if scores.get("sillage", 0) < 40:
            picks = _owned_candidates(
                _STYLE_ADDITIONS.get(style or "", _STYLE_ADDITIONS["classical"])["heart"],
                self.inventory,
            )
            picks = picks[:1] if conservative else picks[:3]
            if picks:
                suggestions.append(
                    f"{_prefix_for_context(context)}: sillage is low. "
                    f"{'Try ' if conservative else 'Consider adding '}"
                    f"{', '.join(picks)} for more diffusion."
                )

    def _suggest_redundancies(
        self,
        fv: FormulaVector,
        suggestions: list,
        context: str = "pre_mix",
    ):
        """Find materials that occupy the same Carles position + SAR class."""
        if context == "post_mix":
            return
        position_groups: dict[str, list[str]] = {}
        for name in fv.ingredient_list():
            mat = _lookup_material(name)
            if mat:
                pos = mat.get("carles_position", "unknown")
                sar = mat.get("sar_class", "unknown")
                key = f"{pos}|{sar}"
                position_groups.setdefault(key, []).append(name)

        for key, members in position_groups.items():
            if len(members) > 2 and "unknown" not in key:
                suggestions.append(
                    f"Redundancy detected: {', '.join(members)} all serve the same "
                    f"role ({key.split('|')[0]}). Consider replacing one for diversity."
                )

    def _suggest_theory_gaps(
        self,
        fv: FormulaVector,
        suggestions: list,
        context: str = "pre_mix",
    ):
        """Check for missing Roudnitska roles and Jellinek quadrants."""
        if context == "post_mix":
            return
        theory = get_theory_rules()

        # Roudnitska roles
        roles_filled = set()
        roud_roles = theory.get("roudnitska_roles", {}).get("roles", {})
        for name in fv.ingredient_list():
            mat = _lookup_material(name)
            if mat and mat.get("roudnitska_function"):
                func = mat["roudnitska_function"].lower()
                for role_key in roud_roles:
                    if role_key in func:
                        roles_filled.add(role_key)

        missing_roles = set(roud_roles.keys()) - roles_filled
        if missing_roles:
            role_strs = []
            for r in list(missing_roles)[:3]:
                info = roud_roles.get(r, {})
                examples = info.get("examples", [])[:2]
                concrete = [
                    _concrete_inventory_name(example, self.inventory)
                    for example in examples
                ]
                concrete = [item for item in concrete if item]
                role_strs.append(
                    f"{r} ({', '.join(concrete)})" if concrete else r
                )
            suggestions.append(
                f"{_prefix_for_context(context)}: missing Roudnitska roles: "
                + ", ".join(role_strs)
                + ". Adding materials for these roles creates a more complete composition."
            )

        # Jellinek quadrants
        quadrants_hit = set()
        jellinek = theory.get("jellinek_map", {}).get("quadrants", {})
        for name in fv.ingredient_list():
            mat = _lookup_material(name)
            if mat and mat.get("jellinek_quadrant"):
                q = mat["jellinek_quadrant"].lower()
                for qk in jellinek:
                    if qk.replace("_", "-") in q or jellinek[qk].get("name", "").lower() in q:
                        quadrants_hit.add(qk)

        missing_quads = set(jellinek.keys()) - quadrants_hit
        if missing_quads:
            quad_strs = []
            for q in list(missing_quads)[:2]:
                info = jellinek.get(q, {})
                name = info.get("name", q)
                mats = info.get("materials", [])[:2]
                concrete = [
                    _concrete_inventory_name(mat, self.inventory)
                    for mat in mats
                ]
                concrete = [item for item in concrete if item]
                quad_strs.append(
                    f"{name} ({', '.join(concrete)})" if concrete else name
                )
            suggestions.append(
                f"{_prefix_for_context(context)}: Jellinek map gaps: "
                + ", ".join(quad_strs)
                + ". Spanning multiple quadrants adds psychological complexity."
            )

    # ── Convenience: Score existing formula ──

    def score(self, formula: FormulaVector) -> dict[str, float]:
        """Score a formula without optimizing."""
        return self.scorer.score(formula)
