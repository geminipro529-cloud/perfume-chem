"""Mixing order computation — determines optimal addition sequence.

Rules (priority order):
  1. Dissolve crystalline solids in carrier or co-solvent first
  2. Pre-bond reactive pairs (Schiff base, H-bond donors+acceptors)
  3. Base materials first (highest MW, lowest VP → slowest evaporation)
  4. Heart materials second
  5. Top materials last (most volatile)
  6. Musks after main structure is set (they "wrap" around)
  7. Within each layer: order by CLP descending (least soluble → most)
  8. Ethanol / DPG / IPM (solvents) always last
"""

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from engine.mixer.prebonding import PreBondingAnalyzer, is_crystalline
from engine.optimizer.models import _lookup_material, classify_note

# Materials that are solvents/carriers — always added last
SOLVENTS = {"ethanol", "dpg", "ipm", "isopropyl myristate", "dipropylene glycol"}

BASKET_LABELS: dict[int, str] = {
    1: "Always used",
    2: "Vetivers",
    3: "Woods",
    4: "Wood modifiers and ambers",
    5: "Wood-vetivers",
    6: "Musks",
    7: "Muguet and lavender",
    8: "Jasmine, indole, and magnolia",
    9: "Ylang, orange flower, and narcotics",
    10: "Rose",
    11: "Iris and orris",
    12: "Edible smells",
    13: "Edible spices",
    14: "Favorite smells",
    15: "Fruits",
    16: "Aldehydes",
    17: "Green things",
}


@dataclass(frozen=True, slots=True)
class MixingRow:
    """One physical stock transfer; never aggregate rows silently."""

    row_id: str
    material: str
    raw_ul: float
    basket: int | None
    physical_stock_label: str = ""
    prepared_dilution_id: str | None = None
    operation: str = "DIRECT_ADD"

    def __post_init__(self) -> None:
        if not self.row_id.strip() or not self.material.strip():
            raise ValueError("Mixing rows require non-blank row_id and material")
        if not math.isfinite(self.raw_ul) or self.raw_ul <= 0:
            raise ValueError(
                f"Mixing row {self.row_id} requires finite positive raw_ul"
            )
        if self.basket is not None and self.basket not in BASKET_LABELS:
            raise ValueError(f"Mixing row {self.row_id} basket must be 1..17")
        operation = self.operation.strip().upper()
        if operation not in {"PRECHARGE", "DIRECT_ADD", "POSTCHARGE"}:
            raise ValueError(f"Unsupported mixing operation: {self.operation}")
        object.__setattr__(self, "operation", operation)
        if not self.physical_stock_label:
            object.__setattr__(self, "physical_stock_label", self.material)


def _coerce_mixing_row(value: MixingRow | Mapping[str, object]) -> MixingRow:
    if isinstance(value, MixingRow):
        return value
    return MixingRow(
        row_id=str(value.get("row_id", "")),
        material=str(value.get("material", "")),
        raw_ul=float(value.get("raw_ul", 0.0) or 0.0),
        basket=(
            None
            if value.get("basket") in (None, "")
            else int(value["basket"])
        ),
        physical_stock_label=str(value.get("physical_stock_label", "") or ""),
        prepared_dilution_id=(
            str(value["prepared_dilution_id"])
            if value.get("prepared_dilution_id")
            else None
        ),
        operation=str(value.get("operation", "DIRECT_ADD")),
    )


def _get_sort_key(mat_name: str) -> tuple:
    """Generate sort key for ordering within a layer.

    Sort by: CLP descending (hardest to dissolve first), then MW descending.
    """
    mat = _lookup_material(mat_name)
    clp = 0.0
    mw = 0.0
    if mat:
        clp = mat.get("clp") or 0.0
        mw = mat.get("mw") or 0.0
    return (-clp, -mw)


