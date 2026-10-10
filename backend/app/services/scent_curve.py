"""Modelled share of the detectable smell per evaporation window (screening only).

Share is each material's OAV over the summed OAV of materials with OAV >= 1.
OAV is a detection diagnostic, not intensity, pleasantness or liking.
"""

from __future__ import annotations

import math
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class ScentCurveRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    identity_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    amount_ul: float = Field(gt=0, allow_inf_nan=False)
    stock_fraction: float = Field(default=1.0, gt=0, le=1, allow_inf_nan=False)


class ScentCurveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: list[ScentCurveRow] = Field(min_length=1, max_length=60)


def compute_scent_curve(rows: list[ScentCurveRow]) -> dict[str, Any]:
    from engine.pipeline.simulator import simulate_formula

    ing: dict[str, float] = {}
    dil: dict[str, float] = {}
    for row in rows:
        ing[row.identity_name] = ing.get(row.identity_name, 0.0) + row.amount_ul
        dil[row.identity_name] = row.stock_fraction
    windows: list[dict[str, Any]] = []
    for frame in simulate_formula(ing, dil):
        oavs = {m.name: m.screening_oav for m in frame.state.materials}
        notes = {m.name: m.note for m in frame.state.materials}
        audible = {
            k: v for k, v in oavs.items() if v is not None and math.isfinite(v) and v >= 1
        }
        total = sum(audible.values())
        materials: list[dict[str, Any]] = []
        for name in ing:
            oav = oavs.get(name)
            known = oav is not None and math.isfinite(oav)
            share = (audible[name] / total if name in audible else 0.0) if known else None
            materials.append(
                {
                    "name": name,
                    "known": known,
                    "oav": oav if known else None,
                    "share": share,
                    "note": notes.get(name) or "heart",
                }
            )
        shares = [m["share"] for m in materials if m["share"]]
        voices = math.exp(-sum(p * math.log(p) for p in shares)) if shares else 0.0
        top = sorted((m for m in materials if m["share"]), key=lambda m: -m["share"])[:3]
        windows.append(
            {
                "label": frame.label,
                "effective_voices": round(voices, 2),
                "top": [m["name"] for m in top],
                "materials": materials,
            }
        )
    return {
        "schema_version": "scent-curve-v1",
        "basis": "Share of what the model can detect (odour-threshold ratio), not strength or pleasantness; a screening model, not a measurement.",
        "windows": windows,
    }
