"""Unified pipeline CLI — chains OAV authority + formula scoring + release gates.
This is the ONLY entry point for formula analysis."""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class _DataclassJSONEncoder(json.JSONEncoder):
    """Handle dataclass objects by converting them to dicts."""

    def default(self, obj):
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        return super().default(obj)


from engine.calibration.hashing import (
    canonical_json_bytes,
    stable_file_hash,
    stable_files_hash,
    stable_formula_definition_hash,
    stable_json_hash,
    stable_text_hash,
)
from engine.optimizer.models import ObjectiveWeights
from engine.optimizer.scoring import FormulaScorer
from engine.pipeline.analysis import render_pipeline_analysis
from engine.pipeline.audit_log import append_event, config_summary
from engine.pipeline.gates import (
    DEFAULT_CONCENTRATE_UL,
    ReleaseGateConfig,
    gate_formula,
)
from engine.pipeline.interventions import build_intervention_contract
from engine.pipeline.oav_authority import OAVAuthorityRequest, analyze_oav_authority
from engine.pipeline.release_scoring import compute_unified_release_scores
from engine.reference_contracts import detect_reference_claim
from scripts.format_pipeline_analysis import cli_transport_text
from scripts.verify_formula_workflow import (
    PIPELINE_ANALYSIS_END,
    PIPELINE_ANALYSIS_START,
    parse_formula_markdown,
    parse_pipeline_analysis_manifest,
    split_generated_pipeline_analysis,
)

PIPELINE_SOURCE_FILES = tuple(
    sorted(
        {
            *(
                path.relative_to(PROJECT_ROOT).as_posix()
                for path in (PROJECT_ROOT / "engine").rglob("*.py")
            ),
            *(
                path.relative_to(PROJECT_ROOT).as_posix()
                for path in (PROJECT_ROOT / "future_modules").rglob("*.py")
            ),
            "scripts/verify_formula_workflow.py",
            "scripts/format_pipeline_analysis.py",
            "scripts/formula_release_gate.py",
        }
    )
)


SCIENTIFIC_INPUT_FILES = (
    "engine/ingredient_intelligence.py",
    "engine/odor_thresholds.py",
    "engine/pipeline/natural_absolute_decomposition.py",
    "data/knowledge_graph/material_properties.json",
)


def _scientific_input_paths() -> tuple[str, ...]:
    paths = list(SCIENTIFIC_INPUT_FILES)
    paths.extend(
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in sorted((PROJECT_ROOT / "data" / "materials").glob("*.yaml"))
    )
    return tuple(paths)


def current_repository_evidence_hashes() -> dict[str, str]:
    """Take one repository evidence snapshot for a run or audit scan."""

    return {
        "inventory_sha256": stable_file_hash(PROJECT_ROOT / "inventory.txt"),
        "scientific_inputs_sha256": stable_files_hash(
            _scientific_input_paths(),
            root=PROJECT_ROOT,
        ),
        "pipeline_source_sha256": stable_files_hash(
            PIPELINE_SOURCE_FILES,
            root=PROJECT_ROOT,
        ),
    }


def _build_config(args: argparse.Namespace) -> ReleaseGateConfig:
    ifra_headroom = args.ifra_headroom
    commercial_mode = args.commercial_ready or args.commercial_trial
    if ifra_headroom is None:
        ifra_headroom = 0.8 if commercial_mode else 1.0
    return ReleaseGateConfig(
        expected_concentrate_ul=args.expected_concentrate_ul,
        batch_volume_ml=args.batch_volume_ml,
        temperature_K=args.temperature_k,
        brief=args.brief,
        family_archetype=args.family_archetype,
        allow_preblends=args.allow_preblends,
        min_confidence_score=args.min_confidence,
        ifra_headroom=ifra_headroom,
        commercial_mode=commercial_mode,
        commercial_confidence_policy="warn" if args.commercial_trial else "block",
        batch_scaling_targets_ml=tuple(args.scaling_target_ml or ()),
        audit_enabled=not args.no_audit,
        audit_source=args.audit_source or str(args.formula_file),
        expected_retail_price_thb=args.expected_retail_price_thb or 1500.0,
    )


