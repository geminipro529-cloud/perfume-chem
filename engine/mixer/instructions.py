"""Generate human-readable step-by-step mixing instructions.

Transforms the raw sequencer output into a formatted protocol document
with clear steps, timing, and rationale.
"""

from engine.mixer.sequencer import MixingSequencer


class InstructionGenerator:
    """Generate formatted mixing instructions from a formula."""

    def __init__(self):
        self.sequencer = MixingSequencer()

    def generate(self, ingredients: dict[str, float], formula_name: str = "Custom Formula") -> dict:
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
        seq = self.sequencer.sequence(ingredients)
        steps = seq["steps"]
        prebond_steps = seq["prebond_steps"]
        dissolution_steps = seq["dissolution_steps"]
        maceration_days = seq["maceration_estimate_days"]

        total_pct = round(sum(ingredients.values()), 2)
        phases = []
        warnings = []
        lines = []

        lines.append(f"═══ MIXING PROTOCOL: {formula_name} ═══")
        lines.append(f"Materials: {len(ingredients)} | Total: {total_pct}%")
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

        # ── Main mixing phases ──
        phase_order = ["base", "heart", "musk", "top", "solvent"]
        phase_labels = {
            "base": "BASE LAYER (foundation)",
            "heart": "HEART LAYER (character)",
            "musk": "MUSKS (smoothing)",
            "top": "TOP NOTES (sparkle)",
            "solvent": "CARRIER / SOLVENT",
        }

        phase_num = 1
        for phase_name in phase_order:
            phase_steps = [s for s in steps if s["phase"] == phase_name]
            if not phase_steps:
                continue

            phase_instructions = []
            label = phase_labels.get(phase_name, phase_name.upper())
            lines.append(f"─── PHASE {phase_num}: {label} ───")

            for s in phase_steps:
                instruction = (
                    f"  Step {s['order']}. Add {s['material']} ({s['pct']}%)\n"
                    f"           {s['rationale']}"
                )
                lines.append(instruction)
                phase_instructions.append(instruction.strip())

            # Add stir instruction between phases
            if phase_name != "solvent":
                stir = "  → Stir gently for 2-3 minutes. Let rest 5 minutes."
                lines.append(stir)
                phase_instructions.append(stir.strip())

            lines.append("")
            phases.append({"phase": phase_name, "instructions": phase_instructions})
            phase_num += 1

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
            "total_materials": len(ingredients),
            "total_pct": total_pct,
            "phases": phases,
            "maceration": f"{maceration_days} days minimum, best at {maceration_days}-{maceration_days + 14} days",
            "warnings": warnings,
            "full_text": "\n".join(lines),
        }
