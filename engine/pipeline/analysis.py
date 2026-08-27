"""Engine-owned access to the pipeline analysis formatter."""

from __future__ import annotations

from typing import Any


def render_pipeline_analysis(payload: dict[str, Any]) -> str:
    """Return the full human-readable pipeline analysis text."""
    from scripts.format_pipeline_analysis import (
        build_authority_dimensions,
        build_class_distribution,
        build_gate_summary,
        build_note_distribution,
        build_oav_headspace_table,
        build_oav_structural,
        build_perfumer,
        build_subthreshold,
        build_temporal,
    )

    formulas = payload.get("formulas", []) or []
    lines: list[str] = []
    for formula in formulas:
        if lines:
            lines.append("")
            lines.append("---")
            lines.append("")
        lines.append(f"# {formula.get('name', 'Formula')}")
        lines.append("")
        materials = formula.get("formula_state", {}).get("materials", [])
        builders = [
            lambda: build_gate_summary(formula),
            lambda: build_authority_dimensions(
                formula, payload.get("run_evidence_contract")
            ),
            lambda: build_oav_headspace_table(materials),
            lambda: build_note_distribution(materials),
            lambda: build_subthreshold(materials),
            lambda: build_class_distribution(materials),
            lambda: build_temporal(formula),
            lambda: build_perfumer(formula),
            lambda: build_oav_structural(materials, formula),
        ]
        for builder in builders:
            try:
                lines.extend(builder())
            except Exception as exc:  # pragma: no cover - defensive path
                lines.append(f"## Analysis Warning\n\nRenderer skipped one section due to {type(exc).__name__}: {exc}\n")
            lines.append("")
    return "\n".join(lines).strip() + "\n"
