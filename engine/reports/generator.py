"""Generated report renderer.

Reads structured JSON ledgers and renders markdown. Markdown is a GENERATED VIEW,
never the source of truth. Editing the report must never silently edit the target
formula.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


# ── ReportConfig ────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ReportConfig:
    """Configuration for a generated formula report.

    Parameters
    ----------
    title:
        Report title (e.g. ``"Reconstruction Report — Chanel No°5"``).
    formula_name:
        Name of the target formula.
    concentration:
        Concentration label (e.g. ``"EDP"``, ``"Extrait"``).
    batch_volume_ml:
        Target batch volume in millilitres.
    date:
        ISO 8601 date string for the report.
    claim_mode:
        Claim mode label (e.g. ``"reconstruction"``, ``"hypothesis"``).
    authority:
        Authority label (e.g. ``"Tier 3 — analytically constrained"``).
    """

    title: str
    formula_name: str
    concentration: str
    batch_volume_ml: float
    date: str
    claim_mode: str
    authority: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Render helpers ──────────────────────────────────────────────────────────────


def _fmt(val: Any) -> str:
    """Format a value for markdown table display."""
    if val is None:
        return "—"
    if isinstance(val, float):
        if abs(val) < 0.001:
            return f"{val:.2e}"
        if val == int(val):
            return str(int(val))
        return f"{val:.2f}"
    return str(val)


def _bold(text: str) -> str:
    """Wrap text in markdown bold markers."""
    return f"**{text}**"


def _header_row(columns: list[str]) -> str:
    """Return a markdown table header + separator given column names."""
    header = "| " + " | ".join(_bold(c) for c in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    return header + "\n" + sep


def _data_row(values: list[Any]) -> str:
    """Return a single markdown table data row."""
    return "| " + " | ".join(_fmt(v) for v in values) + " |"


# ── Section renderers ───────────────────────────────────────────────────────────


def _render_concept_lock(ledger: Any) -> str:
    """Render the concept-lock section if available."""
    lines: list[str] = []
    lines.append("")
    lines.append(_bold("Concept Lock"))
    lines.append("")
    concept = ledger.get("concept", "")
    if concept:
        lines.append(f"**Concept:** {concept}")
    family = ledger.get("family", "")
    if family:
        lines.append(f"**Family:** {family}")
    brief = ledger.get("brief", "")
    if brief:
        lines.append(f"**Brief:** {brief}")
    notes = ledger.get("notes", "")
    if notes:
        lines.append(f"**Notes:** {notes}")
    return "\n".join(lines)


def render_formula_report(
    config: ReportConfig,
    target_formula: list[dict[str, Any]],
    chassis_partition: list[dict[str, Any]] | None = None,
    modules: dict[str, list[dict[str, Any]]] | None = None,
) -> str:
    """Render a complete markdown formula report.

    Parameters
    ----------
    config:
        Report configuration.
    target_formula:
        Rows with keys ``ingredient``, ``stock``, ``raw_ul``, ``active_ul``,
        ``block``, ``role``.
    chassis_partition:
        Optional chassis rows with keys ``ingredient``, ``core_raw_ul``,
        ``module_raw_ul``, ``classification``.
    modules:
        Optional dict mapping module names to lists of material rows.

    Returns
    -------
    str
        Rendered markdown report.
    """
    lines: list[str] = []

    # ── Title header ────────────────────────────────────────────────────────
    lines.append(f"# {config.title}")
    lines.append("")
    lines.append(
        f"**Formula:** {config.formula_name}  "
        f"**Concentration:** {config.concentration}  "
        f"**Batch:** {_fmt(config.batch_volume_ml)} mL"
    )
    lines.append("")
    lines.append(
        f"**Date:** {config.date}  "
        f"**Claim mode:** {config.claim_mode}  "
        f"**Authority:** {config.authority}"
    )
    lines.append("")

    # ── Formula table ───────────────────────────────────────────────────────
    lines.append(_bold("Formula"))
    lines.append("")
    formula_cols = ["#", "Ingredient", "Stock", "Raw µL", "Active µL", "Role"]
    lines.append(_header_row(formula_cols))
    for i, row in enumerate(target_formula, start=1):
        lines.append(
            _data_row(
                [
                    i,
                    row.get("ingredient", ""),
                    row.get("stock", ""),
                    row.get("raw_ul", 0),
                    row.get("active_ul", 0),
                    row.get("role", ""),
                ]
            )
        )
    lines.append("")

    # ── Chassis partition table ─────────────────────────────────────────────
    if chassis_partition is not None:
        lines.append(_bold("Chassis Partition"))
        lines.append("")
        chassis_cols = ["Ingredient", "Core µL", "Module µL", "Classification"]
        lines.append(_header_row(chassis_cols))
        for row in chassis_partition:
            lines.append(
                _data_row(
                    [
                        row.get("ingredient", ""),
                        row.get("core_raw_ul", 0),
                        row.get("module_raw_ul", 0),
                        row.get("classification", ""),
                    ]
                )
            )
        lines.append("")

    # ── Flanker interface ───────────────────────────────────────────────────
    if modules is not None and modules:
        lines.append(_bold("Flanker Interface"))
        lines.append("")
        for module_name, module_rows in modules.items():
            lines.append(f"**Module:** {module_name}")
            lines.append("")
            mod_cols = ["Ingredient", "Raw µL", "Active µL", "Role"]
            lines.append(_header_row(mod_cols))
            for row in module_rows:
                lines.append(
                    _data_row(
                        [
                            row.get("ingredient", ""),
                            row.get("raw_ul", 0),
                            row.get("active_ul", 0),
                            row.get("role", ""),
                        ]
                    )
                )
            lines.append("")

    return "\n".join(lines)


def render_evidence_summary(evidence_claims: list[dict[str, Any]]) -> str:
    """Render a markdown table of evidence claims.

    Parameters
    ----------
    evidence_claims:
        Rows with keys ``claim_id``, ``source``, ``material``, ``type``,
        ``confidence``, ``excerpt``.

    Returns
    -------
    str
        Rendered markdown.
    """
    lines: list[str] = []
    lines.append(_bold("Evidence Claims"))
    lines.append("")

    if not evidence_claims:
        lines.append("*No evidence claims recorded.*")
        lines.append("")
        return "\n".join(lines)

    cols = ["Claim ID", "Source", "Material", "Type", "Confidence", "Excerpt"]
    lines.append(_header_row(cols))
    for row in evidence_claims:
        lines.append(
            _data_row(
                [
                    row.get("claim_id", ""),
                    row.get("source", ""),
                    row.get("material", ""),
                    row.get("type", ""),
                    row.get("confidence", ""),
                    row.get("excerpt", ""),
                ]
            )
        )
    lines.append("")

    # ── Contradictions ──────────────────────────────────────────────────────
    contradictions = [
        c for c in evidence_claims if c.get("contradiction") or c.get("conflict_group")
    ]
    if contradictions:
        lines.append(_bold("Contradictions"))
        lines.append("")
        for c in contradictions:
            cid = c.get("claim_id", "?")
            group = c.get("conflict_group", "")
            detail = c.get("contradiction", "")
            lines.append(f"- **{cid}** (group: {group}): {detail}")
        lines.append("")

    return "\n".join(lines)


def render_sensory_report(sensory_observations: list[dict[str, Any]]) -> str:
    """Render a time-resolved sensory evaluation table.

    Parameters
    ----------
    sensory_observations:
        Rows with keys ``time_seconds``, ``sample_code``, ``opening``,
        ``heart``, ``drydown``, ``diffusion``, ``longevity``, ``overall``.

    Returns
    -------
    str
        Rendered markdown.
    """
    lines: list[str] = []
    lines.append(_bold("Sensory Evaluation"))
    lines.append("")

    if not sensory_observations:
        lines.append("*No sensory observations recorded.*")
        lines.append("")
        return "\n".join(lines)

    cols = [
        "Time",
        "Sample Code",
        "Opening",
        "Heart",
        "Drydown",
        "Diffusion",
        "Longevity",
        "Overall",
    ]
    lines.append(_header_row(cols))
    for row in sensory_observations:
        t = row.get("time_seconds", 0)
        time_label = f"{_fmt(t)}s" if isinstance(t, (int, float)) else str(t)
        lines.append(
            _data_row(
                [
                    time_label,
                    row.get("sample_code", ""),
                    row.get("opening", ""),
                    row.get("heart", ""),
                    row.get("drydown", ""),
                    row.get("diffusion", ""),
                    row.get("longevity", ""),
                    row.get("overall", ""),
                ]
            )
        )
    lines.append("")

    return "\n".join(lines)


def render_batch_report(batch_events: list[dict[str, Any]]) -> str:
    """Render an event log table for a bottle batch.

    Parameters
    ----------
    batch_events:
        Rows with keys ``timestamp``, ``event_type``, ``material``,
        ``mass_g``, ``operator``, ``status``.

    Returns
    -------
    str
        Rendered markdown.
    """
    lines: list[str] = []
    lines.append(_bold("Batch Event Log"))
    lines.append("")

    if not batch_events:
        lines.append("*No batch events recorded.*")
        lines.append("")
        return "\n".join(lines)

    cols = ["Timestamp", "Event Type", "Material", "Mass (g)", "Operator", "Status"]
    lines.append(_header_row(cols))
    for row in batch_events:
        lines.append(
            _data_row(
                [
                    row.get("timestamp", ""),
                    row.get("event_type", ""),
                    row.get("material", ""),
                    row.get("mass_g", 0),
                    row.get("operator", ""),
                    row.get("status", ""),
                ]
            )
        )
    lines.append("")

    # ── Current-state summary ───────────────────────────────────────────────
    lines.append(_bold("Current State — Material Masses"))
    lines.append("")
    state_cols = ["Material", "Current Mass (g)"]
    lines.append(_header_row(state_cols))

    # Aggregate: last event per material with a mass_g value
    material_masses: dict[str, float] = {}
    for row in batch_events:
        mat = row.get("material", "")
        mass = row.get("mass_g")
        if mat and mass is not None:
            material_masses[mat] = float(mass)

    if material_masses:
        for mat, mass in sorted(material_masses.items()):
            lines.append(_data_row([mat, mass]))
    else:
        lines.append(_data_row(["—", "—"]))
    lines.append("")

    return "\n".join(lines)


def render_authority_vector(authority: dict[str, float]) -> str:
    """Render a markdown table of authority scores per dimension.

    Parameters
    ----------
    authority:
        Mapping from dimension name to score (0.0 – 1.0).

    Returns
    -------
    str
        Rendered markdown.
    """
    lines: list[str] = []
    lines.append(_bold("Authority Vector"))
    lines.append("")

    if not authority:
        lines.append("*No authority scores recorded.*")
        lines.append("")
        return "\n".join(lines)

    cols = ["Dimension", "Score (0.0–1.0)", "Assessment"]
    lines.append(_header_row(cols))

    for dim in sorted(authority.keys()):
        score = authority[dim]
        if score >= 0.8:
            assessment = "High"
        elif score >= 0.5:
            assessment = "Moderate"
        elif score >= 0.2:
            assessment = "Low"
        else:
            assessment = "Insufficient"
        lines.append(_data_row([dim, score, assessment]))
    lines.append("")

    lines.append(_bold("These dimensions are NEVER averaged into a single confidence score."))
    lines.append("")

    return "\n".join(lines)


# ── Full report assembly ────────────────────────────────────────────────────────


def generate_full_report(
    output_path: str,
    config: ReportConfig,
    **ledgers: Any,
) -> str:
    """Generate a complete markdown report from structured ledgers.

    Accepts keyword arguments for each ledger. Supported keys:

    * ``target`` — target formula rows (list of dict)
    * ``chassis`` — chassis partition rows (list of dict)
    * ``modules`` — module dict (dict of str to list of dict)
    * ``evidence`` — evidence claims (list of dict)
    * ``sensory`` — sensory observations (list of dict)
    * ``batch`` — batch events (list of dict)
    * ``authority_vector`` — authority scores (dict of str to float)
    * ``concept_lock`` — concept-lock metadata (dict)

    Parameters
    ----------
    output_path:
        Filesystem path to write the report to.
    config:
        Report configuration.
    **ledgers:
        Named ledger data.

    Returns
    -------
    str
        The rendered markdown text.
    """
    sections: list[str] = []

    # ── Title header ────────────────────────────────────────────────────────
    sections.append(f"# {config.title}")
    sections.append("")
    sections.append(
        f"**Formula:** {config.formula_name}  "
        f"**Concentration:** {config.concentration}  "
        f"**Batch:** {_fmt(config.batch_volume_ml)} mL"
    )
    sections.append("")
    sections.append(
        f"**Date:** {config.date}  "
        f"**Claim mode:** {config.claim_mode}  "
        f"**Authority:** {config.authority}"
    )
    sections.append("")

    # ── Concept lock ────────────────────────────────────────────────────────
    concept_lock: Any = ledgers.get("concept_lock")
    if concept_lock:
        sections.append(_render_concept_lock(concept_lock))

    # ── Formula table ───────────────────────────────────────────────────────
    target: Any = ledgers.get("target")
    if target is not None:
        sections.append(_bold("Formula"))
        sections.append("")
        formula_cols = ["#", "Ingredient", "Stock", "Raw µL", "Active µL", "Role"]
        sections.append(_header_row(formula_cols))
        for i, row in enumerate(target, start=1):
            sections.append(
                _data_row(
                    [
                        i,
                        row.get("ingredient", ""),
                        row.get("stock", ""),
                        row.get("raw_ul", 0),
                        row.get("active_ul", 0),
                        row.get("role", ""),
                    ]
                )
            )
        sections.append("")

    # ── Chassis partition ───────────────────────────────────────────────────
    chassis: Any = ledgers.get("chassis")
    if chassis is not None:
        sections.append(_bold("Chassis Partition"))
        sections.append("")
        chassis_cols = ["Ingredient", "Core µL", "Module µL", "Classification"]
        sections.append(_header_row(chassis_cols))
        for row in chassis:
            sections.append(
                _data_row(
                    [
                        row.get("ingredient", ""),
                        row.get("core_raw_ul", 0),
                        row.get("module_raw_ul", 0),
                        row.get("classification", ""),
                    ]
                )
            )
        sections.append("")

    # ── Flanker interface ───────────────────────────────────────────────────
    modules: Any = ledgers.get("modules")
    if modules is not None and modules:
        sections.append(_bold("Flanker Interface"))
        sections.append("")
        for module_name, module_rows in modules.items():
            sections.append(f"**Module:** {module_name}")
            sections.append("")
            mod_cols = ["Ingredient", "Raw µL", "Active µL", "Role"]
            sections.append(_header_row(mod_cols))
            for row in module_rows:
                sections.append(
                    _data_row(
                        [
                            row.get("ingredient", ""),
                            row.get("raw_ul", 0),
                            row.get("active_ul", 0),
                            row.get("role", ""),
                        ]
                    )
                )
            sections.append("")

    # ── Evidence summary ────────────────────────────────────────────────────
    evidence: Any = ledgers.get("evidence")
    if evidence is not None:
        sections.append(render_evidence_summary(evidence))

    # ── Sensory report ──────────────────────────────────────────────────────
    sensory: Any = ledgers.get("sensory")
    if sensory is not None:
        sections.append(render_sensory_report(sensory))

    # ── Batch report ────────────────────────────────────────────────────────
    batch: Any = ledgers.get("batch")
    if batch is not None:
        sections.append(render_batch_report(batch))

    # ── Authority vector ────────────────────────────────────────────────────
    authority_vector: Any = ledgers.get("authority_vector")
    if authority_vector is not None:
        sections.append(render_authority_vector(authority_vector))

    rendered = "\n".join(sections)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")

    return rendered


__all__ = [
    "ReportConfig",
    "generate_full_report",
    "render_authority_vector",
    "render_batch_report",
    "render_evidence_summary",
    "render_formula_report",
    "render_sensory_report",
]
