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


__all__ = [
    "BlindingManifestV1",
    "DEFAULT_PERSONAL_TIMEPOINTS_SECONDS",
    "InstrumentalObservationContractV1",
    "build_personal_sensory_protocol",
]