def _format_oav_table(state) -> list[dict]:
    return [
        {
            "name": m.name,
            "dilution": m.dilution,
            "raw_ul": round(m.raw_ul, 2),
            "active_ul": round(m.active_ul, 2),
            "active_concentrate_ppm_w_w": m.active_concentrate_ppm_w_w,
            "active_mass_authority": m.active_mass_authority,
            "stock_fraction_basis": m.stock_fraction_basis,
            "mw": m.mw_g_mol,
            "mf_pct": round(m.mole_fraction * 100, 2),
            "vp_pa": m.vp_pure_pa,
            "gamma": round(m.gamma, 2),
            "vapor_ppm": round(m.vapor_ppm, 6),
            "odt_air_ppm": m.odt_air_ppm,
            "oav": round(m.oav, 2) if m.oav else None,
            "note": m.note,
        }
        for m in sorted(state.materials, key=lambda x: -(x.oav or 0))
    ]


def _run_input_hashes(
    formulas: list[dict],
    config: ReleaseGateConfig,
    *,
    parent_formulas: list[dict] | None = None,
    authorized_active_dose_changes: dict[str, str] | None = None,
) -> dict:
    requested_config = config_summary(config)
    requested_config.pop("audit_source", None)
    semantic_config = {
        "requested": requested_config,
        "formula_family_archetypes": [
            str(formula.get("family_archetype", "") or "") for formula in formulas
        ],
        "g15_authorized_active_dose_changes": dict(
            authorized_active_dose_changes or {}
        ),
    }
    return {
        "formula_definitions": [
            {
                "number": int(formula.get("number", 1)),
                "name": str(formula.get("name", "")),
                "sha256": stable_formula_definition_hash(formula),
            }
            for formula in formulas
        ],
        "g15_parent_formula_definitions": [
            {
                "number": int(formula.get("number", 1)),
                "name": str(formula.get("name", "")),
                "sha256": stable_formula_definition_hash(formula),
            }
            for formula in (parent_formulas or [])
        ],
        "semantic_config": semantic_config,
        "config_sha256": stable_json_hash(semantic_config),
        **current_repository_evidence_hashes(),
    }


def _prior_analysis_binding(formula: dict, run_hashes: dict) -> dict[str, object]:
    embedded = dict(formula.get("embedded_analysis", {}) or {})
    if not embedded.get("present"):
        return {"status": "NONE"}
    manifest = embedded.get("manifest")
    if not isinstance(manifest, dict) or manifest.get("manifest_status"):
        return {"status": "UNBOUND_LEGACY"}

    current_definition = stable_formula_definition_hash(formula)
    prior_definitions = list(manifest.get("formula_definitions", []) or [])
    prior_definition = next(
        (
            row
            for row in prior_definitions
            if int(row.get("number", -1)) == int(formula.get("number", 1))
        ),
        None,
    )
    mismatches = []
    if not prior_definition or prior_definition.get("sha256") != current_definition:
        mismatches.append("formula_definition")
    for key in (
        "config_sha256",
        "inventory_sha256",
        "scientific_inputs_sha256",
        "pipeline_source_sha256",
    ):
        if manifest.get(key) != run_hashes.get(key):
            mismatches.append(key.removesuffix("_sha256"))
    return {
        "status": "STALE" if mismatches else "CURRENT",
        "mismatches": mismatches,
    }


