"""Generate human-readable step-by-step mixing instructions.

Transforms the raw sequencer output into a formatted protocol document
with clear steps, timing, and rationale.
"""

from typing import Mapping, Sequence

from engine.mixer.sequencer import BASKET_LABELS, MixingRow, MixingSequencer


class InstructionGenerator:
    """Generate formatted mixing instructions from a formula."""

    def __init__(self):
        self.sequencer = MixingSequencer()

    def generate(
        self,
        ingredients: dict[str, float] | None = None,
        formula_name: str = "Custom Formula",
        prebond_analysis: dict | None = None,
        rows: Sequence[MixingRow | Mapping[str, object]] | None = None,
        source_authority_blockers: Sequence[str] = (),
    ) -> dict:
        """Generate complete mixing protocol.

        Args:
            ingredients: {material_name: percentage}
            formula_name: Name for the protocol header

        Returns: {
            title: str,
            total_materials: int,
            total_pct: float,
            phases: [{phase: str, instructions: [str]}],
            maceration: str,
            warnings: [str],
            full_text: str,  # complete protocol as a single string
        }
        """
        seq = self.sequencer.sequence(
            ingredients,
            prebond_analysis=prebond_analysis,
            rows=rows,
            source_authority_blockers=source_authority_blockers,
        )
        steps = seq["steps"]
        prebond_steps = seq["prebond_steps"]
        dissolution_steps = seq["dissolution_steps"]
        maceration_days = seq["maceration_estimate_days"]
        mixing_timing = seq["mixing_timing"]

        ingredients = dict(ingredients or {})
        raw_total_ul = seq.get("raw_total_ul")
        total_pct = (
            None if raw_total_ul is not None else round(sum(ingredients.values()), 2)
        )
        total_materials = len(rows or ingredients)
        phases = []
        warnings = []
        lines = []
        last_non_solvent_instructions: list[str] | None = None

        lines.append(f"═══ MIXING PROTOCOL: {formula_name} ═══")
        if raw_total_ul is None:
            lines.append(f"Materials: {total_materials} | Total: {total_pct}%")
        else:
            lines.append(
                f"Physical stock rows: {total_materials} | Raw total: {raw_total_ul:g} µL"
            )
        lines.append("")

        # ── Warnings ──
        if prebond_steps:
            w = (f"⚠ REACTIVE PAIRS DETECTED — {len(prebond_steps)} pair(s) require "
                 "pre-bonding before main mixing.")
            warnings.append(w)
        if dissolution_steps:
            ds_names = [d["material"] for d in dissolution_steps]
            w = (f"⚠ CRYSTALLINE SOLIDS: {', '.join(ds_names)} — "
                 "dissolve in warm solvent before adding.")
            warnings.append(w)
        if seq.get("compounding_authority") == "WITHHELD":
            w = (
                "⚠ EXECUTABLE COMPOUNDING CARD WITHHELD — "
                + "; ".join(seq.get("authority_blockers", []))
            )
            warnings.append(w)

        if warnings:
            lines.append("─── WARNINGS ───")
            for w in warnings:
                lines.append(w)
            lines.append("")

        # ── Dissolution phase ──
        dissolved = set()
        if dissolution_steps:
            phase_instructions = []
            lines.append("─── PHASE 0: DISSOLUTION ───")
            for i, ds in enumerate(dissolution_steps, 1):
                instruction = f"  {i}. {ds['method']}"
                lines.append(instruction)
                phase_instructions.append(instruction.strip())
                dissolved.add(ds["material"])
            lines.append("")
            phases.append({"phase": "dissolution", "instructions": phase_instructions})
            last_non_solvent_instructions = phase_instructions

        # ── Pre-bonding phase ──
        if prebond_steps:
            phase_instructions = []
            lines.append("─── PHASE 1: PRE-BONDING ───")
            for i, pb in enumerate(prebond_steps, 1):
                mats = " + ".join(pb["materials"])
                instruction = (
                    f"  {i}. Combine {mats} in a separate vessel.\n"
                    f"     Reaction: {pb['reaction']}\n"
                    f"     {pb['note']}\n"
                    f"     Allow 30-60 minutes for reaction to proceed."
                )
                lines.append(instruction)
                phase_instructions.append(instruction.strip())
            lines.append("")
            phases.append({"phase": "pre-bond", "instructions": phase_instructions})
            last_non_solvent_instructions = phase_instructions

        # ── Main mixing phases ──
        structured_order = str(seq.get("ordering_contract", "")).startswith("BASKET_")
        phase_order = (
            list(dict.fromkeys(step["phase"] for step in steps))
            if structured_order
            else ["base", "heart", "musk", "top", "solvent"]
        )
        phase_labels = {
            "base": "BASE LAYER (foundation)",
            "heart": "HEART LAYER (character)",
            "musk": "MUSKS (smoothing)",
            "top": "TOP NOTES (sparkle)",
            "solvent": "CARRIER / SOLVENT",
            "precharge": "DECLARED CARRIER PRECHARGE",
            "postcharge": "DECLARED FINAL MAKE-UP / POSTCHARGE",
            "unassigned": "UNASSIGNED PHYSICAL BASKET — NOT EXECUTABLE",
        }
        for basket, label in BASKET_LABELS.items():
            phase_labels[f"basket_{basket:02d}"] = f"BASKET {basket}: {label}"

        phase_num = 1
        finalizing_phases = {"solvent", "postcharge"}
        non_solvent_phase_names = [
            phase_name
            for phase_name in phase_order
            if phase_name not in finalizing_phases
            and phase_name != "precharge"
            and any(s["phase"] == phase_name for s in steps)
        ]
        last_non_solvent_phase = (
            non_solvent_phase_names[-1] if non_solvent_phase_names else None
        )
        has_non_solvent_steps = any(
            s["phase"] not in finalizing_phases | {"precharge"} for s in steps
        )
        final_homogenization_added = False

        def append_final_homogenization() -> None:
            nonlocal final_homogenization_added
            if final_homogenization_added:
                return
            checkpoint = (
                "  → Final concentrate homogenization: stir gently for "
                "2-3 minutes before the carrier/solvent addition or final handoff."
            )
            lines.append(checkpoint)
            lines.append("")
            if last_non_solvent_instructions is not None:
                last_non_solvent_instructions.append(checkpoint.strip())
            final_homogenization_added = True

        for phase_name in phase_order:
            phase_steps = [s for s in steps if s["phase"] == phase_name]
            if not phase_steps:
                continue

            # Special-only formulas have no ordinary aromatic phase to carry
            # the final homogenization.  Insert it immediately before the
            # carrier/solvent phase so dissolution and pre-bond waits remain
            # intact and the addition order is unchanged.
            if phase_name in finalizing_phases and has_non_solvent_steps:
                append_final_homogenization()

            phase_instructions = []
            label = phase_labels.get(phase_name, phase_name.upper())
            lines.append(f"─── PHASE {phase_num}: {label} ───")

            for s in phase_steps:
                display_material = s.get("physical_stock_label") or s["material"]
                amount = (
                    f"{s['raw_ul']:g} µL raw stock"
                    if s.get("amount_unit") == "raw_ul"
                    else f"{s['pct']}%"
                )
                receipt = ""
                if s.get("row_id"):
                    receipt += f" [row {s['row_id']}]"
                if s.get("prepared_dilution_id"):
                    receipt += f" [prepared dilution {s['prepared_dilution_id']}]"
                draft_prefix = (
                    "DRAFT ONLY — DO NOT COMPOUND. "
                    if structured_order
                    and seq.get("compounding_authority") == "WITHHELD"
                    else ""
                )
                instruction = (
                    f"  Step {s['order']}. {draft_prefix}Add {display_material} "
                    f"({amount}){receipt}\n"
                    f"           {s['rationale']}"
                )
                lines.append(instruction)
                phase_instructions.append(instruction.strip())

            # Keep addition continuous.  A brief end-of-phase homogeneity
            # check replaces the old timed stir/rest pair.  Only the final
            # aromatic phase gets a timed homogenization before the carrier
            # is added.
            if phase_name not in finalizing_phases | {"precharge"}:
                if phase_name == last_non_solvent_phase:
                    checkpoint = (
                        "  → Final concentrate homogenization: stir gently for "
                        "2-3 minutes before the carrier/solvent addition or final handoff."
                    )
                    final_homogenization_added = True
                else:
                    checkpoint = (
                        "  → Continue directly to the next ordered phase. At the end "
                        "of this phase/basket, make a brief homogeneity check; no timed rest."
                    )
                lines.append(checkpoint)
                phase_instructions.append(checkpoint.strip())

            lines.append("")
            phases.append({"phase": phase_name, "instructions": phase_instructions})
            if phase_name not in finalizing_phases | {"precharge"}:
                last_non_solvent_instructions = phase_instructions
            phase_num += 1

        # A formula without a carrier still needs its one final concentrate
        # homogenization after the last dissolution or pre-bond step.
        if has_non_solvent_steps:
            append_final_homogenization()

        # ── Maceration ──
        maceration_text = (
            f"─── MACERATION ───\n"
            f"  Seal tightly and store in a cool, dark place.\n"
            f"  Estimated maturation: {maceration_days} days minimum.\n"
            f"  Check at day 7 for initial impressions.\n"
            f"  Best results typically at day {maceration_days} – {maceration_days + 14}."
        )
        lines.append(maceration_text)

        return {
            "title": formula_name,
            "total_materials": total_materials,
            "total_pct": total_pct,
            "raw_total_ul": raw_total_ul,
            "ordered_raw_total_ul": seq.get("ordered_raw_total_ul"),
            "phases": phases,
            "maceration": f"{maceration_days} days minimum, best at {maceration_days}-{maceration_days + 14} days",
            "mixing_timing": mixing_timing,
            "elapsed_time_scope": seq.get("elapsed_time_scope", {}),
            "compounding_authority": seq.get("compounding_authority"),
            "authority_blockers": list(seq.get("authority_blockers", [])),
            "ordering_contract": seq.get("ordering_contract"),
            "basket_checkpoints": list(seq.get("basket_checkpoints", [])),
            "warnings": warnings,
            "full_text": "\n".join(lines),
        }


