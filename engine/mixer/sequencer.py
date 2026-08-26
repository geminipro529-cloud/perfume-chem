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

from engine.mixer.prebonding import PreBondingAnalyzer, is_crystalline
from engine.optimizer.models import _lookup_material, classify_note

# Materials that are solvents/carriers — always added last
SOLVENTS = {"ethanol", "dpg", "ipm", "isopropyl myristate", "dipropylene glycol"}


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

    def sequence(self, ingredients: dict[str, float]) -> dict:
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
        analysis = self.prebonder.analyze_formula(ingredients)

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

        return {
            "steps": steps,
            "prebond_steps": prebond_steps,
            "dissolution_steps": dissolution_steps,
            "maceration_estimate_days": maceration_days,
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