def _analysis_authority_header(manifest: dict, reports: list[dict]) -> str:
    authorities = manifest.get("authorities", {})
    ppm_statuses = [
        report.get("formula_state", {})
        .get("quantitative_authority", {})
        .get("active_concentrate_ppm_w_w", "UNAVAILABLE")
        for report in reports
    ]
    definitions = ", ".join(
        f"#{row['number']} {row['sha256']}" for row in manifest["formula_definitions"]
    )
    headspace_bases = [
        report.get("formula_state", {}).get("headspace_basis", "MODELED_ACTIVE_CONCENTRATE_SCREEN")
        for report in reports
    ]
    lines = [
        "# Run Evidence Contract",
        "",
        f"Formula definition SHA-256: {definitions}",
        f"Config SHA-256: {manifest['config_sha256']}",
        f"Inventory SHA-256: {manifest['inventory_sha256']}",
        f"Scientific inputs SHA-256: {manifest['scientific_inputs_sha256']}",
        f"Pipeline source SHA-256: {manifest['pipeline_source_sha256']}",
        "Exact concentrate ppm w/w: " + ", ".join(str(value) for value in ppm_statuses),
        "Headspace/OAV basis: " + ", ".join(str(value) for value in headspace_bases),
        "Headspace/OAV class: HEURISTIC_NOT_MEASURED (never a sensory-similarity percentage)",
        "Inventory stock authority: "
        + ", ".join(str(value) for value in authorities.get("stock", ["UNKNOWN"])),
        "Quantitative gate authority: "
        + ", ".join(str(value) for value in authorities.get("quantitative", ["UNKNOWN"])),
        "Named-reference authority: "
        + ", ".join(str(value) for value in authorities.get("claim", ["UNKNOWN"])),
        "Sensory-equivalence authority: NOT_AUTHORIZED_NOT_MEASURED",
        "",
    ]
    return "\n".join(lines)


def _artifact_payload(analysis_text: str, manifest: dict) -> str:
    manifest_json = canonical_json_bytes(manifest).decode("utf-8")
    return (
        f"{PIPELINE_ANALYSIS_START}\n"
        "## Pipeline Analysis\n\n"
        f"<!-- pipeline-analysis-manifest: {manifest_json} -->\n\n"
        f"```text\n{analysis_text.rstrip()}\n```\n"
        f"{PIPELINE_ANALYSIS_END}\n"
    )


def _verify_pipeline_analysis_artifact(
    formula_path: Path,
    expected_manifest: dict,
    expected_analysis: str,
) -> None:
    text = formula_path.read_text(encoding="utf-8", errors="strict")
    _formula_source, artifact = split_generated_pipeline_analysis(text)
    parsed_manifest = parse_pipeline_analysis_manifest(artifact)
    if not isinstance(parsed_manifest, dict) or stable_json_hash(
        parsed_manifest
    ) != stable_json_hash(expected_manifest):
        raise RuntimeError("Appended pipeline manifest failed immediate verification")
    code_block = re.search(r"```text\r?\n(.*?)\r?\n```", artifact, flags=re.DOTALL)
    if not code_block or stable_text_hash(code_block.group(1)) != stable_text_hash(
        expected_analysis
    ):
        raise RuntimeError("Appended pipeline analysis content hash failed verification")
    reparsed = parse_formula_markdown(formula_path)
    current_definitions = [
        {
            "number": int(formula.get("number", 1)),
            "name": str(formula.get("name", "")),
            "sha256": stable_formula_definition_hash(formula),
        }
        for formula in reparsed
    ]
    if current_definitions != expected_manifest.get("formula_definitions"):
        raise RuntimeError("Formula definition changed while appending pipeline analysis")


def _append_pipeline_analysis(
    formula_path: Path,
    analysis_text: str,
    manifest: dict,
) -> None:
    original_bytes = formula_path.read_bytes()
    text = original_bytes.decode("utf-8", errors="replace")
    formula_source, _old_artifact = split_generated_pipeline_analysis(text)
    replacement = formula_source.rstrip() + "\n\n" + _artifact_payload(analysis_text, manifest)
    temporary_path: Path | None = None
    rollback_path: Path | None = None
    replaced = False
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            delete=False,
            dir=formula_path.parent,
            prefix=f".{formula_path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(replacement)
            temporary_path = Path(handle.name)
        os.replace(temporary_path, formula_path)
        temporary_path = None
        replaced = True
        _verify_pipeline_analysis_artifact(formula_path, manifest, analysis_text)
        validation = validate_pipeline_analysis_artifact(formula_path)
        validation_status = validation.get("status")
        artifact_binding_status = validation.get(
            "artifact_binding_status",
            validation_status,
        )
        if validation_status not in {"CURRENT", "QUARANTINED"} or (
            artifact_binding_status != "CURRENT"
        ):
            raise RuntimeError(
                "Persisted pipeline artifact is not current: "
                + ", ".join(str(issue) for issue in validation.get("issues", []))
            )
    except Exception:
        if replaced:
            with tempfile.NamedTemporaryFile(
                "wb",
                delete=False,
                dir=formula_path.parent,
                prefix=f".{formula_path.name}.rollback.",
                suffix=".tmp",
            ) as handle:
                handle.write(original_bytes)
                rollback_path = Path(handle.name)
            os.replace(rollback_path, formula_path)
            rollback_path = None
        raise
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
        if rollback_path is not None and rollback_path.exists():
            rollback_path.unlink()