def build_formula_compounding_protocol(
    formula: Mapping[str, object],
    *,
    prebond_analysis: dict | None = None,
) -> dict:
    """Compile one parsed formula into an authority-bounded mixer result.

    Parsed physical rows are preserved exactly. Historical formulas receive an
    unassigned diagnostic preview, which necessarily withholds an executable
    card instead of inferring basket placement. Structured rows remain a
    diagnostic ordering preview until a trusted receipt producer binds current
    inventory, formula/G15/release status, and any prepared dilution lineage.
    """

    ingredient_values = formula.get("ingredients_ul", {}) or {}
    ingredients_ul = {
        str(material): float(raw_ul)
        for material, raw_ul in dict(ingredient_values).items()
    }
    generator = InstructionGenerator()
    analysis = (
        prebond_analysis
        if prebond_analysis is not None
        else generator.sequencer.prebonder.analyze_formula(ingredients_ul)
    )
    mixing_rows = list(formula.get("compounding_rows", []) or [])
    source_blockers = list(formula.get("compounding_row_blockers", []) or [])
    if not mixing_rows:
        mixing_rows = [
            {
                "row_id": f"formula-row-{index:03d}",
                "material": material,
                "physical_stock_label": material,
                "raw_ul": raw_ul,
                "basket": None,
                "operation": "DIRECT_ADD",
            }
            for index, (material, raw_ul) in enumerate(ingredients_ul.items(), 1)
        ]
        if not source_blockers:
            source_blockers = ["EXPLICIT_BASKET_ASSIGNMENTS_NOT_DECLARED"]
    return generator.generate(
        rows=mixing_rows,
        formula_name=str(formula.get("name", "Custom Formula")),
        prebond_analysis=analysis,
        source_authority_blockers=source_blockers,
    )
