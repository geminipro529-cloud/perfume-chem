"""Dose-response modelling and character-shift diagnostics.

Stock dose, liquid concentration, delivered gas concentration, ODT, OAV,
intensity, character, pleasantness, and liking are separate endpoints. OAV is
only a detection-related diagnostic when numerator and threshold share a
compatible identity, phase, unit, matrix, and protocol. It is never an
intensity, perceived-contribution, pleasantness, beauty, or selection score.

Most aroma chemicals change their olfactive character at different
concentrations. This is NOT just intensity — it's qualitative shift:

  **Indole**: 0.01% floral-jasmine → 0.1% animalic → 1% fecal
  **Guaiacol**: 0.001% smoky depth → 0.01% phenolic → 0.1% medicinal
  **Civet/Castoreum**: trace = warmth → 0.1% = animalic
  **Ethyl Maltol**: 0.1% sweet lift → 2% cotton candy → 5% chemical burn
  **Iso E Super**: low = transparent woody → 5%+ = molecular cocoon effect
  **Hydroxycitronellal**: low = dewy-fresh → high = soapy/detergent
  **Aldehydes**: trace = sparkle → 1% = waxy-candle → 2%+ = soapy

The sigmoid Hill equation models this:
  Response = Rmax × [C]^n / (EC50^n + [C]^n)
where:
  Rmax = maximal response
  EC50 = half-maximal concentration
  n    = Hill coefficient (steepness of dose-response curve)

Sources:
  Chastrette (1998) Chemical Senses — structure-odor relationships
  Arctander (1969) Perfume and Flavor Chemicals
  Sell (2006) Chemistry and the Sense of Smell
  Stevens (1957) Psychophysical Review — power law for perceived intensity
  Cain (1969) Perception & Psychophysics — adaptation and dose-response
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence


def air_ppm_to_ug_l(
    gas_ppm_vv: float, *, mw_g_mol: float, temperature_k: float = 298.15,
    pressure_pa: float = 101325.0,
) -> float:
    """Ideal-gas conversion; never pass liquid ppm or a mass stock fraction here."""
    values = (gas_ppm_vv, mw_g_mol, temperature_k, pressure_pa)
    if (not all(math.isfinite(x) for x in values) or gas_ppm_vv < 0
            or min(mw_g_mol, temperature_k, pressure_pa) <= 0):
        raise ValueError("Finite nonnegative gas ppm and positive MW/T/P required")
    return gas_ppm_vv * pressure_pa * mw_g_mol / (8.31446261815324 * temperature_k) * .001


def measured_intensity_curve(
    gas_ug_l: float, *, imax: float, midpoint_log10_ug_l: float, slope: float,
) -> float:
    """Wakayama 2019 OISC, reconstructed against Table S3 (DOI 9b01225).

    Input is gas mass concentration in micrograms/litre air, NOT liquid dose.
    Coefficients are human-fitted intensity curves, not pleasantness or ODT.
    Zero printed slopes cannot be resolved from rounded source coefficients.
    """
    values = (gas_ug_l, imax, midpoint_log10_ug_l, slope)
    if not all(math.isfinite(x) for x in values) or gas_ug_l < 0 or imax <= 0 or slope <= 0:
        raise ValueError("Finite nonnegative gas concentration and positive Imax/slope required")
    if gas_ug_l == 0:
        return 0.0
    z = (math.log10(gas_ug_l) - midpoint_log10_ug_l) / slope
    if z >= 0:
        return imax / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return imax * ez / (1.0 + ez)


def corrected_wakayama_threshold_ng_l(
    *,
    imax: float,
    midpoint_log10_ug_l: float,
    slope: float,
    criterion_intensity: float = 1.4,
) -> float:
    """Return the corrected Wakayama threshold in ng/L air.

    This implements the December 2020 correction to Equation 3 of Wakayama
    et al.  The source curve uses micrograms per litre inside ``log10``; the
    leading ``3`` converts the solved concentration to nanograms per litre.
    The default 1.4 is the paper's LMS "barely detectable" criterion, not a
    receptor EC50 or a universal detection probability.
    """

    values = (imax, midpoint_log10_ug_l, slope, criterion_intensity)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Finite curve parameters and criterion are required")
    if slope <= 0.0 or criterion_intensity <= 0.0 or imax <= criterion_intensity:
        raise ValueError(
            "Positive slope/criterion and Imax greater than the criterion are required"
        )
    exponent = 3.0 + midpoint_log10_ug_l - slope * math.log(
        (imax - criterion_intensity) / criterion_intensity
    )
    try:
        threshold = 10.0 ** exponent
    except OverflowError as exc:
        raise ValueError(
            "Corrected threshold is outside the finite positive domain"
        ) from exc
    if not math.isfinite(threshold) or threshold <= 0.0:
        raise ValueError("Corrected threshold is outside the finite positive domain")
    return threshold


def parse_measured_intensity_parameters(rows) -> dict:
    """Parse the Pyrfume transcription without silently repairing source defects.

    Caller owns source-hash/license binding and exact CAS/stock mapping.
    This opt-in component does not replace existing production Hill parameters.
    """
    curves, excluded, seen = {}, [], set()
    for row in rows:
        cas = str(row["CAS"]).strip()
        if not cas or cas in seen:
            raise ValueError(f"Duplicate or empty CAS: {cas}")
        seen.add(cas)
        coefficients = dict(imax=float(row["I_max"]),
                            midpoint_log10_ug_l=float(row["C"]), slope=float(row["D"]))
        if not all(math.isfinite(x) for x in coefficients.values()):
            raise ValueError(f"Nonfinite source parameters: {cas}")
        reason = "NONPOSITIVE_SLOPE" if coefficients["slope"] <= 0 else (
            "NONPOSITIVE_MAXIMUM" if coefficients["imax"] <= 0 else None)
        if reason:
            excluded.append({"cas": cas, "name": row["Name"], "reason": reason})
        else:
            curves[cas] = coefficients
    return {"curves": curves, "excluded": excluded, "source_rows": len(seen)}


def measured_mixture_intensity(gas_ug_l_by_cas: dict, curves: dict, *, method: str) -> dict:
    """Opt-in intensity hypotheses, not a formula-quality objective.

    strongest_component: Wakayama 2019 Table S5.
    primacy: Pellegrino 2025 DOI 10.1101/2025.08.08.668954 Eq8,
    logsumexp at 20% ambient concentration, without an undocumented /N.
    Applying primacy to Wakayama curves is an external transfer experiment.
    Even with active components only, its low-dose limit depends on count;
    callers must retain this model discrepancy, not interpret it as richness.
    """
    if method not in {"strongest_component", "primacy"}:
        raise ValueError("Unknown measured mixture model")
    if any(not math.isfinite(v) or v < 0 for v in gas_ug_l_by_cas.values()):
        raise ValueError("Finite nonnegative gas concentrations required")
    active = {cas: value for cas, value in gas_ug_l_by_cas.items() if value > 0}
    missing = sorted(set(active) - set(curves))
    result = {"method": method, "intensity": None, "component_intensities": {},
              "missing_calibrations": missing, "predicted_liking": None,
              "formula_optimization_authority": False,
              "model_domain_warning": "Intensity only; mixture suppression and study transfer unvalidated"}
    if missing:
        return result
    intensities = {cas: measured_intensity_curve(
        value * (.2 if method == "primacy" else 1.), **curves[cas])
        for cas, value in active.items()}
    if not intensities:
        prediction = 0.
    else:
        maximum = max(intensities.values())
        prediction = maximum if method == "strongest_component" else maximum + math.log(
            sum(math.exp(value - maximum) for value in intensities.values()))
    result.update(intensity=prediction, component_intensities=intensities)
    return result


def benchmark_measured_intensity(curves: dict, observations: dict) -> dict:
    """Published-curve reconstruction and transfer comparison; no fitting here.

    Source training/observation overlap is not established. This is not a
    held-out validation claim for the source coefficients.
    """
    def summarize(rows):
        if not rows:
            raise ValueError("Benchmark groups must contain observations")
        if not all(math.isfinite(r[key]) for r in rows
                   for key in ("predicted", "observed", "published_prediction")):
            raise ValueError("Benchmark observations and predictions must be finite")
        groups = sorted({r["group"] for r in rows})
        errors = [(r["predicted"] - r["observed"]) ** 2 for r in rows]
        per_group = {group: math.sqrt(sum(
            (r["predicted"] - r["observed"]) ** 2 for r in rows if r["group"] == group
        ) / sum(r["group"] == group for r in rows)) for group in groups}
        return {"n": len(rows), "pooled_rmse": math.sqrt(sum(errors) / len(errors)),
                "mean_group_rmse": sum(per_group.values()) / len(per_group),
                "per_group_rmse": per_group, "rows": rows,
                "published_prediction_max_abs_difference": max(
                    abs(r["predicted"] - r["published_prediction"]) for r in rows)}

    singles = []
    for series in observations["single_component_series"]:
        for log_g, observed, published in zip(
            series["log_g"], series["observed"], series["published_prediction"], strict=True
        ):
            singles.append({"group": series["name"], "log_g": log_g, "observed": observed,
                            "published_prediction": published,
                            "predicted": measured_intensity_curve(10 ** log_g, **curves[series["cas"]])})
    methods = {}
    for method in ("strongest_component", "primacy"):
        rows = []
        for series in observations["mixture_series"]:
            if not series["cas"] or len(set(series["cas"])) != len(series["cas"]):
                raise ValueError("Mixture CAS must be nonempty and unique")
            for offset, observed, published in zip(
                series["log_dilution_offsets"], series["observed"],
                series["published_prediction"], strict=True
            ):
                gas = {cas: 10 ** (log_g + offset) for cas, log_g in zip(
                    series["cas"], series["highest_log_g"], strict=True)}
                prediction = measured_mixture_intensity(gas, curves, method=method)
                if prediction["intensity"] is None:
                    raise ValueError(f"Missing benchmark curves: {prediction['missing_calibrations']}")
                rows.append({"group": series["id"], "log_offset": offset, "observed": observed,
                             "published_prediction": published, "predicted": prediction["intensity"]})
        methods[method] = summarize(rows)
        methods[method]["published_reference_method"] = "strongest_component"
    return {"single": summarize(singles), "mixtures": methods,
            "parameters_fitted": False, "sensory_endpoint": "INTENSITY_ONLY",
            "parameters_fitted_in_this_run": False,
            "benchmark_scope": "PUBLISHED_CURVE_RECONSTRUCTION_AND_MIXTURE_TRANSFER_COMPARISON",
            "source_training_observation_overlap": "NOT_ESTABLISHED",
            "formula_changed": False, "full_perfume_validated": False}


# ── Governed measured-intensity capabilities (Checkpoint 2) ────────────────

MEASURED_INTENSITY_MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "governance"
    / "measured_intensity_capabilities_20260923.json"
)

MEASURED_INTENSITY_FALSE_AUTHORITIES = {
    "character_authorized": False,
    "pleasantness_authorized": False,
    "personal_liking_authorized": False,
    "population_liking_authorized": False,
    "beauty_authorized": False,
    "formula_optimization_authority": False,
    "evidence_admission_authorized": False,
    "physical_experiment_authorized": False,
    "compounding_authorized": False,
    "purchase_authorized": False,
    "inventory_mutation_authorized": False,
    "safety_authorized": False,
    "release_authorized": False,
}


def _file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_measured_intensity_capabilities(
    manifest_path: str | Path = MEASURED_INTENSITY_MANIFEST,
) -> dict[str, Any]:
    """Load source parameters without promoting any unadjudicated identity.

    The source and transcription byte hashes are verified before a curve row is
    returned.  Rows remain ``UNADJUDICATED`` unless an independent capability
    record supplies exact canonical identity and applicability bindings.
    """

    manifest_file = Path(manifest_path).resolve()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    root = Path(__file__).resolve().parents[1]
    source = manifest["source"]
    source_path = root / source["source_artifact_path"]
    transcription_path = root / source["transcription_artifact_path"]
    reasons: list[str] = []
    if _file_sha256(source_path) != source["source_artifact_sha256"]:
        reasons.append("SOURCE_ARTIFACT_HASH_MISMATCH")
    if _file_sha256(transcription_path) != source["transcription_artifact_sha256"]:
        reasons.append("TRANSCRIPTION_ARTIFACT_HASH_MISMATCH")
    if not str(source.get("license", "")).strip():
        reasons.append("LICENSE_MISSING")
    conflicts = {
        row["source_cas"]: row
        for row in manifest["identity_adjudication"]["known_conflicts"]
    }
    curves: dict[str, dict[str, Any]] = {}
    if not reasons:
        with transcription_path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                cas = str(row["CAS"]).strip()
                name = str(row["Name"]).strip()
                curve = {
                    "imax": float(row["I_max"]),
                    "midpoint_log10_ug_l": float(row["C"]),
                    "slope": float(row["D"]),
                }
                state = "CONFLICT" if cas in conflicts else "UNADJUDICATED"
                curves[cas] = {
                    "capability_id": f"{manifest['manifest_id']}:{cas}",
                    "manifest_id": manifest["manifest_id"],
                    "source_artifact_sha256": source["source_artifact_sha256"],
                    "transcription_artifact_sha256": source[
                        "transcription_artifact_sha256"
                    ],
                    "license": source["license"],
                    "permitted_use": source["permitted_use"],
                    "commercial_use_authorized": source[
                        "commercial_use_authorized"
                    ],
                    "source_fit_overlap": source["source_fit_overlap"],
                    "chemical_identity": {
                        "source_name": name,
                        "source_cas": cas,
                        "canonical_name": None,
                        "canonical_cas": None,
                        "identity_status": state,
                        "exact_stock_match_required": True,
                        "conflict_description": (
                            conflicts[cas]["reason"] if cas in conflicts else None
                        ),
                    },
                    "input_contract": dict(manifest["input_contract"]),
                    "curve": {
                        **curve,
                        **manifest["curve_contract"],
                    },
                    "applicability": {
                        **manifest["applicability"],
                        "observed_range_ug_l_air": None,
                        "exact_material_ids": [],
                    },
                    "uncertainty": dict(manifest["uncertainty"]),
                    "endpoint_authority": dict(manifest["endpoint_authority"]),
                    "action_authority": dict(manifest["action_authority"]),
                }
    return {
        "manifest": manifest,
        "manifest_sha256": _file_sha256(manifest_file),
        "status": "HOLD" if reasons or manifest["admission_state"].startswith("HOLD") else "AVAILABLE",
        "reasons": reasons or [manifest["admission_state"]],
        "curves": curves,
    }


def validate_measured_intensity_capability(
    record: Mapping[str, Any], requested_context: Mapping[str, Any]
) -> dict[str, Any]:
    """Fail closed unless identity, gas units, range, matrix and use all match."""

    reasons: list[str] = []
    caveats: list[str] = []
    try:
        governed = json.loads(MEASURED_INTENSITY_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        governed = {}
    governed_source = governed.get("source", {}) if isinstance(governed, Mapping) else {}
    for field, reason in (
        ("source_artifact_sha256", "SOURCE_ARTIFACT_HASH_MISMATCH"),
        ("transcription_artifact_sha256", "TRANSCRIPTION_ARTIFACT_HASH_MISMATCH"),
    ):
        value = record.get(field)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            reasons.append(reason)
    if record.get("manifest_id") != governed.get("manifest_id"):
        reasons.append("SOURCE_ARTIFACT_HASH_MISMATCH")
    if record.get("source_artifact_sha256") != governed_source.get(
        "source_artifact_sha256"
    ):
        reasons.append("SOURCE_ARTIFACT_HASH_MISMATCH")
    if record.get("transcription_artifact_sha256") != governed_source.get(
        "transcription_artifact_sha256"
    ):
        reasons.append("TRANSCRIPTION_ARTIFACT_HASH_MISMATCH")
    license_name = str(record.get("license", "")).strip()
    if not license_name:
        reasons.append("LICENSE_MISSING")
    if requested_context.get("commercial_use") and not record.get(
        "commercial_use_authorized", False
    ):
        reasons.append("LICENSE_SCOPE_INCOMPATIBLE")
    identity = record.get("chemical_identity")
    if not isinstance(identity, Mapping):
        reasons.append("SOURCE_IDENTITY_CONFLICT")
        identity = {}
    if identity.get("identity_status") == "CONFLICT":
        reasons.extend(["SOURCE_IDENTITY_CONFLICT", "CAS_NAME_CONFLICT"])
    elif identity.get("identity_status") != "EXACT":
        reasons.append("STOCK_IDENTITY_NOT_EXACT")
    if (
        identity.get("canonical_name") != requested_context.get("canonical_name")
        or identity.get("canonical_cas") != requested_context.get("canonical_cas")
        or requested_context.get("material_id")
        not in record.get("applicability", {}).get("exact_material_ids", [])
    ):
        reasons.append("STOCK_IDENTITY_NOT_EXACT")
    input_contract = record.get("input_contract")
    if not isinstance(input_contract, Mapping) or (
        input_contract.get("physical_quantity") != "GAS_MASS_CONCENTRATION"
        or input_contract.get("phase") != "AIR"
        or input_contract.get("unit") != "ug/L_air"
        or input_contract.get("log_base") != 10
        or input_contract.get("extrapolation_authorized") is not False
    ):
        reasons.append("UNIT_NOT_GAS_UG_L_AIR")
    if requested_context.get("physical_quantity") != "GAS_MASS_CONCENTRATION" or (
        requested_context.get("phase") != "AIR"
        or requested_context.get("unit") != "ug/L_air"
    ):
        reasons.append("UNIT_NOT_GAS_UG_L_AIR")
    curve = record.get("curve")
    if not isinstance(curve, Mapping):
        reasons.append("CURVE_PARAMETERS_MISSING")
        curve = {}
    try:
        imax = float(curve.get("imax"))
        midpoint = float(curve.get("midpoint_log10_ug_l"))
        slope = float(curve.get("slope"))
    except (TypeError, ValueError):
        imax = midpoint = slope = math.nan
    if not all(math.isfinite(value) for value in (imax, midpoint, slope)):
        reasons.append("CURVE_PARAMETERS_NONFINITE")
    else:
        if slope <= 0:
            reasons.append("NONPOSITIVE_SLOPE")
        if imax <= 0:
            reasons.append("NONPOSITIVE_MAXIMUM")
        if imax <= 1.4:
            reasons.append("IMAX_NOT_ABOVE_LMS_1_4")
        if slope > 0 and imax > 1.4:
            threshold_ng_l = corrected_wakayama_threshold_ng_l(
                imax=imax,
                midpoint_log10_ug_l=midpoint,
                slope=slope,
            )
            roundtrip = measured_intensity_curve(
                threshold_ng_l / 1000.0,
                imax=imax,
                midpoint_log10_ug_l=midpoint,
                slope=slope,
            )
            if not math.isclose(roundtrip, 1.4, rel_tol=0.0, abs_tol=1e-12):
                reasons.append("CORRECTED_THRESHOLD_ROUNDTRIP_FAILED")
    if (
        curve.get("threshold_equation_revision")
        != "WAKAYAMA_DECEMBER_2020_CORRECTION"
        or curve.get("threshold_output_unit") != "ng/L_air"
        or curve.get("threshold_roundtrip_criterion") != 1.4
        or curve.get("threshold_roundtrip_tolerance") != 1e-12
    ):
        reasons.append("CORRECTED_THRESHOLD_CONTRACT_MISSING")
    applicability = record.get("applicability")
    if not isinstance(applicability, Mapping):
        reasons.append("APPLICABILITY_MISSING")
        applicability = {}
    concentration = requested_context.get("gas_ug_l_air")
    observed_range = applicability.get("observed_range_ug_l_air")
    if (
        isinstance(concentration, bool)
        or not isinstance(concentration, (int, float))
        or not math.isfinite(float(concentration))
        or float(concentration) < 0
    ):
        reasons.append("UNIT_NOT_GAS_UG_L_AIR")
    if (
        not isinstance(observed_range, (list, tuple))
        or len(observed_range) != 2
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) <= 0
            for value in observed_range
        )
    ):
        reasons.append("CONCENTRATION_OUTSIDE_SOURCE_RANGE")
    elif float(observed_range[0]) > float(observed_range[1]):
        reasons.append("CONCENTRATION_OUTSIDE_SOURCE_RANGE")
    elif concentration is not None and not (
        float(observed_range[0]) <= float(concentration) <= float(observed_range[1])
    ):
        reasons.append("CONCENTRATION_OUTSIDE_SOURCE_RANGE")
    for context_key, applicability_key, reason in (
        ("matrix", "matrices", "MATRIX_OUT_OF_DOMAIN"),
        ("delivery", "delivery_modes", "DELIVERY_OUT_OF_DOMAIN"),
        ("scenario", "scenarios", "SCENARIO_OUT_OF_DOMAIN"),
    ):
        admitted = applicability.get(applicability_key)
        if not isinstance(admitted, (list, tuple)) or requested_context.get(
            context_key
        ) not in admitted:
            reasons.append(reason)
    if requested_context.get("whole_natural") and not applicability.get(
        "whole_natural_transfer_authorized", False
    ):
        reasons.append("WHOLE_NATURAL_CALIBRATION_ABSENT")
    if requested_context.get("commercial_product") and not applicability.get(
        "commercial_product_transfer_authorized", False
    ):
        reasons.append("STOCK_IDENTITY_NOT_EXACT")
    if requested_context.get("full_perfume") and not applicability.get(
        "full_perfume_transfer_authorized", False
    ):
        reasons.append("FULL_FORMULA_TRANSFER_NOT_ESTABLISHED")
    uncertainty = record.get("uncertainty")
    if not isinstance(uncertainty, Mapping):
        reasons.append("UNCERTAINTY_METHOD_UNAVAILABLE")
        uncertainty = {}
    else:
        if uncertainty.get("coefficient_rounding_known"):
            caveats.append("ROUNDED_SOURCE_COEFFICIENTS")
        if str(uncertainty.get("prediction_interval_method", "")).upper() in {
            "",
            "UNAVAILABLE",
            "UNKNOWN",
        }:
            caveats.append("UNCERTAINTY_METHOD_UNAVAILABLE")
    if record.get("source_fit_overlap") == "UNKNOWN":
        caveats.append("SOURCE_FIT_OVERLAP_UNKNOWN")
    endpoint_authority = record.get("endpoint_authority")
    required_endpoint_flags = {
        "character",
        "intensity",
        "pleasantness",
        "personal_liking",
        "population_liking",
        "beauty",
        "formula_optimization_authority",
    }
    if not isinstance(endpoint_authority, Mapping) or not required_endpoint_flags.issubset(
        endpoint_authority
    ):
        reasons.append("ENDPOINT_AUTHORITY_MISSING")
    elif (
        endpoint_authority.get("character") is not False
        or endpoint_authority.get("pleasantness") is not False
        or endpoint_authority.get("personal_liking") is not False
        or endpoint_authority.get("population_liking") is not False
        or endpoint_authority.get("beauty") is not False
        or endpoint_authority.get("formula_optimization_authority") is not False
        or not (
            endpoint_authority.get("intensity") is True
            or endpoint_authority.get("intensity")
            == "CONDITIONAL_EXACT_SOURCE_DOMAIN_ONLY"
        )
    ):
        reasons.append("ENDPOINT_AUTHORITY_INVALID")
    action_authority = record.get("action_authority")
    if not isinstance(action_authority, Mapping) or any(
        action_authority.get(flag) is not False
        for flag in (
            "evidence_admission_authorized",
            "physical_experiment_authorized",
            "compounding_authorized",
            "purchase_authorized",
            "inventory_mutation_authorized",
            "safety_authorized",
            "release_authorized",
        )
    ):
        reasons.append("ACTION_AUTHORITY_NOT_FALSE")
    return {
        "status": "ADMITTED_INTENSITY_CURVE" if not reasons else "HOLD",
        "usable": not reasons,
        "reason_codes": sorted(set(reasons)),
        "caveat_codes": sorted(set(caveats)),
        "optimizer_selection_usable": not reasons
        and "UNCERTAINTY_METHOD_UNAVAILABLE" not in caveats
        and "SOURCE_FIT_OVERLAP_UNKNOWN" not in caveats,
        **MEASURED_INTENSITY_FALSE_AUTHORITIES,
    }


def resolve_measured_curve(
    capability: Mapping[str, Any],
    *,
    gas_ug_l_air: float,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate a capability only after the complete gas-domain admission."""

    request = {
        **dict(context),
        "physical_quantity": "GAS_MASS_CONCENTRATION",
        "phase": "AIR",
        "unit": "ug/L_air",
        "gas_ug_l_air": gas_ug_l_air,
    }
    admission = validate_measured_intensity_capability(capability, request)
    if not admission["usable"]:
        return {"intensity": None, "admission": admission}
    curve = capability["curve"]
    return {
        "intensity": measured_intensity_curve(
            gas_ug_l_air,
            imax=float(curve["imax"]),
            midpoint_log10_ug_l=float(curve["midpoint_log10_ug_l"]),
            slope=float(curve["slope"]),
        ),
        "admission": admission,
    }


