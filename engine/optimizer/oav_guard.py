"""OAV batch-scaling guard — prevents silent non-linear OAV shifts when
bottle volume changes.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**
- Concentrations in ppm (parts per million w/w in concentrate).
- ODT in ppm for ethanol solution, ppb for air.
- OAV = concentration_ppm / ODT_ppm (dimensionless).
- OAV < 1 = below threshold, OAV 1-5 = weak, OAV 5-50 = clear, OAV > 50 = dominant.
- Every perceptibility claim must be backed by OAV.

Why this module exists
----------------------
When you scale a formula between batch volumes (e.g. splitting a 30 mL
formulation into two 15 mL bottles), naive linear µL → µL/2 halving
looks correct on paper but is **not linear in perceptual terms**:

1. Integer-µL pipetting floors. Geosmin at 1 µL in 30 mL cannot be
   halved to 0.5 µL — you either keep 1 µL (2× concentration = beet
   overdose) or drop it (0× = accord loses rhizome earth-trace).

2. Dilution re-preparation. A 1% stock dose becomes unreliable below
   ~1 µL of neat, so a 5 µL dose of 1% cannot be halved cleanly — you
   must re-dilute to 0.5% and keep 5 µL, or keep 5 µL of 1% and accept
   2× concentration.

3. Threshold crossings. Materials sitting within 3× of their ODT may
   cross from suprathreshold (OAV ≥ 1) to subliminal (OAV < 1) with
   small concentration shifts. Every such material must be individually
   re-verified when volume changes — not assumed linear.

This guard checks every material in a formula for these three failure
modes and returns explicit warnings BEFORE a split is committed.

This was added after the v11 Photorealistic Iris DHM-overdose incident
where an optimizer run hardcoded a 10 mL batch assumption and produced
µL values that could not be safely rescaled without manual re-checking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from engine.odor_thresholds import MIXTURE_SUPPRESSION_FACTOR, lookup_odt_entry


# Smallest dose a hobbyist can reliably pipette (1 µL glass syringe floor).
MIN_PIPETTE_UL = 1.0

# Below this neat-equivalent dose we consider the material "trace" —
# splitting or re-scaling requires re-dilution, not linear arithmetic.
TRACE_NEAT_EQUIV_UL = 1.0


@dataclass
class OAVCheck:
    material: str
    source_conc_ppm: float
    target_conc_ppm: float
    odt_ppm: float | None
    source_oav: float | None
    target_oav: float | None
    severity: str          # "ok" | "info" | "warn" | "error"
    message: str


def _lookup_odt(name: str) -> float | None:
    """Look up ODT (ppm in ethanol) for a material via normalized exact match."""
    data = lookup_odt_entry(name)
    if data is None:
        return None
    odt_val = data.get("odt_eth")
    if odt_val is None:
        return None
    return float(odt_val)


def check_batch_scaling(
    ingredients_ul: dict[str, float],
    dilutions: dict[str, float],
    source_volume_ml: float,
    target_volume_ml: float,
) -> list[OAVCheck]:
    """Audit a µL-per-material formula for safe re-scaling between two bottle
    volumes. Returns per-material checks flagging:

    - **trace**: dose so small that linear halving crosses the pipette floor
    - **threshold**: material crosses its ODT (suprathreshold ↔ subliminal)
    - **mixture**: material leaves the mixture-suppression zone (3–5× ODT)

    The scale is performed under "same absolute µL, different ethanol volume"
    semantics — i.e. the user intends to KEEP dosing the same amount of each
    material and only change how much ethanol surrounds it. If the user
    instead intends proportional scaling (same %), use
    check_proportional_scaling.
    """
    results: list[OAVCheck] = []
    src_total_ul = source_volume_ml * 1000.0
    tgt_total_ul = target_volume_ml * 1000.0
    if src_total_ul <= 0 or tgt_total_ul <= 0:
        return results

    for name, amount_ul in ingredients_ul.items():
        dil = dilutions.get(name, 1.0)
        active_ul = amount_ul * dil
        src_ppm = (active_ul / src_total_ul) * 1e6
        tgt_ppm = (active_ul / tgt_total_ul) * 1e6

        odt_ppm = _lookup_odt(name)
        src_oav = (src_ppm / odt_ppm) if odt_ppm else None
        tgt_oav = (tgt_ppm / odt_ppm) if odt_ppm else None

        # 1) Trace-pipette check — if keeping absolute µL fixed we're fine,
        #    but if a downstream caller tries to halve the dose it will go
        #    below the pipette floor.
        neat_equiv = amount_ul * dil
        if neat_equiv < TRACE_NEAT_EQUIV_UL * 2:
            results.append(OAVCheck(
                material=name,
                source_conc_ppm=src_ppm,
                target_conc_ppm=tgt_ppm,
                odt_ppm=odt_ppm,
                source_oav=src_oav,
                target_oav=tgt_oav,
                severity="warn",
                message=(
                    f"{name}: {amount_ul:.2f} µL (neat-equiv {neat_equiv:.2f} µL) "
                    f"— near pipette floor; cannot be halved safely, "
                    f"re-dilute stock or keep dose fixed across splits"
                ),
            ))
            continue

        # 2) Threshold crossing — keeping absolute µL fixed means the
        #    concentration ratio changes inversely with volume. Check if
        #    OAV crosses 1.0 or MIXTURE_SUPPRESSION_FACTOR boundaries.
        if odt_ppm and src_oav is not None and tgt_oav is not None:
            if (src_oav >= 1.0) != (tgt_oav >= 1.0):
                results.append(OAVCheck(
                    material=name, source_conc_ppm=src_ppm,
                    target_conc_ppm=tgt_ppm, odt_ppm=odt_ppm,
                    source_oav=src_oav, target_oav=tgt_oav,
                    severity="error",
                    message=(
                        f"{name}: ODT crossing — OAV {src_oav:.2f} → {tgt_oav:.2f} "
                        f"(crosses detection threshold). Material becomes "
                        f"{'perceptible' if tgt_oav >= 1.0 else 'SUBLIMINAL'} "
                        f"at {target_volume_ml} mL."
                    ),
                ))
                continue
            if (src_oav >= MIXTURE_SUPPRESSION_FACTOR) != (tgt_oav >= MIXTURE_SUPPRESSION_FACTOR):
                results.append(OAVCheck(
                    material=name, source_conc_ppm=src_ppm,
                    target_conc_ppm=tgt_ppm, odt_ppm=odt_ppm,
                    source_oav=src_oav, target_oav=tgt_oav,
                    severity="warn",
                    message=(
                        f"{name}: mixture-suppression crossing — OAV "
                        f"{src_oav:.2f} → {tgt_oav:.2f} (crosses "
                        f"{MIXTURE_SUPPRESSION_FACTOR}× ODT). In a complex "
                        f"mixture this may become masked at {target_volume_ml} mL."
                    ),
                ))
                continue

        # 3) OK
        results.append(OAVCheck(
            material=name, source_conc_ppm=src_ppm,
            target_conc_ppm=tgt_ppm, odt_ppm=odt_ppm,
            source_oav=src_oav, target_oav=tgt_oav,
            severity="ok",
            message=f"{name}: OAV {src_oav or 0:.2f} → {tgt_oav or 0:.2f} (stable)",
        ))

    return results


def check_proportional_scaling(
    ingredients_ul: dict[str, float],
    dilutions: dict[str, float],
    source_volume_ml: float,
    target_volume_ml: float,
) -> list[OAVCheck]:
    """Audit a µL-per-material formula for PROPORTIONAL re-scaling (each
    material's µL is multiplied by target/source, keeping concentration %
    constant). Concentrations and OAVs are invariant, so the only failure
    mode is the pipette floor on trace materials.
    """
    results: list[OAVCheck] = []
    ratio = target_volume_ml / source_volume_ml if source_volume_ml > 0 else 1.0

    for name, amount_ul in ingredients_ul.items():
        dil = dilutions.get(name, 1.0)
        scaled_ul = amount_ul * ratio
        scaled_neat_equiv = scaled_ul * dil

        odt_ppm = _lookup_odt(name)
        src_total_ul = source_volume_ml * 1000.0
        conc_ppm = ((amount_ul * dil) / src_total_ul) * 1e6 if src_total_ul > 0 else 0.0
        oav = (conc_ppm / odt_ppm) if odt_ppm else None

        if scaled_ul < MIN_PIPETTE_UL:
            results.append(OAVCheck(
                material=name, source_conc_ppm=conc_ppm,
                target_conc_ppm=conc_ppm, odt_ppm=odt_ppm,
                source_oav=oav, target_oav=oav,
                severity="error",
                message=(
                    f"{name}: proportional scaling from {source_volume_ml} mL "
                    f"→ {target_volume_ml} mL yields {scaled_ul:.3f} µL "
                    f"(below {MIN_PIPETTE_UL} µL pipette floor). "
                    f"Use a weaker pre-dilution or keep minimum 1 µL and "
                    f"accept concentration shift."
                ),
            ))
        elif scaled_neat_equiv < TRACE_NEAT_EQUIV_UL and dil < 1.0:
            results.append(OAVCheck(
                material=name, source_conc_ppm=conc_ppm,
                target_conc_ppm=conc_ppm, odt_ppm=odt_ppm,
                source_oav=oav, target_oav=oav,
                severity="info",
                message=(
                    f"{name}: scaled dose {scaled_ul:.2f} µL of {dil*100:.1f}% "
                    f"(neat-equiv {scaled_neat_equiv:.3f} µL) — trace band, "
                    f"verify dilution stock accuracy"
                ),
            ))
        else:
            results.append(OAVCheck(
                material=name, source_conc_ppm=conc_ppm,
                target_conc_ppm=conc_ppm, odt_ppm=odt_ppm,
                source_oav=oav, target_oav=oav,
                severity="ok",
                message=f"{name}: scales cleanly to {scaled_ul:.1f} µL",
            ))

    return results


def summarize(checks: Iterable[OAVCheck]) -> str:
    checks = list(checks)
    errs = [c for c in checks if c.severity == "error"]
    warns = [c for c in checks if c.severity == "warn"]
    infos = [c for c in checks if c.severity == "info"]
    lines = [
        f"OAV batch-scaling audit: {len(errs)} error(s), "
        f"{len(warns)} warning(s), {len(infos)} info",
    ]
    for c in errs + warns + infos:
        sev_icon = {"error": "✗", "warn": "⚠", "info": "ℹ"}[c.severity]
        lines.append(f"  {sev_icon} {c.message}")
    if not (errs or warns or infos):
        lines.append("  ✓ all materials scale cleanly")
    return "\n".join(lines)