class MixingSequencer:
    """Compute optimal mixing order for a formula."""

    def __init__(self):
        self.prebonder = PreBondingAnalyzer()

    def sequence(
        self,
        ingredients: dict[str, float] | None = None,
        prebond_analysis: dict | None = None,
        rows: Sequence[MixingRow | Mapping[str, object]] | None = None,
        source_authority_blockers: Sequence[str] = (),
    ) -> dict:
        """Compute mixing order for a formula.

        Args:
            ingredients: {material_name: percentage}

        Returns: {
            steps: [
                {order: int, material: str, pct: float, phase: str, rationale: str},
                ...
            ],
            prebond_steps: [
                {materials: [str, str], reaction: str, note: str},
                ...
            ],
            dissolution_steps: [
                {material: str, method: str},
                ...
            ],
            maceration_estimate_days: int,
        }
        """
        structured_rows = tuple(_coerce_mixing_row(row) for row in (rows or ()))
        if structured_rows:
            if ingredients:
                raise ValueError("Pass either ingredients or structured rows, not both")
            row_ids = [row.row_id for row in structured_rows]
            if len(row_ids) != len(set(row_ids)):
                raise ValueError("Mixing row_id values must be unique")
            ingredients = {}
            for row in structured_rows:
                ingredients[row.material] = ingredients.get(row.material, 0.0) + row.raw_ul
            # Structured rows prove only that an ordering can be rendered.  They
            # do not prove current inventory, formula/G15/release status, or the
            # lineage of an opaque prepared-dilution identifier.  Until a
            # server-verified receipt is wired into this boundary, fail closed
            # and expose the result as a diagnostic ordering preview.
            source_authority_blockers = tuple(
                dict.fromkeys(
                    (
                        *source_authority_blockers,
                        "VERIFIED_PHYSICAL_AUTHORITY_RECEIPTS_REQUIRED",
                    )
                )
            )
        else:
            ingredients = dict(ingredients or {})

        # ``verify_formula_workflow`` already performs this analysis while
        # building its verification bundle.  Accepting that result lets
        # callers pass it through instead of paying for the O(n^2) pair scan
        # a second time.  Keep the default for existing callers.
        analysis = (
            prebond_analysis
            if prebond_analysis is not None
            else self.prebonder.analyze_formula(ingredients)
        )

        # Separate solvents
        solvents = {}
        materials = {}
        for name, pct in ingredients.items():
            if name.lower().strip() in SOLVENTS:
                solvents[name] = pct
            else:
                materials[name] = pct

        # ── Step 1: Dissolution steps for crystalline solids ──
        dissolution_steps = []
        for name in analysis["crystalline"]:
            if name in materials:
                dissolution_steps.append({
                    "material": name,
                    "method": f"Dissolve {name} in warm ethanol or DPG (40-50°C) "
                              "until fully clear before adding to formula."
                })

        # ── Step 2: Pre-bonding steps ──
        prebond_steps = []
        prebonded = set()
        for mat_a, mat_b, details in analysis["must_prebond"]:
            prebond_steps.append({
                "materials": [mat_a, mat_b],
                "reaction": details["reaction"],
                "note": details["note"],
            })
            prebonded.add(mat_a)
            prebonded.add(mat_b)

        if structured_rows:
            return self._sequence_basket_rows(
                structured_rows,
                analysis=analysis,
                prebond_steps=prebond_steps,
                dissolution_steps=dissolution_steps,
                source_authority_blockers=source_authority_blockers,
            )

        # ── Step 3: Classify remaining materials by note ──
        base_mats = []
        heart_mats = []
        top_mats = []
        musk_mats = []

        for name in materials:
            if name in prebonded:
                continue  # handled in prebond step

            mat_data = _lookup_material(name)
            sar = ""
            if mat_data:
                sar = (mat_data.get("sar_class") or "").lower()

            # Musks go in their own phase
            if "musk" in sar or "musk" in name.lower():
                musk_mats.append(name)
                continue

            note = classify_note(name)
            if note == "top":
                top_mats.append(name)
            elif note == "heart":
                heart_mats.append(name)
            else:
                base_mats.append(name)

        # Sort each layer by CLP descending (least soluble first)
        base_mats.sort(key=_get_sort_key)
        heart_mats.sort(key=_get_sort_key)
        top_mats.sort(key=_get_sort_key)
        musk_mats.sort(key=_get_sort_key)

        # ── Build step list ──
        steps = []
        order = 1

        # Dissolution before pre-bonding so solids are already in solution.
        for ds in dissolution_steps:
            steps.append({
                "order": order,
                "material": ds["material"],
                "pct": round(materials.get(ds["material"], 0), 2),
                "phase": "dissolution",
                "rationale": "Crystalline solid — dissolve before adding.",
            })
            order += 1
            # Remove from note lists to avoid duplicate step
            for lst in [base_mats, heart_mats, top_mats]:
                if ds["material"] in lst:
                    lst.remove(ds["material"])

        if prebond_steps:
            for pb in prebond_steps:
                total_pct = sum(materials.get(m, 0) for m in pb["materials"])
                steps.append({
                    "order": order,
                    "material": " + ".join(pb["materials"]),
                    "pct": round(total_pct, 2),
                    "phase": "pre-bond",
                    "rationale": pb["reaction"],
                })
                order += 1

        # Base layer
        for name in base_mats:
            steps.append({
                "order": order,
                "material": name,
                "pct": round(materials[name], 2),
                "phase": "base",
                "rationale": "Base note — add early for structural foundation.",
            })
            order += 1

        # Heart layer
        for name in heart_mats:
            steps.append({
                "order": order,
                "material": name,
                "pct": round(materials[name], 2),
                "phase": "heart",
                "rationale": "Heart note — forms the core character.",
            })
            order += 1

        # Musks (after structure)
        for name in musk_mats:
            steps.append({
                "order": order,
                "material": name,
                "pct": round(materials[name], 2),
                "phase": "musk",
                "rationale": "Musk — add after structure is set; wraps and smooths.",
            })
            order += 1

        # Top layer
        for name in top_mats:
            steps.append({
                "order": order,
                "material": name,
                "pct": round(materials[name], 2),
                "phase": "top",
                "rationale": "Top note — most volatile, add last to preserve freshness.",
            })
            order += 1

        # Solvents always last
        for name, pct in solvents.items():
            steps.append({
                "order": order,
                "material": name,
                "pct": round(pct, 2),
                "phase": "solvent",
                "rationale": "Carrier solvent — add last, stir gently to incorporate.",
            })
            order += 1

        # ── Maceration estimate ──
        maceration_days = self._estimate_maceration(materials)

        occupied_non_solvent_phases = {
            step["phase"]
            for step in steps
            if step["phase"] in {"base", "heart", "musk", "top"}
        }
        phase_count = len(occupied_non_solvent_phases)
        non_solvent_phase_count = len({
            step["phase"] for step in steps if step["phase"] != "solvent"
        })
        has_non_solvent_additions = non_solvent_phase_count > 0

        return {
            "steps": steps,
            "prebond_steps": prebond_steps,
            "dissolution_steps": dissolution_steps,
            "maceration_estimate_days": maceration_days,
            "compounding_authority": "LEGACY_OLFACTIVE_PHASE_SUGGESTION",
            "authority_blockers": [
                "RAW_UL_ROWS_AND_EXPLICIT_BASKET_ASSIGNMENTS_REQUIRED"
            ],
            "ordering_contract": "LEGACY_NOTE_PHASE_CLP_MW",
            "mixing_timing": {
                "occupied_non_solvent_phase_count": phase_count,
                "non_solvent_phase_count": non_solvent_phase_count,
                # Previous instructions prescribed 2-3 minutes of stirring
                # plus a 5-minute rest after every occupied non-solvent
                # phase.  Keep this reference so callers can show the
                # operator-time reduction without reconstructing history.
                "legacy_stir_minutes": {
                    "min": 2 * phase_count,
                    "max": 3 * phase_count,
                },
                "legacy_rest_minutes": 5 * phase_count,
                "legacy_timed_wait_minutes": {
                    "min": 7 * phase_count,
                    "max": 8 * phase_count,
                },
                # The optimized path uses one final concentrate
                # homogenization and no automatic inter-phase rest.
                "optimized_final_homogenization_minutes": {
                    "min": 2 if has_non_solvent_additions else 0,
                    "max": 3 if has_non_solvent_additions else 0,
                },
                "optimized_rest_minutes": 0,
                "homogeneity_checkpoint_count": (
                    phase_count if phase_count else int(has_non_solvent_additions)
                ),
            },
        }

    def _sequence_basket_rows(
        self,
        rows: tuple[MixingRow, ...],
        *,
        analysis: Mapping[str, object],
        prebond_steps: list[dict],
        dissolution_steps: list[dict],
        source_authority_blockers: Sequence[str],
    ) -> dict:
        """Build a conservation-preserving basket-first transfer order."""

        blockers: list[str] = list(dict.fromkeys(source_authority_blockers))
        direct_rows = [row for row in rows if row.operation == "DIRECT_ADD"]
        precharge_rows = [row for row in rows if row.operation == "PRECHARGE"]
        postcharge_rows = [row for row in rows if row.operation == "POSTCHARGE"]

        unassigned = [row.row_id for row in direct_rows if row.basket is None]
        if unassigned:
            blockers.append("UNASSIGNED_BASKET:" + ",".join(sorted(unassigned)))
        below_floor = [
            row.row_id
            for row in rows
            if row.raw_ul < 10.0 and not row.prepared_dilution_id
        ]
        if below_floor:
            blockers.append(
                "BELOW_10_UL_WITHOUT_PREPARED_DILUTION:"
                + ",".join(sorted(below_floor))
            )
        if analysis.get("must_prebond"):
            blockers.append("EXPLICIT_PREBOND_ALLOCATION_PLAN_REQUIRED")
        if analysis.get("keep_separate"):
            blockers.append("EXPLICIT_KEEP_SEPARATE_PLAN_REQUIRED")
        if analysis.get("crystalline"):
            blockers.append("EXPLICIT_DISSOLUTION_ALLOCATION_PLAN_REQUIRED")

        def label_key(row: MixingRow) -> tuple[float, str, str]:
            return (
                -row.raw_ul,
                row.physical_stock_label.casefold(),
                row.row_id,
            )
        precharge_rows.sort(key=label_key)
        postcharge_rows.sort(key=label_key)
        direct_rows.sort(
            key=lambda row: (
                row.basket if row.basket is not None else 10_000,
                *label_key(row),
            )
        )
        ordered_rows = [*precharge_rows, *direct_rows, *postcharge_rows]
        total_raw_ul = sum(row.raw_ul for row in rows)
        steps: list[dict] = []
        for order, row in enumerate(ordered_rows, 1):
            if row.operation == "PRECHARGE":
                phase = "precharge"
                rationale = "Explicit method precharge; placement was not inferred from its name."
            elif row.operation == "POSTCHARGE":
                phase = "postcharge"
                rationale = "Explicit method postcharge/final make-up."
            else:
                phase = f"basket_{int(row.basket):02d}" if row.basket is not None else "unassigned"
                rationale = (
                    f"Basket {row.basket} — {BASKET_LABELS.get(int(row.basket or 0), 'unassigned')}; "
                    "descending raw transfer within basket."
                )
            steps.append(
                {
                    "order": order,
                    "row_id": row.row_id,
                    "material": row.material,
                    "physical_stock_label": row.physical_stock_label,
                    "prepared_dilution_id": row.prepared_dilution_id,
                    "raw_ul": round(row.raw_ul, 6),
                    "pct": round(row.raw_ul / total_raw_ul * 100.0, 6),
                    "amount_unit": "raw_ul",
                    "basket": row.basket,
                    "operation": row.operation,
                    "phase": phase,
                    "rationale": rationale,
                }
            )

        basket_checkpoints: list[dict] = []
        running_total = sum(row.raw_ul for row in precharge_rows)
        for basket in range(1, 18):
            basket_rows = [row for row in direct_rows if row.basket == basket]
            subtotal = sum(row.raw_ul for row in basket_rows)
            running_total += subtotal
            basket_checkpoints.append(
                {
                    "basket": basket,
                    "label": BASKET_LABELS[basket],
                    "status": "COMPOUND" if basket_rows else "SKIP",
                    "row_ids": [row.row_id for row in basket_rows],
                    "subtotal_ul": round(subtotal, 6),
                    "running_total_ul": round(running_total, 6),
                }
            )
        # Unassigned direct rows are intentionally placed after all declared
        # baskets, but they remain real physical transfers in the diagnostic
        # preview.  Include them in conservation even though their presence
        # withholds execution authority.
        running_total += sum(row.raw_ul for row in direct_rows if row.basket is None)
        running_total += sum(row.raw_ul for row in postcharge_rows)

        occupied_baskets = len({row.basket for row in direct_rows if row.basket is not None})
        has_additions = bool(direct_rows)
        unassigned_phase_count = int(any(row.basket is None for row in direct_rows))
        direct_phase_count = occupied_baskets + unassigned_phase_count
        maceration_days = self._estimate_maceration(
            {row.material: row.raw_ul for row in direct_rows}
        )
        return {
            "steps": steps,
            "prebond_steps": prebond_steps,
            "dissolution_steps": dissolution_steps,
            "maceration_estimate_days": maceration_days,
            "compounding_authority": "WITHHELD",
            "authority_blockers": blockers,
            "ordering_contract": "BASKET_THEN_DESCENDING_RAW_UL_V1",
            "basket_checkpoints": basket_checkpoints,
            "raw_total_ul": round(total_raw_ul, 6),
            "ordered_raw_total_ul": round(running_total, 6),
            "mixing_timing": {
                "occupied_non_solvent_phase_count": direct_phase_count,
                "non_solvent_phase_count": direct_phase_count,
                "legacy_stir_minutes": {
                    "min": 2 * occupied_baskets,
                    "max": 3 * occupied_baskets,
                },
                "legacy_rest_minutes": 5 * occupied_baskets,
                "legacy_timed_wait_minutes": {
                    "min": 7 * occupied_baskets,
                    "max": 8 * occupied_baskets,
                },
                "optimized_final_homogenization_minutes": {
                    "min": 2 if has_additions else 0,
                    "max": 3 if has_additions else 0,
                },
                "optimized_rest_minutes": 0,
                "homogeneity_checkpoint_count": direct_phase_count,
            },
            "elapsed_time_scope": {
                "automatic_phase_rest_minutes": 0,
                "chemical_wait_minutes": (
                    {"min": 30, "max": 60}
                    if analysis.get("must_prebond")
                    else {"min": 0, "max": 0}
                ),
                "dissolution_wait": (
                    "UNTIL_CLEAR" if analysis.get("crystalline") else "NOT_APPLICABLE"
                ),
                "total_elapsed_status": (
                    "PARTIALLY_BOUNDED"
                    if analysis.get("must_prebond") or analysis.get("crystalline")
                    else "OPERATOR_ADDITION_TIME_NOT_MEASURED"
                ),
            },
        }

    def _estimate_maceration(self, materials: dict[str, float]) -> int:
        """Estimate maceration time in days.

        Heuristic based on:
        - More ingredients → longer maceration
        - Heavy base materials (MW > 250) → longer
        - Pre-bond pairs → additional time
        - Crystalline solids → additional time
        """
        base_days = 14
        n_ingredients = len(materials)
        heavy_count = 0
        crystalline_count = 0

        for name in materials:
            mat = _lookup_material(name)
            if mat:
                mw = mat.get("mw") or 0
                if mw > 250:
                    heavy_count += 1
            if is_crystalline(name):
                crystalline_count += 1

        # More ingredients → 1 extra day per 3 beyond 5
        if n_ingredients > 5:
            base_days += (n_ingredients - 5) // 3

        # Heavy bases need more time
        base_days += heavy_count * 2

        # Crystalline solids may take longer to fully incorporate
        base_days += crystalline_count

        return min(base_days, 60)  # cap at 60 days