def _explicit_formula_quarantine(formula_source: str) -> bool:
    """Return whether the source declares a fail-closed lifecycle quarantine."""

    status_declared = re.search(
        r"(?im)^\*\*Status(?:\*\*:|:\*\*)\s*QUARANTINED\b",
        formula_source[:4000],
    )
    normalized = " ".join(formula_source[:4000].casefold().split())
    return bool(status_declared) and "do not mix or release" in normalized


def validate_pipeline_analysis_artifact(
    formula_path: Path,
    *,
    repository_hashes: dict[str, str] | None = None,
) -> dict[str, object]:
    """Validate a persisted artifact without trusting its embedded conclusions."""

    formula_path = Path(formula_path)
    text = formula_path.read_text(encoding="utf-8", errors="replace")
    formula_source, artifact = split_generated_pipeline_analysis(text)
    explicitly_quarantined = _explicit_formula_quarantine(formula_source)
    if not artifact:
        if explicitly_quarantined:
            return {
                "status": "QUARANTINED",
                "artifact_binding_status": "NONE",
                "issues": [],
                "release_authority": False,
                "quarantine_explicit": True,
            }
        return {"status": "NONE", "issues": []}
    manifest = parse_pipeline_analysis_manifest(artifact)
    if not isinstance(manifest, dict) or manifest.get("manifest_status"):
        return {"status": "UNBOUND_LEGACY", "issues": ["missing_or_invalid_manifest"]}

    integrity_issues: list[str] = []
    stale_issues: list[str] = []
    manifest_without_artifact_hash = dict(manifest)
    artifact_hash = manifest_without_artifact_hash.pop("artifact_sha256", None)
    if artifact_hash != stable_json_hash(manifest_without_artifact_hash):
        integrity_issues.append("artifact_manifest_hash")
    if manifest.get("config_sha256") != stable_json_hash(manifest.get("semantic_config", {})):
        integrity_issues.append("config_hash")
    code_block = re.search(r"```text\r?\n(.*?)\r?\n```", artifact, flags=re.DOTALL)
    if not code_block or manifest.get("analysis_sha256") != stable_text_hash(
        code_block.group(1) if code_block else ""
    ):
        integrity_issues.append("analysis_content_hash")

    formulas = parse_formula_markdown(formula_path)
    current_definitions = [
        {
            "number": int(formula.get("number", 1)),
            "name": str(formula.get("name", "")),
            "sha256": stable_formula_definition_hash(formula),
        }
        for formula in formulas
    ]
    if manifest.get("formula_definitions") != current_definitions:
        stale_issues.append("formula_definition")
    if manifest.get("binding_schema") == "formula-artifact-binding-v1":
        if manifest.get("renderer_version") != "formula-release-gate-v1":
            integrity_issues.append("renderer_version")
        bound_records = manifest.get("canonical_records")
        expected_records = [
            {
                "record_id": (
                    f"formula:{int(row['number'])}:"
                    + re.sub(
                        r"[^a-z0-9]+",
                        "-",
                        str(row["name"]).casefold(),
                    ).strip("-")
                ),
                "record_version": int(row["number"]),
                "canonical_content_sha256": row["sha256"],
            }
            for row in current_definitions
        ]
        if bound_records != expected_records:
            stale_issues.append("canonical_record_binding")
        input_fields = {
            key: manifest.get(key)
            for key in (
                "formula_definitions",
                "semantic_config",
                "config_sha256",
                "inventory_sha256",
                "scientific_inputs_sha256",
                "pipeline_source_sha256",
            )
        }
        # Early v1 artifacts predate parent binding. Preserve their exact input
        # shape, but never omit a lineage field that the writer actually stored.
        if "g15_parent_formula_definitions" in manifest:
            input_fields["g15_parent_formula_definitions"] = manifest[
                "g15_parent_formula_definitions"
            ]
        if manifest.get("analysis_input_sha256") != stable_json_hash(
            input_fields
        ):
            integrity_issues.append("analysis_input_hash")
        generated_at = manifest.get("generated_at_utc")
        try:
            parsed_generated_at = datetime.fromisoformat(
                str(generated_at).replace("Z", "+00:00")
            )
        except ValueError:
            parsed_generated_at = None
        if (
            parsed_generated_at is None
            or parsed_generated_at.tzinfo is None
            or parsed_generated_at.utcoffset() is None
        ):
            integrity_issues.append("generation_timestamp")
        repository_commit = manifest.get("repository_commit")
        if repository_commit != "UNAVAILABLE" and not re.fullmatch(
            r"[0-9a-f]{40,64}",
            str(repository_commit),
        ):
            integrity_issues.append("repository_commit")
    current_hashes = repository_hashes or current_repository_evidence_hashes()
    if manifest.get("inventory_sha256") != current_hashes["inventory_sha256"]:
        stale_issues.append("inventory")
    if manifest.get("scientific_inputs_sha256") != current_hashes["scientific_inputs_sha256"]:
        stale_issues.append("scientific_inputs")
    if manifest.get("pipeline_source_sha256") != current_hashes["pipeline_source_sha256"]:
        stale_issues.append("pipeline_source")

    if integrity_issues:
        artifact_binding_status = "TAMPERED"
        status = "TAMPERED"
    elif stale_issues:
        artifact_binding_status = "STALE"
        status = "QUARANTINED" if explicitly_quarantined else "STALE"
    else:
        artifact_binding_status = "CURRENT"
        status = "QUARANTINED" if explicitly_quarantined else "CURRENT"
    return {
        "status": status,
        "artifact_binding_status": artifact_binding_status,
        "issues": integrity_issues + stale_issues,
        "integrity_issues": integrity_issues,
        "stale_issues": stale_issues,
        "artifact_sha256": manifest.get("artifact_sha256"),
        "release_authority": False if explicitly_quarantined else None,
        "quarantine_explicit": explicitly_quarantined,
    }


