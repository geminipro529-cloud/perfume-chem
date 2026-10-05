"""Planning-only instrumental and sensory protocol builders.

The builders encode metadata and randomization contracts without reproducing
copyrighted standards text or authorizing a physical experiment.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Literal, Mapping, Sequence

from .contracts import FALSE_ACTION_AUTHORITY, stable_payload_hash

SensoryProtocolKind = Literal[
    "CHARACTER_PROFILE",
    "PAIRED_INTENSITY",
    "PAIRED_LIKING",
    "TRIANGLE_DISCRIMINATION",
    "THRESHOLD_ESTIMATION",
]

DEFAULT_PERSONAL_TIMEPOINTS_SECONDS = (300, 1800, 7200, 14400)


def _sha(value: str, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


@dataclass(frozen=True, slots=True)
class InstrumentalObservationContractV1:
    observation_id: str
    formula_sha256: str
    inventory_sha256: str
    stock_lot_sha256: str
    release_scenario_sha256: str
    preparation_receipt_sha256: str
    deposit_decimal: str
    deposit_unit: Literal["mg", "g", "uL", "mL"]
    matrix_id: str
    substrate_id: str
    temperature_k_decimal: str
    relative_humidity_decimal: str
    airflow_m_s_decimal: str
    surface_area_m2_decimal: str
    sampling_geometry_id: str
    sampling_method_id: str
    instrument_id: str
    calibration_receipt_sha256: str
    blank_receipt_sha256: str
    timepoints_seconds: tuple[int, ...]
    replicate_id: str
    session_id: str
    raw_data_sha256: str
    processed_result_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "observation_id",
            "matrix_id",
            "substrate_id",
            "sampling_geometry_id",
            "sampling_method_id",
            "instrument_id",
            "replicate_id",
            "session_id",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in (
            "formula_sha256",
            "inventory_sha256",
            "stock_lot_sha256",
            "release_scenario_sha256",
            "preparation_receipt_sha256",
            "calibration_receipt_sha256",
            "blank_receipt_sha256",
            "raw_data_sha256",
            "processed_result_sha256",
        ):
            _sha(getattr(self, name), name)
        points = tuple(self.timepoints_seconds)
        if not points or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in points
        ):
            raise ValueError("timepoints must be non-negative integer seconds")
        if tuple(sorted(set(points))) != points:
            raise ValueError("timepoints must be unique and increasing")
        object.__setattr__(self, "timepoints_seconds", points)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "instrumental-observation-contract-v1",
            **asdict(self),
            "observation_admitted": False,
            **FALSE_ACTION_AUTHORITY,
        }


@dataclass(frozen=True, slots=True)
class BlindingManifestV1:
    protocol_id: str
    session_codes: Mapping[str, Mapping[str, str]]
    closed_sessions: tuple[str, ...] = ()

    def public_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": "sensory-blinding-public-v1",
            "protocol_id": self.protocol_id,
            "sessions": {
                session_id: sorted(code_map)
                for session_id, code_map in sorted(self.session_codes.items())
            },
            "mapping_withheld_until_session_close": True,
            "mapping_sha256": stable_payload_hash(
                {
                    "protocol_id": self.protocol_id,
                    "session_codes": self.session_codes,
                }
            ),
            **FALSE_ACTION_AUTHORITY,
        }

    def reveal_session(self, session_id: str) -> dict[str, str]:
        if session_id not in self.closed_sessions:
            raise PermissionError("BLINDING_REMAINS_SEALED_UNTIL_SESSION_CLOSE")
        try:
            return dict(self.session_codes[session_id])
        except KeyError as exc:
            raise KeyError("unknown sensory session") from exc


def _codes(count: int, rng: random.Random) -> list[str]:
    population = [f"{value:03d}" for value in range(100, 1000)]
    return rng.sample(population, count)


def build_personal_sensory_protocol(
    candidate_formula_sha256: Mapping[str, str],
    *,
    protocol_id: str,
    kind: SensoryProtocolKind,
    session_ids: Sequence[str],
    seed: int,
    timepoints_seconds: Sequence[int] = DEFAULT_PERSONAL_TIMEPOINTS_SECONDS,
    repeats_per_pair: int = 3,
) -> tuple[dict[str, Any], BlindingManifestV1]:
    """Build a sealed, randomized protocol plan; do not authorize execution."""

    protocol_id = _text(protocol_id, "protocol_id")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    candidates = sorted(candidate_formula_sha256)
    if len(candidates) < 2 or len(candidates) > 5:
        raise ValueError("personal comparison protocols require two to five candidates")
    for candidate_id, digest in candidate_formula_sha256.items():
        _text(candidate_id, "candidate_id")
        _sha(digest, f"formula hash for {candidate_id}")
    sessions = tuple(_text(value, "session_id") for value in session_ids)
    if len(sessions) < 3 or len(set(sessions)) != len(sessions):
        raise ValueError("at least three unique sessions are required")
    points = tuple(timepoints_seconds)
    if points != DEFAULT_PERSONAL_TIMEPOINTS_SECONDS:
        raise ValueError("personal v1 protocol uses fixed 5m, 30m, 2h, and 4h timepoints")
    if repeats_per_pair < 3:
        raise ValueError("each relevant pair requires at least three repeats")

    pairwise_kind = kind in {"PAIRED_INTENSITY", "PAIRED_LIKING"}
    if pairwise_kind:
        pairs = list(itertools.combinations(candidates, 2))
    elif kind == "TRIANGLE_DISCRIMINATION":
        pairs = list(itertools.combinations(candidates, 2))
    else:
        pairs = []
    rng = random.Random(seed)
    session_codes: dict[str, dict[str, str]] = {}
    schedules: list[dict[str, Any]] = []
    pair_repeat_counter: dict[tuple[str, str], int] = {
        pair: 0 for pair in pairs
    }
    for session_index, session_id in enumerate(sessions):
        codes = _codes(len(candidates), rng)
        candidate_to_code = dict(zip(candidates, codes, strict=True))
        session_codes[session_id] = {
            code: candidate for candidate, code in candidate_to_code.items()
        }
        if pairs:
            ordered_pairs = list(pairs)
            rng.shuffle(ordered_pairs)
            for pair in ordered_pairs:
                if pair_repeat_counter[pair] >= repeats_per_pair:
                    continue
                left, right = pair
                presentation = [candidate_to_code[left], candidate_to_code[right]]
                rng.shuffle(presentation)
                pair_repeat_counter[pair] += 1
                schedules.append(
                    {
                        "session_id": session_id,
                        "pair_id": sha256("|".join(pair).encode("utf-8")).hexdigest()[:16],
                        "repeat_number": pair_repeat_counter[pair],
                        "blind_codes_in_presentation_order": presentation,
                        "timepoints_seconds": list(points),
                        "allow_tie": pairwise_kind,
                        "allow_cannot_determine": True,
                    }
                )
        else:
            presentation = list(codes)
            rng.shuffle(presentation)
            schedules.append(
                {
                    "session_id": session_id,
                    "blind_codes_in_presentation_order": presentation,
                    "timepoints_seconds": list(points),
                    "allow_cannot_determine": True,
                }
            )

    incomplete_pairs = [
        pair for pair, count in pair_repeat_counter.items() if count < repeats_per_pair
    ]
    plan = {
        "schema_version": "personal-sensory-protocol-plan-v1",
        "protocol_id": protocol_id,
        "protocol_kind": kind,
        "candidate_count": len(candidates),
        "session_count": len(sessions),
        "timepoints_seconds": list(points),
        "schedule": schedules,
        "all_pairwise_comparisons_required": pairwise_kind,
        "repeats_per_pair_required": repeats_per_pair if pairs else None,
        "pair_coverage_complete": not incomplete_pairs,
        "incomplete_pair_ids": ["|".join(pair) for pair in incomplete_pairs],
        "skin_and_blotter_pooling_allowed": False,
        "population_generalization_authorized": False,
        "physical_execution_authorized": False,
        "formula_action": "NO_CHANGE",
        **FALSE_ACTION_AUTHORITY,
    }
    plan["protocol_sha256"] = stable_payload_hash(plan)
    return plan, BlindingManifestV1(
        protocol_id=protocol_id,
        session_codes=session_codes,
    )


def build_reference_anchored_protocol(
    candidate_formula_sha256: Mapping[str, str],
    *,
    target_candidate_id: str,
    protocol_id: str,
    mode: str,
    session_ids: Sequence[str],
    seed: int,
    requested_descriptors: Sequence[str] = (),
    preserve_constraints: Sequence[str] = (),
    avoid_constraints: Sequence[str] = (),
) -> tuple[dict[str, Any], BlindingManifestV1]:
    """Build target-versus-reference schedules without reference-reference work.

    ``QUICK_REFERENCE`` is one exploratory personal session at five minutes
    and two hours.  ``CONTROLLED_REFERENCE`` uses at least three sessions,
    three repeats per target-reference pair, balanced AB/BA order, and the
    fixed personal-comparison timepoints.  Neither mode authorizes a physical
    test or a population claim.
    """

    protocol_id = _text(protocol_id, "protocol_id")
    target_candidate_id = _text(target_candidate_id, "target_candidate_id")
    if mode not in {"QUICK_REFERENCE", "CONTROLLED_REFERENCE"}:
        raise ValueError(f"unsupported reference protocol mode: {mode}")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    candidates = sorted(candidate_formula_sha256)
    if target_candidate_id not in candidate_formula_sha256:
        raise ValueError("target_candidate_id must be one of the supplied candidates")
    if not 2 <= len(candidates) <= 5:
        raise ValueError("reference protocols require one target and one to four references")
    for candidate_id, digest in candidate_formula_sha256.items():
        _text(candidate_id, "candidate_id")
        _sha(digest, f"formula hash for {candidate_id}")
    sessions = tuple(_text(value, "session_id") for value in session_ids)
    if len(set(sessions)) != len(sessions):
        raise ValueError("session IDs must be unique")
    if mode == "QUICK_REFERENCE":
        if len(sessions) != 1:
            raise ValueError("QUICK_REFERENCE requires exactly one session")
        timepoints = (300, 7200)
        repeats_per_pair = 1
    else:
        if len(sessions) < 3:
            raise ValueError("CONTROLLED_REFERENCE requires at least three sessions")
        timepoints = DEFAULT_PERSONAL_TIMEPOINTS_SECONDS
        repeats_per_pair = 3

    references = [candidate for candidate in candidates if candidate != target_candidate_id]
    pairs = [(target_candidate_id, reference) for reference in references]
    rng = random.Random(seed)
    session_codes: dict[str, dict[str, str]] = {}
    schedules: list[dict[str, Any]] = []
    pair_counts = {pair: 0 for pair in pairs}
    order_counts = {pair: {"TARGET_FIRST": 0, "REFERENCE_FIRST": 0} for pair in pairs}
    for session_index, session_id in enumerate(sessions):
        codes = _codes(len(candidates), rng)
        candidate_to_code = dict(zip(candidates, codes, strict=True))
        session_codes[session_id] = {
            code: candidate for candidate, code in candidate_to_code.items()
        }
        ordered_pairs = list(pairs)
        rng.shuffle(ordered_pairs)
        for target_id, reference_id in ordered_pairs:
            pair = (target_id, reference_id)
            if pair_counts[pair] >= repeats_per_pair:
                continue
            repeat_number = pair_counts[pair] + 1
            # Alternate each pair by its repeat number.  With three repeats,
            # each order differs by exactly one presentation regardless of
            # session numbering.
            target_first = (repeat_number + seed) % 2 == 0
            presentation_ids = (
                [target_id, reference_id]
                if target_first
                else [reference_id, target_id]
            )
            order_key = "TARGET_FIRST" if target_first else "REFERENCE_FIRST"
            pair_counts[pair] = repeat_number
            order_counts[pair][order_key] += 1
            schedules.append(
                {
                    "session_id": session_id,
                    "pair_id": sha256("|".join(pair).encode("utf-8")).hexdigest()[:16],
                    "target_candidate_id_withheld": True,
                    "reference_candidate_id_withheld": True,
                    "repeat_number": repeat_number,
                    "blind_codes_in_presentation_order": [
                        candidate_to_code[value] for value in presentation_ids
                    ],
                    "timepoints_seconds": list(timepoints),
                    "allow_tie": True,
                    "allow_cannot_determine": True,
                    "short_reason_required": mode == "QUICK_REFERENCE",
                }
            )

    incomplete = [pair for pair, count in pair_counts.items() if count < repeats_per_pair]
    order_balance = {
        "|".join(pair): counts for pair, counts in sorted(order_counts.items())
    }
    order_balanced = all(
        abs(counts["TARGET_FIRST"] - counts["REFERENCE_FIRST"]) <= 1
        for counts in order_counts.values()
    )
    endpoints = {
        "requested_descriptors": [str(value).strip() for value in requested_descriptors if str(value).strip()],
        "preserve_constraints": [str(value).strip() for value in preserve_constraints if str(value).strip()],
        "avoid_constraints": [str(value).strip() for value in avoid_constraints if str(value).strip()],
        "fixed": ["INTENSITY", "FAMILIARITY", "OVERALL_LIKING"],
    }
    plan = {
        "schema_version": "reference-anchored-sensory-protocol-v1",
        "protocol_id": protocol_id,
        "mode": mode,
        "result_scope": (
            "QUICK_PERSONAL_OBSERVATION"
            if mode == "QUICK_REFERENCE"
            else "CONTROLLED_PERSONAL_REFERENCE_EVIDENCE"
        ),
        "target_candidate_id": target_candidate_id,
        "reference_candidate_ids": references,
        "session_count": len(sessions),
        "timepoints_seconds": list(timepoints),
        "repeats_per_target_reference_pair": repeats_per_pair,
        "schedule": schedules,
        "reference_reference_comparisons_required": False,
        "pair_coverage_complete": not incomplete,
        "incomplete_pair_ids": ["|".join(pair) for pair in incomplete],
        "presentation_order_counts": order_balance,
        "presentation_order_balanced": order_balanced,
        "evaluation_endpoints": endpoints,
        "substrate_pooling_allowed": False,
        "retained_pre_delta_sample_required": False,
        "population_generalization_authorized": False,
        "physical_execution_authorized": False,
        "formula_action": "NO_CHANGE",
        **FALSE_ACTION_AUTHORITY,
    }
    plan["protocol_sha256"] = stable_payload_hash(plan)
    return plan, BlindingManifestV1(
        protocol_id=protocol_id,
        session_codes=session_codes,
    )


__all__ = [
    "BlindingManifestV1",
    "DEFAULT_PERSONAL_TIMEPOINTS_SECONDS",
    "InstrumentalObservationContractV1",
    "build_personal_sensory_protocol",
    "build_reference_anchored_protocol",
]
