"""Smell log against the model: what the time curve put on top, and what was smelled.

The model's leaders are the materials with the largest share of the summed
OAV in the scent curve: a detection screen, not perceived intensity,
pleasantness or liking (AGENTS.md Rule 1). Only names and their rank order
leave this module. Nothing here writes back to the model.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from math import isfinite
from typing import Any

from app.services.scent_curve import ScentCurveRow

SMELL_LOG_COMPARISON_BASIS = (
    "Model's leaders (detection screen): the materials the model can most easily "
    "detect at that time, by odour-threshold ratio. Not how strong they smell, "
    "nor how pleasant; a screening model, not a measurement."
)
# The scent curve's frames end at 4 h ("drydown", 14400 s). The loss law is
# unfitted, so the comparison does not run it out to skin day 1 or day 7.
SMELL_LOG_MODEL_LAST_SECONDS = 14400
SMELL_LOG_MODEL_LAST_LABEL = "4 h"


def smell_log_time_label(seconds: int) -> str:
    if seconds < 3600:
        return f"{seconds // 60} min"
    if seconds < 86400:
        return f"{seconds // 3600} h"
    return f"day {seconds // 86400}"


def smell_log_model_rows(
    components: Sequence[tuple[str, float | None, float, float | None, float]],
) -> tuple[list[ScentCurveRow], list[dict[str, str]]]:
    """Scent-curve rows from (name, volume uL, mass g, density g/mL, active fraction).

    A row without a volume is converted from its mass with the stock's own
    density; a row with neither, or with a stock strength outside (0, 1], is
    not modelled and is listed with the reason.
    """

    rows: list[ScentCurveRow] = []
    skipped: list[dict[str, str]] = []
    for name, volume_ul, mass_g, density_g_ml, active_fraction in components:
        amount = volume_ul
        if amount is None and density_g_ml is not None and density_g_ml > 0:
            amount = mass_g / density_g_ml * 1000.0
        if amount is None or not isfinite(amount) or amount <= 0:
            skipped.append(
                {"name": name, "reason": "no volume, and no stock density to convert its mass"}
            )
            continue
        if not isfinite(active_fraction) or not 0 < active_fraction <= 1:
            skipped.append({"name": name, "reason": "stock strength is not between 0 and 1"})
            continue
        rows.append(
            ScentCurveRow(identity_name=name, amount_ul=amount, stock_fraction=active_fraction)
        )
    return rows, skipped


def _tally(
    entries: Sequence[Mapping[str, Any]],
    field: str,
    spelling: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Names marked in ``field`` with the number of entries marking each, most first."""

    counts: dict[str, list[Any]] = {}
    for entry in entries:
        for key, name in {str(item).casefold(): str(item) for item in entry.get(field) or []}.items():
            if key not in counts:
                counts[key] = [spelling.get(key, name), 0]
            counts[key][1] += 1
    tallied = [{"name": name, "count": count} for name, count in counts.values()]
    return sorted(tallied, key=lambda item: -item["count"])


def smell_log_agreement(
    model_top: Sequence[str],
    you_leads: Sequence[str],
    you_weak: Sequence[str],
) -> dict[str, list[str]]:
    """Names-only agreement between the model's leaders and what was smelled."""

    leads = {name.casefold() for name in you_leads}
    weak = {name.casefold() for name in you_weak}
    top = {name.casefold() for name in model_top}
    return {
        "leads_the_model_also_had_on_top": [n for n in model_top if n.casefold() in leads],
        "model_top_you_did_not_mark_leading": [n for n in model_top if n.casefold() not in leads],
        "you_marked_weak_but_model_had_on_top": [n for n in model_top if n.casefold() in weak],
        "leads_the_model_did_not_have_on_top": [n for n in you_leads if n.casefold() not in top],
    }


def smell_log_comparison_windows(
    entries: Sequence[Mapping[str, Any]],
    windows: Mapping[str, tuple[str, str, int]],
    run_model: Callable[[list[tuple[str, float]]], Mapping[str, list[str]]],
    row_names: Sequence[str] = (),
) -> list[dict[str, Any]]:
    """One block per logged window, in window order; the model runs once.

    ``run_model`` takes the (window key, seconds) pairs inside the model's range
    and returns each key's model leaders, best first. A smelled name that
    matches a formula row apart from case is shown with the row's spelling.
    """

    spelling = {name.casefold(): name for name in row_names}
    logged = {key: [e for e in entries if e.get("window") == key] for key in windows}
    logged = {key: found for key, found in logged.items() if found}
    in_range = [
        (key, float(windows[key][2]))
        for key in logged
        if windows[key][2] <= SMELL_LOG_MODEL_LAST_SECONDS
    ]
    model_top = run_model(in_range) if in_range else {}
    blocks: list[dict[str, Any]] = []
    for key, found in logged.items():
        label, surface, seconds = windows[key]
        you_leads = _tally(found, "leads", spelling)
        you_weak = _tally(found, "weak", spelling)
        likings = [e["liking"] for e in found if e.get("liking") is not None]
        block: dict[str, Any] = {
            "window": key,
            "label": label,
            "surface": surface,
            "seconds": seconds,
            "n_entries": len(found),
            "liking_mean": round(sum(likings) / len(likings), 1) if likings else None,
            "you_leads": you_leads,
            "you_weak": you_weak,
        }
        if key in model_top:
            top = list(model_top[key])
            block.update(
                model_in_range=True,
                model_time_label=smell_log_time_label(seconds),
                model_note=None,
                model_top=top,
                agreement=smell_log_agreement(
                    top,
                    [item["name"] for item in you_leads],
                    [item["name"] for item in you_weak],
                ),
            )
        else:
            block.update(
                model_in_range=False,
                model_time_label=None,
                model_note=(
                    "Beyond the model's range: its time curve stops at "
                    f"{SMELL_LOG_MODEL_LAST_LABEL}, so it says nothing about {label.lower()}."
                ),
                model_top=[],
                agreement=None,
            )
        blocks.append(block)
    return blocks
