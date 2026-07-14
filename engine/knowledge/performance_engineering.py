"""Performance-engineering doctrine references for the canonical pipeline.

The live performance-engineering gate is implemented in `engine.pipeline.gates`.
This module exists to provide a stable, import-safe knowledge surface instead of
the previously corrupted placeholder file.
"""

from __future__ import annotations

PERFORMANCE_ENGINEERING_REFERENCES = {
    "projection": (
        "Use OAV carriers, diffusion boosters, and volatility layering to create "
        "projection without collapsing the formula into one loud material."
    ),
    "fixation": (
        "Fixative logic should combine multiple mechanisms such as caging, "
        "mw/logP persistence, and hydrogen-bond support rather than one brute-force base."
    ),
    "legibility": (
        "Performance gains do not justify unreadable overdosing; structural waste "
        "and sensory crowding should remain visible in the release path."
    ),
}


def get_performance_engineering_references() -> dict[str, str]:
    return dict(PERFORMANCE_ENGINEERING_REFERENCES)