def partial_addition_intensity(
    component_intensities: Sequence[float], *, lambda_: float, upper_bound: float
) -> float:
    """Strongest component plus a fitted fraction of remaining intensity."""

    values = tuple(float(value) for value in component_intensities)
    if (
        not values
        or any(not math.isfinite(value) or value < 0 for value in values)
        or not math.isfinite(lambda_)
        or not 0 <= lambda_ <= 1
        or not math.isfinite(upper_bound)
        or upper_bound <= 0
    ):
        raise ValueError("Finite intensities, lambda in [0,1], and upper bound required")
    maximum = max(values)
    return min(upper_bound, maximum + lambda_ * (math.fsum(values) - maximum))


def fit_partial_addition_lambda(training_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Fit only lambda using equal mixture-group weighting.

    No held-out labels or curve parameters are accepted by this function.  The
    convex piecewise-quadratic objective is solved deterministically; equal
    minima choose the smaller lambda.
    """

    rows = []
    for row in training_rows:
        intensities = tuple(float(value) for value in row["component_intensities"])
        observed = float(row["observed"])
        upper = float(row["upper_bound"])
        group = str(row["group_id"])
        if (
            not group
            or not intensities
            or any(not math.isfinite(value) or value < 0 for value in intensities)
            or not math.isfinite(observed)
            or not math.isfinite(upper)
            or upper <= 0
        ):
            raise ValueError("Invalid partial-addition training row")
        maximum = max(intensities)
        remainder = math.fsum(intensities) - maximum
        rows.append((group, maximum, remainder, upper, observed))
    group_ids = sorted({row[0] for row in rows})
    positive_remainders = {round(row[2], 12) for row in rows if row[2] > 0}
    if len(group_ids) < 3 or len(positive_remainders) < 2:
        return {
            "status": "HOLD_PARTIAL_ADDITION_IDENTIFIABILITY",
            "lambda": None,
            "training_groups": group_ids,
            "reason": "INSUFFICIENT_GROUPS_OR_ADDITIVE_POTENTIAL_VARIATION",
        }
    counts = {group: sum(row[0] == group for row in rows) for group in group_ids}

    def objective(lambda_value: float) -> float:
        return math.fsum(
            (
                min(upper, maximum + lambda_value * remainder) - observed
            )
            ** 2
            / (len(group_ids) * counts[group])
            for group, maximum, remainder, upper, observed in rows
        )

    breakpoints = {0.0, 1.0}
    for _, maximum, remainder, upper, _ in rows:
        if remainder > 0:
            breakpoints.add(max(0.0, min(1.0, (upper - maximum) / remainder)))
    ordered = sorted(breakpoints)
    candidates = set(ordered)
    for low, high in zip(ordered, ordered[1:]):
        midpoint = (low + high) / 2
        numerator = denominator = 0.0
        for group, maximum, remainder, upper, observed in rows:
            weight = 1.0 / (len(group_ids) * counts[group])
            if maximum + midpoint * remainder < upper and remainder > 0:
                numerator += weight * remainder * (observed - maximum)
                denominator += weight * remainder * remainder
        if denominator > 0:
            candidates.add(max(low, min(high, numerator / denominator)))
    scored = sorted((objective(value), value) for value in candidates)
    best_objective = scored[0][0]
    best_lambda = min(
        value
        for score, value in scored
        if math.isclose(score, best_objective, rel_tol=0.0, abs_tol=1e-15)
    )
    return {
        "status": "FITTED_DEVELOPMENT_ONLY",
        "lambda": best_lambda,
        "training_macro_group_mse": best_objective,
        "training_groups": group_ids,
        "empirical_admission": "HOLD",
        **MEASURED_INTENSITY_FALSE_AUTHORITIES,
    }


def measured_mixture_intensity_challengers(
    gas_ug_l_by_cas: Mapping[str, float],
    curves: Mapping[str, Mapping[str, float]],
    *,
    partial_addition_lambda: float | None,
    upper_bound: float,
) -> dict[str, Any]:
    """Return separate SC, partial-addition and primacy predictions."""

    active = {cas: float(value) for cas, value in gas_ug_l_by_cas.items() if value > 0}
    missing = sorted(set(active) - set(curves))
    base = {
        "missing_calibrations": missing,
        "models_averaged": False,
        "predicted_liking": None,
        **MEASURED_INTENSITY_FALSE_AUTHORITIES,
    }
    if missing:
        return {
            **base,
            "status": "HOLD_MISSING_COMPONENT_CALIBRATION",
            "strongest_component": None,
            "partial_addition": None,
            "primacy_transfer": None,
        }
    component_intensities = {
        cas: measured_intensity_curve(value, **curves[cas])
        for cas, value in active.items()
    }
    strongest = max(component_intensities.values(), default=0.0)
    partial = (
        partial_addition_intensity(
            tuple(component_intensities.values()),
            lambda_=partial_addition_lambda,
            upper_bound=upper_bound,
        )
        if partial_addition_lambda is not None
        else None
    )
    primacy = measured_mixture_intensity(
        dict(active), dict(curves), method="primacy"
    )
    return {
        **base,
        "status": "DIAGNOSTIC_MODELS_SEPARATE",
        "component_intensities": component_intensities,
        "strongest_component": {
            "intensity": strongest,
            "fit_parameters": 0,
        },
        "partial_addition": (
            {
                "intensity": partial,
                "lambda": partial_addition_lambda,
                "empirical_admission": "HOLD",
            }
            if partial is not None
            else {
                "intensity": None,
                "status": "HOLD_PARTIAL_ADDITION_NOT_FITTED",
            }
        ),
        "primacy_transfer": {
            "intensity": primacy["intensity"],
            "status": "EXTERNAL_TRANSFER",
        },
    }


def molecule_connected_mixture_groups(
    mixtures: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Join every mixture sharing a molecule into one leakage-safe component."""

    identifiers = [str(row["mixture_id"]) for row in mixtures]
    if len(identifiers) != len(set(identifiers)) or any(not item for item in identifiers):
        raise ValueError("mixture_id values must be non-empty and unique")
    parent = {identifier: identifier for identifier in identifiers}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    molecule_owner: dict[str, str] = {}
    for row in mixtures:
        mixture_id = str(row["mixture_id"])
        molecules = tuple(sorted({str(value).strip() for value in row["molecule_ids"]}))
        if not molecules or any(not molecule for molecule in molecules):
            raise ValueError("Every mixture requires non-empty molecule identities")
        for molecule in molecules:
            if molecule in molecule_owner:
                union(mixture_id, molecule_owner[molecule])
            else:
                molecule_owner[molecule] = mixture_id
    components: dict[str, list[str]] = {}
    for identifier in identifiers:
        components.setdefault(find(identifier), []).append(identifier)
    ordered = sorted(tuple(sorted(values)) for values in components.values())
    groups = {
        mixture_id: f"mcg-{index:03d}"
        for index, values in enumerate(ordered, start=1)
        for mixture_id in values
    }
    status = (
        "LEAKAGE_SAFE_GROUPS_AVAILABLE"
        if len(ordered) >= 3
        else "HOLD_INSUFFICIENT_LEAKAGE_SAFE_GROUPS"
    )
    return {
        "status": status,
        "group_count": len(ordered),
        "groups": groups,
        "components": [list(values) for values in ordered],
    }


def _rank_values(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and values[order[end]] == values[order[cursor]]:
            end += 1
        rank = (cursor + 1 + end) / 2
        for position in order[cursor:end]:
            ranks[position] = rank
        cursor = end
    return ranks


def _spearman(observed: Sequence[float], predicted: Sequence[float]) -> float | None:
    if len(observed) < 2 or len(observed) != len(predicted):
        return None
    left, right = _rank_values(observed), _rank_values(predicted)
    left_mean = math.fsum(left) / len(left)
    right_mean = math.fsum(right) / len(right)
    numerator = math.fsum(
        (a - left_mean) * (b - right_mean) for a, b in zip(left, right)
    )
    denominator = math.sqrt(
        math.fsum((value - left_mean) ** 2 for value in left)
        * math.fsum((value - right_mean) ** 2 for value in right)
    )
    return None if denominator == 0 else numerator / denominator


def _grouped_metrics(rows: Sequence[Mapping[str, Any]], model: str) -> dict[str, Any]:
    usable = [row for row in rows if row.get(model) is not None]
    grouped: dict[str, list[tuple[float, float]]] = {}
    for row in usable:
        grouped.setdefault(str(row["connected_group_id"]), []).append(
            (float(row["observed"]), float(row[model]))
        )
    group_rmse = {
        group: math.sqrt(
            math.fsum((prediction - observed) ** 2 for observed, prediction in pairs)
            / len(pairs)
        )
        for group, pairs in grouped.items()
    }
    errors = [
        prediction - observed
        for row in usable
        for observed, prediction in [(float(row["observed"]), float(row[model]))]
    ]
    absolute = sorted(abs(value) for value in errors)
    median = (
        None
        if not absolute
        else absolute[len(absolute) // 2]
        if len(absolute) % 2
        else (absolute[len(absolute) // 2 - 1] + absolute[len(absolute) // 2]) / 2
    )
    observed = [float(row["observed"]) for row in usable]
    predicted = [float(row[model]) for row in usable]
    return {
        "macro_group_weighted_rmse": (
            math.fsum(group_rmse.values()) / len(group_rmse) if group_rmse else None
        ),
        "pooled_rmse": (
            math.sqrt(math.fsum(value * value for value in errors) / len(errors))
            if errors
            else None
        ),
        "mae": (
            math.fsum(abs(value) for value in errors) / len(errors) if errors else None
        ),
        "median_absolute_error": median,
        "bias": math.fsum(errors) / len(errors) if errors else None,
        "per_group_rmse": group_rmse,
        "worst_group_rmse": max(group_rmse.values()) if group_rmse else None,
        "spearman_rank_correlation": _spearman(observed, predicted),
        "valid_prediction_count": len(usable),
        "observation_count": len(rows),
        "valid_prediction_coverage": len(usable) / len(rows) if rows else 0.0,
        "independent_group_count": len(group_rmse),
    }


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("Cannot calculate a percentile of an empty sample")
    position = probability * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    fraction = position - low
    return ordered[low] * (1 - fraction) + ordered[high] * fraction


def benchmark_grouped_mixture_intensity_challengers(
    rows: Sequence[Mapping[str, Any]],
    curves: Mapping[str, Mapping[str, float]],
    *,
    upper_bound: float,
    bootstrap_draws: int = 20_000,
    bootstrap_seed: int = 20260923,
) -> dict[str, Any]:
    """Leakage-safe, offline comparison of the three separate mixture rules.

    Rows sharing a molecule are held out together. Partial addition fits one
    lambda inside each training fold. The routine reports comparison evidence
    but deliberately leaves empirical admission on HOLD.
    """

    import random

    if (
        not rows
        or isinstance(bootstrap_draws, bool)
        or bootstrap_draws < 1
        or not math.isfinite(float(upper_bound))
        or upper_bound <= 0
    ):
        raise ValueError("Rows, positive upper bound, and bootstrap draws required")
    series: dict[str, tuple[str, ...]] = {}
    normalized_rows: list[dict[str, Any]] = []
    for index, source in enumerate(rows):
        mixture_id = str(source["mixture_id"]).strip()
        molecules = tuple(sorted({str(value).strip() for value in source["molecule_ids"]}))
        gases = {str(key): float(value) for key, value in source["gas_ug_l_by_cas"].items()}
        observed = float(source["observed"])
        if (
            not mixture_id
            or not molecules
            or any(not molecule for molecule in molecules)
            or set(gases) != set(molecules)
            or any(not math.isfinite(value) or value < 0 for value in gases.values())
            or not any(value > 0 for value in gases.values())
            or not math.isfinite(observed)
        ):
            raise ValueError("Invalid grouped mixture-intensity row")
        if mixture_id in series and series[mixture_id] != molecules:
            raise ValueError("One mixture series cannot change chemical identity")
        series[mixture_id] = molecules
        normalized_rows.append(
            {
                "row_id": str(source.get("row_id", f"row-{index + 1}")),
                "mixture_id": mixture_id,
                "molecule_ids": molecules,
                "gas_ug_l_by_cas": gases,
                "observed": observed,
            }
        )
    grouping = molecule_connected_mixture_groups(
        [
            {"mixture_id": mixture_id, "molecule_ids": molecules}
            for mixture_id, molecules in sorted(series.items())
        ]
    )
    split_key = sha256(
        json.dumps(
            {
                "schema": "molecule-connected-mixture-split-v1",
                "series": sorted((key, list(value)) for key, value in series.items()),
                "groups": grouping["groups"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if grouping["status"] != "LEAKAGE_SAFE_GROUPS_AVAILABLE":
        return {
            "status": "HOLD_INSUFFICIENT_LEAKAGE_SAFE_GROUPS",
            "split_key_sha256": split_key,
            "grouping": grouping,
            "winner": None,
            "empirical_admission": "HOLD",
            **MEASURED_INTENSITY_FALSE_AUTHORITIES,
        }
    missing = sorted(
        {
            molecule
            for row in normalized_rows
            for molecule, gas in row["gas_ug_l_by_cas"].items()
            if gas > 0 and molecule not in curves
        }
    )
    if missing:
        return {
            "status": "HOLD_MISSING_COMPONENT_CALIBRATION",
            "missing_calibrations": missing,
            "split_key_sha256": split_key,
            "grouping": grouping,
            "winner": None,
            "empirical_admission": "HOLD",
            **MEASURED_INTENSITY_FALSE_AUTHORITIES,
        }
    for row in normalized_rows:
        row["connected_group_id"] = grouping["groups"][row["mixture_id"]]
        row["component_intensities"] = [
            measured_intensity_curve(row["gas_ug_l_by_cas"][molecule], **curves[molecule])
            for molecule in row["molecule_ids"]
        ]
    connected_groups = sorted(set(grouping["groups"].values()))
    fold_receipts = []
    predictions = []
    for held_out in connected_groups:
        training = [row for row in normalized_rows if row["connected_group_id"] != held_out]
        fit = fit_partial_addition_lambda(
            [
                {
                    "group_id": row["connected_group_id"],
                    "component_intensities": row["component_intensities"],
                    "observed": row["observed"],
                    "upper_bound": upper_bound,
                }
                for row in training
            ]
        )
        fold_receipts.append(
            {
                "held_out_group": held_out,
                "training_groups": sorted(
                    {row["connected_group_id"] for row in training}
                ),
                "lambda_fit": fit,
            }
        )
        for row in normalized_rows:
            if row["connected_group_id"] != held_out:
                continue
            comparison = measured_mixture_intensity_challengers(
                row["gas_ug_l_by_cas"],
                curves,
                partial_addition_lambda=fit.get("lambda"),
                upper_bound=upper_bound,
            )
            predictions.append(
                {
                    "row_id": row["row_id"],
                    "mixture_id": row["mixture_id"],
                    "connected_group_id": held_out,
                    "observed": row["observed"],
                    "strongest_component": comparison["strongest_component"]["intensity"],
                    "partial_addition": comparison["partial_addition"].get("intensity"),
                    "primacy_transfer": comparison["primacy_transfer"]["intensity"],
                }
            )
    models = ("strongest_component", "partial_addition", "primacy_transfer")
    metrics = {model: _grouped_metrics(predictions, model) for model in models}
    equal_coverage = len(
        {metrics[model]["valid_prediction_count"] for model in models}
    ) == 1
    rng = random.Random(bootstrap_seed)
    group_losses = {
        model: metrics[model]["per_group_rmse"] for model in models
    }
    pairwise = {}
    for left_index, left in enumerate(models):
        for right in models[left_index + 1 :]:
            common_groups = sorted(
                set(group_losses[left]) & set(group_losses[right])
            )
            if set(common_groups) != set(connected_groups):
                pairwise[f"{left}_minus_{right}"] = {
                    "clustered_group_bootstrap_draws": 0,
                    "seed": bootstrap_seed,
                    "interval_95": None,
                    "status": "UNEQUAL_VALID_COVERAGE",
                }
                continue
            draws = []
            for _ in range(bootstrap_draws):
                sampled = [rng.choice(common_groups) for _ in common_groups]
                draws.append(
                    math.fsum(
                        group_losses[left][group] - group_losses[right][group]
                        for group in sampled
                    )
                    / len(sampled)
                )
            pairwise[f"{left}_minus_{right}"] = {
                "clustered_group_bootstrap_draws": bootstrap_draws,
                "seed": bootstrap_seed,
                "interval_95": [_percentile(draws, 0.025), _percentile(draws, 0.975)],
            }
    lambda_draws = []
    by_group = {
        group: [row for row in normalized_rows if row["connected_group_id"] == group]
        for group in connected_groups
    }
    for _ in range(bootstrap_draws):
        sampled_groups = [rng.choice(connected_groups) for _ in connected_groups]
        sampled_rows = []
        for occurrence, group in enumerate(sampled_groups):
            for row in by_group[group]:
                sampled_rows.append(
                    {
                        "group_id": f"bootstrap-{occurrence}-{group}",
                        "component_intensities": row["component_intensities"],
                        "observed": row["observed"],
                        "upper_bound": upper_bound,
                    }
                )
        fit = fit_partial_addition_lambda(sampled_rows)
        if fit.get("lambda") is not None:
            lambda_draws.append(float(fit["lambda"]))
    identifiable = all(
        fold["lambda_fit"].get("lambda") is not None for fold in fold_receipts
    )
    status = (
        "MODEL_COMPARISON_UNRESOLVED"
        if not equal_coverage or not identifiable
        else "MODEL_COMPARISON_EVALUATED_ADMISSION_HOLD"
    )
    return {
        "status": status,
        "primary_metric": "macro_group_weighted_rmse",
        "split_key_sha256": split_key,
        "grouping": grouping,
        "folds": fold_receipts,
        "predictions": predictions,
        "metrics": metrics,
        "pairwise_clustered_uncertainty": pairwise,
        "partial_addition_lambda_bootstrap": {
            "draws_requested": bootstrap_draws,
            "identifiable_draws": len(lambda_draws),
            "interval_95": (
                [_percentile(lambda_draws, 0.025), _percentile(lambda_draws, 0.975)]
                if lambda_draws
                else None
            ),
        },
        "identical_held_out_rows": equal_coverage,
        "winner": None,
        "empirical_admission": "HOLD",
        **MEASURED_INTENSITY_FALSE_AUTHORITIES,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# Character Shift Data
# Each material defines concentration zones and their character descriptors
# Zones are cumulative (highest matching zone applies)
# conc_pct thresholds are % of CONCENTRATE (not finished product)
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class CharacterZone:
    """A concentration-dependent character region."""

    max_conc_pct: float  # upper limit of this zone (% in concentrate)
    character: str  # olfactive character in this zone
    quality: str  # "positive", "neutral", "negative", "dangerous"


CHARACTER_SHIFT_DATA: dict[str, list[CharacterZone]] = {
    # ── Animalics / trace materials ──
    "Indole": [
        CharacterZone(0.05, "transparent jasmine-floral lift", "positive"),
        CharacterZone(0.2, "narcotic floral, slightly animalic", "positive"),
        CharacterZone(0.5, "animalic, mothball, ink", "neutral"),
        CharacterZone(2.0, "fecal, skatolic, overwhelming", "dangerous"),
    ],
    "Isobutyl Quinoline": [
        CharacterZone(0.05, "dirty leather undertone", "positive"),
        CharacterZone(0.2, "dark leather, animalistic", "positive"),
        CharacterZone(0.5, "harsh quinoline, chemical", "negative"),
    ],
    "Guaiacol": [
        CharacterZone(0.03, "smoky depth, leather warmth", "positive"),
        CharacterZone(0.1, "creosote, phenolic", "neutral"),
        CharacterZone(0.5, "medicinal, sharp, overwhelming", "dangerous"),
    ],
    # ── Aldehydes ──
    "Aldehyde C10": [
        CharacterZone(0.05, "waxy sparkle, citrus peel", "positive"),
        CharacterZone(0.3, "orange-peel, slightly soapy", "positive"),
        CharacterZone(1.0, "waxy-candle, metallic", "neutral"),
        CharacterZone(3.0, "soapy, tallow, rancid", "negative"),
    ],
    "Aldehyde C11": [
        CharacterZone(0.05, "clean, fresh, soapy lift", "positive"),
        CharacterZone(0.3, "waxy, aldehydic body", "positive"),
        CharacterZone(1.0, "heavy waxy, detergent", "neutral"),
        CharacterZone(3.0, "overwhelming, chemical soapy", "negative"),
    ],
    "Aldehyde C12 MNA": [
        CharacterZone(0.05, "metallic sparkle, amber warmth", "positive"),
        CharacterZone(0.3, "amber-metallic, powdery", "positive"),
        CharacterZone(1.0, "soapy, laundry", "neutral"),
    ],
    "Cyclamen Aldehyde": [
        CharacterZone(0.1, "green-metallic floral", "positive"),
        CharacterZone(0.5, "cucumber, hyacinth", "positive"),
        CharacterZone(1.5, "sharp, chemical, metallic overload", "negative"),
    ],
    "Hydroxycitronellal": [
        CharacterZone(0.2, "dewy, fresh linen, transparent", "positive"),
        CharacterZone(0.8, "sweet muguet, slightly waxy", "positive"),
        CharacterZone(2.0, "soapy, detergent-like", "neutral"),
        CharacterZone(5.0, "cloying, chemical laundry", "negative"),
    ],
    # ── Musks ──
    "Galaxolide": [
        CharacterZone(2.0, "clean musk, subtle skin", "positive"),
        CharacterZone(5.0, "sweet musk, laundry clean", "positive"),
        CharacterZone(15.0, "powdery-sweet, slightly synthetic", "neutral"),
        CharacterZone(30.0, "overwhelming, headache-inducing", "negative"),
    ],
    "Ethylene Brassylate": [
        CharacterZone(3.0, "subtle musk veil, skin-scent", "positive"),
        CharacterZone(8.0, "powdery musk, gentle fixative", "positive"),
        CharacterZone(20.0, "flat, monotone musk blanket", "neutral"),
    ],
    "Musk Ketone": [
        CharacterZone(0.5, "powdery, sweet musk, cosmetic", "positive"),
        CharacterZone(2.0, "classic musk, slightly powdery", "positive"),
        CharacterZone(5.0, "heavy, nitro-musk character", "neutral"),
    ],
    # ── Florals ──
    "Hedione": [
        CharacterZone(3.0, "radiance amplifier, transparent lift", "positive"),
        CharacterZone(10.0, "jasmine-green, full body", "positive"),
        CharacterZone(30.0, "dominant jasmine-hedione character", "neutral"),
        CharacterZone(50.0, "overwhelming, loses nuance", "negative"),
    ],
    "Phenethyl Alcohol": [
        CharacterZone(1.0, "rose-petal transparency", "positive"),
        CharacterZone(3.0, "full rose, honey undertone", "positive"),
        CharacterZone(8.0, "yeasty, bread-dough, fermented", "negative"),
    ],
    # ── Woods ──
    "Iso E Super": [
        CharacterZone(3.0, "transparent woody veil, skin-scent", "positive"),
        CharacterZone(8.0, "molecular cocoon, cedar-amber", "positive"),
        CharacterZone(20.0, "dominant abstract-wood, monotone", "neutral"),
        CharacterZone(40.0, "flat, loses all other materials", "negative"),
    ],
    "Cashmeran": [
        CharacterZone(0.5, "woody-musky warmth, cashmere", "positive"),
        CharacterZone(2.0, "dense wood-amber, musky", "positive"),
        CharacterZone(5.0, "overwhelming, sweet-chemical", "negative"),
    ],
    # ── Balsamic / gourmand ──
    "Vanillin": [
        CharacterZone(0.5, "warm vanilla sweetness", "positive"),
        CharacterZone(2.0, "rich vanilla, balsamic", "positive"),
        CharacterZone(5.0, "cloying sweet, confectionery", "neutral"),
        CharacterZone(10.0, "synthetic, harsh vanilla", "negative"),
    ],
    "Ethyl Vanillin": [
        CharacterZone(0.3, "intense vanilla, sweeter than vanillin", "positive"),
        CharacterZone(1.0, "rich vanilla-cream", "positive"),
        CharacterZone(3.0, "overpowering sweet, chemical", "negative"),
    ],
    "Coumarin": [
        CharacterZone(0.5, "tonka-hay transparency", "positive"),
        CharacterZone(2.0, "rich coumarinic, tobacco warmth", "positive"),
        CharacterZone(4.0, "heavy, slightly bitter", "neutral"),
    ],
    # Heliotropal (piperonal): benzodioxole aldehyde, heliotrope-almond-vanilla.
    # At subliminal doses activates OR5A1/OR5A2 → sweet-powdery subliminal warmth.
    # At moderate doses → full heliotrope character. Overdose → cloying powdery-chemical.
    # Lower VP than Heliotropin (less volatile), deeper fixative quality.
    "Heliotropal": [
        CharacterZone(0.5, "subliminal sweet-almond warmth, powdery depth", "positive"),
        CharacterZone(2.0, "full heliotrope, cherry-almond, violet-powder", "positive"),
        CharacterZone(5.0, "dense heliotrope powder, starts to dominate", "neutral"),
        CharacterZone(10.0, "cloying sweet-powder, chemical-aldehyde", "negative"),
    ],
    # ── Terpene alcohols ──
    # Ethyl Linalool (3,7-dimethyl-1,6-octadien-3-ol ethyl ether):
    # Cleaner, sharper than linalool — more transparent, less sweet.
    # At moderate dose: crisp floral-citrus lift. Overdose: chemical-etherish.
    "Ethyl Linalool": [
        CharacterZone(1.0, "clean citrus-floral, sharper linalool", "positive"),
        CharacterZone(3.0, "transparent terpene-ether, floral body", "positive"),
        CharacterZone(8.0, "chemical-etherish, loses floral quality", "neutral"),
        CharacterZone(15.0, "harsh solvent-ether, flat terpenic", "negative"),
    ],
    # ── Green ──
    "Dynascone": [
        CharacterZone(0.01, "green galbanum freshness", "positive"),
        CharacterZone(0.05, "intense green, stem-like", "positive"),
        CharacterZone(0.2, "overwhelming green bomb, harsh", "dangerous"),
    ],
    "cis-3-Hexenol": [
        CharacterZone(0.1, "fresh cut grass, natural green", "positive"),
        CharacterZone(0.5, "crushed leaves, vegetal", "positive"),
        CharacterZone(1.5, "harsh, acetaldehyde-like", "negative"),
    ],
    # ── Fresh/aquatic terpene alcohols ──
    # Dihydromyrcenol is a hydrated myrcene — at low dose the hydroxyl
    # group drives the percept (clean-citrus-muguet, the Cool Water effect).
    # At overdose or after nose adapts to the fresh topnote, the terpenic
    # hydrocarbon backbone dominates → petroleum/gasoline/paraffin character.
    # Classic "Cool Water gone bad" inversion.
    "Dihydromyrcenol": [
        CharacterZone(1.0, "clean citrus-muguet lift, lime peel", "positive"),
        CharacterZone(4.0, "fresh cologne-soapy, lily-of-valley", "positive"),
        CharacterZone(10.0, "waxy-terpenic, adaptation residual", "neutral"),
        CharacterZone(20.0, "petroleum/gasoline hydrocarbon backbone exposed", "negative"),
        CharacterZone(40.0, "kerosene-paraffin, raw terpenic solvent", "dangerous"),
    ],
    # ── Smoke / leather ──
    "Birch Tar Rectified": [
        CharacterZone(0.02, "subtle campfire smoke", "positive"),
        CharacterZone(0.1, "leather-smoke, Russian leather", "positive"),
        CharacterZone(0.3, "overwhelming creosote, tarry", "dangerous"),
    ],
    # ── Ozonic ──
    "Calone": [
        CharacterZone(0.01, "watermelon-marine transparency", "positive"),
        CharacterZone(0.05, "marine-ozonic, sea breeze", "positive"),
        CharacterZone(0.2, "synthetic, harsh melon", "negative"),
    ],
    "Scentenal": [
        CharacterZone(0.02, "metallic green ozone, mineral", "positive"),
        CharacterZone(0.1, "intense metal-green, unusual", "positive"),
        CharacterZone(0.3, "aggressive, headache-inducing", "negative"),
    ],
    # ── Spice ──
    "Eugenol": [
        CharacterZone(0.1, "warm spice, clove nuance", "positive"),
        CharacterZone(0.5, "clove-spice, dental", "positive"),
        CharacterZone(1.5, "dental office, numbing, harsh", "negative"),
    ],
    # ── Fruity ──
    "Paradisamide": [
        CharacterZone(0.1, "tropical-fruity modifier, guava", "positive"),
        CharacterZone(0.5, "passion fruit, cassis, rhubarb", "positive"),
        CharacterZone(2.0, "sulfurous-catty undertone", "neutral"),
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# Hill Equation Parameters
# For each material: EC50 (% producing half-max response), n (steepness)
# ═══════════════════════════════════════════════════════════════════════════════

HILL_PARAMS: dict[str, dict[str, float]] = {
    "Indole": {"EC50": 0.08, "n": 2.5, "Rmax": 1.0},
    "Guaiacol": {"EC50": 0.05, "n": 3.0, "Rmax": 1.0},
    "Isobutyl Quinoline": {"EC50": 0.1, "n": 2.0, "Rmax": 1.0},
    "Aldehyde C10": {"EC50": 0.2, "n": 1.5, "Rmax": 1.0},
    "Aldehyde C11": {"EC50": 0.2, "n": 1.5, "Rmax": 1.0},
    "Cyclamen Aldehyde": {"EC50": 0.3, "n": 1.8, "Rmax": 1.0},
    "Galaxolide": {"EC50": 5.0, "n": 1.2, "Rmax": 1.0},
    "Iso E Super": {"EC50": 5.0, "n": 1.0, "Rmax": 1.0},
    "Hedione": {"EC50": 8.0, "n": 1.0, "Rmax": 1.0},
    "Vanillin": {"EC50": 2.0, "n": 1.5, "Rmax": 1.0},
    "Coumarin": {"EC50": 1.5, "n": 1.3, "Rmax": 1.0},
    "Dynascone": {"EC50": 0.03, "n": 3.0, "Rmax": 1.0},
    "Calone": {"EC50": 0.03, "n": 3.5, "Rmax": 1.0},
    "Scentenal": {"EC50": 0.05, "n": 2.8, "Rmax": 1.0},
    "Birch Tar Rectified": {"EC50": 0.05, "n": 3.0, "Rmax": 1.0},
    "cis-3-Hexenol": {"EC50": 0.3, "n": 1.5, "Rmax": 1.0},
    "Eugenol": {"EC50": 0.3, "n": 1.8, "Rmax": 1.0},
    "Phenethyl Alcohol": {"EC50": 2.0, "n": 1.2, "Rmax": 1.0},
    "Cashmeran": {"EC50": 1.5, "n": 1.5, "Rmax": 1.0},
    "Ethyl Vanillin": {"EC50": 0.8, "n": 1.8, "Rmax": 1.0},
    "Paradisamide": {"EC50": 0.3, "n": 1.8, "Rmax": 1.0},
    "Hydroxycitronellal": {"EC50": 0.5, "n": 1.5, "Rmax": 1.0},
    # Dihydromyrcenol: gradual dose response, relatively high ODT in
    # concentrate terms. EC50 ~3% conc, gentle slope (n=1.2) — why it's
    # used at 5-15% as a workhorse before the hydrocarbon inversion hits.
    "Dihydromyrcenol": {"EC50": 3.0, "n": 1.2, "Rmax": 1.0},
    # Heliotropal: moderate sensitivity, gentle slope — sweet materials
    # need higher concentrations to trigger character shift
    "Heliotropal": {"EC50": 1.5, "n": 1.5, "Rmax": 1.0},
    # Ethyl Linalool: similar profile to linalool but slightly higher threshold
    "Ethyl Linalool": {"EC50": 2.0, "n": 1.3, "Rmax": 1.0},
}


# Validate Hill parameters at module load
for _hp_name, _hp_vals in HILL_PARAMS.items():
    assert 0.5 <= _hp_vals["n"] <= 5.0, (
        f"Hill coefficient n={_hp_vals['n']} for {_hp_name} outside valid range [0.5, 5.0]"
    )
    assert _hp_vals["EC50"] > 0, f"EC50 must be positive for {_hp_name}"
del _hp_name, _hp_vals

# Pre-build normalized indexes for cross-module lookups
from engine.name_utils import normalize_name as _nn  # noqa: E402  # sys.path

_HILL_INDEX: dict[str, dict[str, float]] = {_nn(k): v for k, v in HILL_PARAMS.items()}
_CHAR_SHIFT_INDEX: dict[str, list[CharacterZone]] = {
    _nn(k): v for k, v in CHARACTER_SHIFT_DATA.items()
}
del _nn


def _hill_response(conc_pct: float, ec50: float, n: float, rmax: float = 1.0) -> float:
    """Hill equation sigmoid response."""
    if conc_pct <= 0:
        return 0.0
    return rmax * (conc_pct**n) / (ec50**n + conc_pct**n)


# ═══════════════════════════════════════════════════════════════════════════════
# Scoring
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class DoseResponseReport:
    """Dose-response analysis with character shift detection."""

    score: float  # 0-100 dosing quality
    overdosed: list[dict[str, Any]]  # materials in negative zone
    optimal: list[dict[str, Any]]  # materials in positive zone
    marginal: list[dict[str, Any]]  # materials in neutral zone
    character_map: dict[str, str]  # material → current character description
    hill_responses: dict[str, float]  # material → sigmoid response level (0-1)
    diagnostics: list[str]


def score_dose_response(
    ingredients: dict[str, float],
    dilutions: dict[str, float] | None = None,
    total_volume_ul: float = 10000.0,
) -> DoseResponseReport:
    """Score formula dosing quality based on character shift analysis.

    Args:
        ingredients: {name: amount_uL}
        dilutions: {name: dilution_factor} (1.0=neat, 0.1=10%, etc.)
        total_volume_ul: total batch volume in µL (default 10mL)

    Returns:
        DoseResponseReport with dosing quality score and character maps.
    """
    dilutions = dilutions or {}
    overdosed: list[dict] = []
    optimal: list[dict] = []
    marginal: list[dict] = []
    char_map: dict[str, str] = {}
    hill_map: dict[str, float] = {}
    diagnostics: list[str] = []
    penalties = 0.0
    bonuses = 0.0
    material_count = 0

    for name, amount in ingredients.items():
        dil = dilutions.get(name, 1.0)
        active_ul = amount * dil
        conc_pct = (active_ul / total_volume_ul) * 100.0

        # Character shift analysis — use normalized index
        from engine.name_utils import normalize_name

        norm = normalize_name(name)
        zones = _CHAR_SHIFT_INDEX.get(norm)
        if zones:
            material_count += 1
            current_char = zones[0].character
            current_quality = zones[0].quality

            for zone in zones:
                if conc_pct <= zone.max_conc_pct:
                    current_char = zone.character
                    current_quality = zone.quality
                    break
            else:
                # Above all defined zones — use the last one
                current_char = zones[-1].character
                current_quality = zones[-1].quality

            char_map[name] = current_char
            info = {
                "material": name,
                "conc_pct": round(conc_pct, 4),
                "character": current_char,
                "quality": current_quality,
            }

            if current_quality == "negative":
                overdosed.append(info)
                penalties += 25  # strong penalty — negative zone = character inversion
            elif current_quality == "dangerous":
                overdosed.append(info)
                penalties += 40  # catastrophic — fecal, kerosene, chemical burn
            elif current_quality == "positive":
                optimal.append(info)
                bonuses += 5
            else:  # neutral
                marginal.append(info)
                penalties += 3  # mild penalty — neutral zones waste material

        # Hill equation response level — use normalized index
        hill = _HILL_INDEX.get(norm)
        if hill:
            response = _hill_response(conc_pct, hill["EC50"], hill["n"], hill["Rmax"])
            hill_map[name] = round(response, 3)

    # Scoring
    if material_count == 0:
        return DoseResponseReport(
            score=75.0,
            overdosed=[],
            optimal=[],
            marginal=[],
            character_map={},
            hill_responses={},
            diagnostics=["No dose-response data for formula materials"],
        )

    # Base score from optimal dosing
    opt_ratio = len(optimal) / material_count if material_count > 0 else 0
    base_score = opt_ratio * 70 + 30  # 30-100 range

    # Penalty for overdosing
    score = base_score - penalties + min(bonuses, 20)
    score = max(0, min(100, score))

    # Diagnostics
    if overdosed:
        names = [f"{o['material']} ({o['conc_pct']:.3f}%: {o['character']})" for o in overdosed]
        diagnostics.append(f"⚠ OVERDOSED: {'; '.join(names)}")
    if optimal:
        diagnostics.append(f"✓ {len(optimal)} material(s) in optimal character zone")
    if not overdosed and material_count > 0:
        diagnostics.append("✓ All profiled materials within positive character range")

    # Check for narrow Hill responses (materials near EC50 — character transition)
    transitional = [n for n, r in hill_map.items() if 0.35 < r < 0.65]
    if transitional:
        diagnostics.append(
            f"ℹ Near character-shift boundary: {', '.join(transitional)} — "
            "small dose changes could shift perceived character"
        )

    return DoseResponseReport(
        score=round(score, 1),
        overdosed=overdosed,
        optimal=optimal,
        marginal=marginal,
        character_map=char_map,
        hill_responses=hill_map,
        diagnostics=diagnostics,
    )