def _repository_commit() -> str:
    """Return the current commit without exposing environment configuration."""

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "UNAVAILABLE"
    commit = result.stdout.strip().lower()
    return commit if re.fullmatch(r"[0-9a-f]{40,64}", commit) else "UNAVAILABLE"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run unified pipeline: OAV + scoring + gates.")
    parser.add_argument("--formula-file", required=True)
    parser.add_argument("--expected-concentrate-ul", type=float, default=DEFAULT_CONCENTRATE_UL)
    parser.add_argument("--batch-volume-ml", type=float, default=30.0)
    parser.add_argument("--temperature-k", type=float, default=305.0)
    parser.add_argument("--min-confidence", type=float, default=25.0)
    commercial = parser.add_mutually_exclusive_group()
    commercial.add_argument("--commercial-ready", action="store_true")
    commercial.add_argument("--commercial-trial", action="store_true")
    parser.add_argument("--ifra-headroom", type=float, default=None)
    parser.add_argument("--scaling-target-ml", type=float, action="append", default=[])
    parser.add_argument("--no-audit", action="store_true")
    parser.add_argument("--audit-source", default="")
    parser.add_argument(
        "--brief",
        default="auto",
        choices=[
            "auto",
            "generic",
            "layton_dna",
            "aromatic_fougere",
            "vetiver_woody",
            "floral_aldehydic_amber",
            "dhi_2011",
            "dhp_2014",
            "woody_floral_musk",
            "gourmand_floral",
            "prada_lhomme",
        ],
    )
    parser.add_argument("--family-archetype", default="")
    parser.add_argument("--allow-preblends", action="store_true")
    parser.add_argument(
        "--expected-retail-price-thb",
        type=float,
        default=1500.0,
        help="Target retail price in THB (default: 1500). Used for mass-market tier margin check.",
    )
    parser.add_argument(
        "--parent-formula-file",
        default=None,
        help="Immediate parent revision for mandatory G15 stock-rebase + temporal OAV screening.",
    )
    parser.add_argument(
        "--authorize-active-dose-change",
        action="append",
        default=[],
        metavar="MATERIAL=AUTHORITY",
        help=(
            "Explicitly authorize an intentional >=3x active-dose revision for one material. "
            "Repeat per material; authority text is preserved in G15 audit evidence."
        ),
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--print-analysis", action="store_true")
    analysis_write = parser.add_mutually_exclusive_group()
    analysis_write.add_argument("--append-analysis", dest="append_analysis", action="store_true")
    analysis_write.add_argument(
        "--no-append-analysis",
        dest="append_analysis",
        action="store_false",
        help="Do not persist the freshly bound analysis artifact (diagnostic/CI only).",
    )
    parser.set_defaults(append_analysis=True)
    args = parser.parse_args(argv)

    formula_path = Path(args.formula_file)
    if not formula_path.is_absolute():
        formula_path = PROJECT_ROOT / formula_path
    formulas = parse_formula_markdown(formula_path)
    if not formulas:
        raise ValueError(f"No parseable formulas found in {formula_path}")

    parent_formulas = None
    if args.parent_formula_file:
        parent_path = Path(args.parent_formula_file)
        if not parent_path.is_absolute():
            parent_path = PROJECT_ROOT / parent_path
        parent_formulas = parse_formula_markdown(parent_path)
        if not parent_formulas:
            raise ValueError(f"No parseable parent formulas found in {parent_path}")
        if len(parent_formulas) not in (1, len(formulas)):
            raise ValueError("Parent file must contain one formula or match child count.")

    authorized_active_dose_changes: dict[str, str] = {}
    for raw_authority in args.authorize_active_dose_change:
        if "=" not in raw_authority:
            raise ValueError(
                "--authorize-active-dose-change must use MATERIAL=AUTHORITY"
            )
        material, authority = (part.strip() for part in raw_authority.split("=", 1))
        if not material or not authority:
            raise ValueError(
                "--authorize-active-dose-change requires non-blank material and authority text"
            )
        if material in authorized_active_dose_changes and authorized_active_dose_changes[material] != authority:
            raise ValueError(f"Conflicting active-dose authorities for {material}")
        authorized_active_dose_changes[material] = authority

    # ── Preflight guard ──────────────────────────────────────────────
    from engine.formula_metadata import pipeline_preflight_guard

    preflight = pipeline_preflight_guard(str(formula_path), brief=args.brief)
    if not preflight.ok():
        print("PREFLIGHT HARD BLOCK — gate aborted", file=sys.stderr)
        for block in preflight.hard_blocks:
            print(f"  HARD_BLOCK: {block}", file=sys.stderr)
        return 1
    if preflight.warnings:
        for warn in preflight.warnings:
            print(f"  PREFLIGHT_WARN: {warn}", file=sys.stderr)

    config = _build_config(args)
    if any(detect_reference_claim(formula).quantitative_requested for formula in formulas):
        config = dataclasses.replace(config, quantitative_claim=True)
    run_hashes = _run_input_hashes(
        formulas,
        config,
        parent_formulas=parent_formulas,
        authorized_active_dose_changes=authorized_active_dose_changes,
    )
    scorer = FormulaScorer(ObjectiveWeights())
    reports = []

    for formula_index, formula in enumerate(formulas):
        ings = formula["ingredients_ul"]
        dils = formula["dilutions"]
        parent_formula = None
        if parent_formulas:
            parent_formula = (
                parent_formulas[0]
                if len(parent_formulas) == 1
                else parent_formulas[formula_index]
            )

        # Build the canonical physical state and temporal simulation once. G15
        # receives the immediate parent here, before any release/report output.
        gate_result = gate_formula(
            formula,
            config,
            parent_formula=parent_formula,
            authorized_active_dose_changes=authorized_active_dose_changes,
        )
        gate_report = gate_result.as_dict()

        # Phase 1: OAV authority analysis
        oav_req = OAVAuthorityRequest(
            formula_name=formula["name"],
            ingredients_ul=ings,
            dilutions=dils,
            stock_specs=formula.get("stock_specs", {}) or {},
            batch_volume_ml=args.batch_volume_ml,
            temperature_K=args.temperature_k,
            family_archetype=str(
                gate_result.config_summary.get("family_archetype", "")
                or formula.get("family_archetype", "")
            ),
            matrix_moles=dict(gate_result.formula_state.matrix_components_moles),
            matrix_mass_g=gate_result.formula_state.matrix_mass_g,
            matrix_source=gate_result.formula_state.matrix_source,
        )
        oav_result = analyze_oav_authority(oav_req, gate_report=gate_result)
        oav_table = _format_oav_table(oav_result.state)

        g15_gate = next(
            gate for gate in gate_report["gates"] if gate.get("gate") == "g15_oav_firewall"
        )
        premix_data = dict(g15_gate.get("data", {}).get("pre_mix_guard", {}) or {})
        if not premix_data:
            premix_data = {
                "status": g15_gate.get("status", "FAIL"),
                "findings": [],
                "g15_failure_code": g15_gate.get("data", {}).get("failure_code"),
                "limitations": [
                    "G15 failed before the lower-level pre_mix_guard could run; inspect G15 gate data."
                ],
            }

        # Phase 3: Release gates
        unified_scores = compute_unified_release_scores(
            formula, oav_result, gate_report, scorer=scorer
        ).as_dict()

        report = {
            **gate_report,
            "pre_mix_guard": premix_data,
            "scores": unified_scores["scores"],
            "industry_10": unified_scores["industry_10"],
            "score_provenance": unified_scores["provenance"],
            "oav_authority": {
                "status": oav_result.primary_status,
                "rank_score": round(oav_result.authority_rank_score, 1),
                "perceptible": len([r for r in oav_result.material_rows if (r.oav or 0) >= 1.0]),
                "subliminal_mass_pct": round(oav_result.subliminal_mass_ratio * 100, 1),
                "total_vapor_ppm": round(oav_result.state.total_vapor_ppm, 2),
                "family_drift_pct": round(oav_result.top_family_drift * 100, 1),
                "headspace_basis": oav_result.state.headspace_basis,
                "model_class": "HEURISTIC_NOT_MEASURED",
            },
            "oav_table": oav_table,
            "time_windows": [
                {
                    "label": w.label,
                    "t_seconds": w.t_seconds,
                    "perceptible_materials": w.perceptible_material_count,
                    "total_vapor_ppm": round(w.total_vapor_ppm, 2),
                    "dominant_leaders": [
                        {"material": leader["material"], "oav": leader["oav"]}
                        for leader in w.dominant_oav[:5]
                    ],
                }
                for w in oav_result.time_windows
            ],
            "prior_analysis_binding": _prior_analysis_binding(formula, run_hashes),
        }

        report["interventions"] = build_intervention_contract(
            formula,
            report,
            batch_volume_ml=args.batch_volume_ml,
        )
        report["diagnosis"] = list(report["interventions"].get("blocking_issues", []))
        reports.append(report)

    overall = "PASS"
    if any(r["status"] == "FAIL" for r in reports):
        overall = "FAIL"
    elif any(r["status"] == "WARN" for r in reports):
        overall = "WARN"

    payload = {
        "formula_file": str(formula_path),
        "overall": overall,
        "formulas": reports,
    }
    base_analysis_text = render_pipeline_analysis(payload)
    manifest = {
        "schema": "perfume_pipeline_run_evidence_v1",
        "binding_schema": "formula-artifact-binding-v1",
        "renderer_version": "formula-release-gate-v1",
        "analysis_input_sha256": stable_json_hash(run_hashes),
        "repository_commit": _repository_commit(),
        "canonical_records": [
            {
                "record_id": (
                    f"formula:{int(row['number'])}:"
                    + re.sub(
                        r"[^a-z0-9]+",
                        "-",
                        str(row["name"]).casefold(),
                    ).strip("-")
                ),
                "record_version": int(row["number"]),
                "canonical_content_sha256": row["sha256"],
            }
            for row in run_hashes["formula_definitions"]
        ],
        **run_hashes,
        "legacy_formula_hashes_v1": [
            {
                "number": report["number"],
                "name": report["name"],
                "sha256": report["formula_hash"],
            }
            for report in reports
        ],
        "overall": overall,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "authorities": {
            "stock": [
                next(
                    gate for gate in report["gates"] if gate["gate"] == "inventory_stock_contract"
                )["status"]
                for report in reports
            ],
            "quantitative": [
                next(gate for gate in report["gates"] if gate["gate"] == "quantitative_authority")[
                    "status"
                ]
                for report in reports
            ],
            "claim": [
                next(
                    gate for gate in report["gates"] if gate["gate"] == "reference_claim_contract"
                )["status"]
                for report in reports
            ],
            "headspace_oav": [
                report.get("formula_state", {}).get(
                    "headspace_basis", "MODELED_ACTIVE_CONCENTRATE_SCREEN"
                )
                for report in reports
            ],
        },
        "provenance": {
            "entities": [
                "formula_definition",
                "release_config",
                "inventory_snapshot",
                "scientific_inputs",
                "pipeline_source",
                "analysis_artifact",
            ],
            "activity": "formula_release_gate",
            "agent": "perfume-chem pipeline",
            "derivation": "analysis_artifact wasDerivedFrom all input entities",
        },
    }
    analysis_text = _analysis_authority_header(manifest, reports) + base_analysis_text
    manifest["analysis_sha256"] = stable_text_hash(analysis_text)
    manifest["artifact_sha256"] = stable_json_hash(manifest)
    if args.append_analysis:
        _append_pipeline_analysis(formula_path, analysis_text, manifest)
        artifact_authority = "PERSISTED_VERIFIED"
    else:
        artifact_authority = "BOUND_OUTPUT_NOT_PERSISTED"
    payload["run_evidence_contract"] = manifest
    payload["artifact_authority"] = artifact_authority
    payload["analysis_markdown"] = analysis_text

    if not args.no_audit:
        artifact_event = append_event(
            {
                "event_type": "analysis_artifact",
                "source": str(formula_path),
                "status": overall,
                "artifact_authority": artifact_authority,
                "run_evidence_contract": manifest,
            }
        )
        payload["analysis_audit_event_id"] = artifact_event.get("event_id")

    if args.json:
        print(json.dumps(payload, indent=2, cls=_DataclassJSONEncoder))
    else:
        print(f"Overall: {overall}")
        for report in reports:
            s = report.get("scores", {})
            oa = report.get("oav_authority", {})
            print(f"\n{report['name']}: {report['status']} ({report['commercial_readiness']})")
            print(
                f"  Diagnostic index: {s.get('total', 0):.1f}  |  "
                f"Heuristic sillage index: {s.get('sillage', 0):.1f}  |  "
                f"Heuristic longevity index: {s.get('longevity', 0):.1f}  |  "
                f"Synergy index: {s.get('synergy', 0):.1f}  |  "
                f"Heuristic skin index: {s.get('skin_performance', 0):.1f}"
            )
            print(
                "  Performance authority: uncalibrated diagnostic indices; "
                "not measured sillage, skin life, or skin outcome"
            )
            print(
                f"  OAV: {oa.get('status', '?')} (rank={oa.get('rank_score', 0)})  |  "
                f"Perceptible: {oa.get('perceptible', '?')}  |  "
                f"Vapor: {oa.get('total_vapor_ppm', 0)} ppm"
            )
            for gate in report["gates"]:
                detail = f" - {gate['detail']}" if gate.get("detail") else ""
                print(f"  {gate['status']}: {gate['gate']}{detail}")

    if args.print_analysis:
        print(cli_transport_text(analysis_text))

    return 1 if overall == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
