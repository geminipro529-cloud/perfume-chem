"""Lightweight calibration records for future empirical fitting."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

THAI_CLIMATE_CONTEXT = {
    "name": "thai_hot_humid",
    "temperature_K": 305.0,
    "relative_humidity": 0.75,
    "notes": "Default skin-wear context for Bangkok-style hot humid conditions.",
}


@dataclass(frozen=True, slots=True)
class WearTestObservation:
    time_minutes: float
    substrate: str = "skin"
    time_window: str = ""
    projection_cm: float | None = None
    perceived_intensity_0_10: float | None = None
    dominant_notes: tuple[str, ...] = ()
    rejection_flags: tuple[str, ...] = ()
    comments: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WearTestObservation":
        return cls(
            time_minutes=float(data["time_minutes"]),
            substrate=str(data.get("substrate") or "skin"),
            time_window=str(data.get("time_window") or ""),
            projection_cm=_optional_float(data.get("projection_cm")),
            perceived_intensity_0_10=_optional_float(data.get("perceived_intensity_0_10")),
            dominant_notes=_tuple_str(data.get("dominant_notes")),
            rejection_flags=_tuple_str(data.get("rejection_flags")),
            comments=str(data.get("comments") or ""),
        )


@dataclass(frozen=True, slots=True)
class PanelResult:
    panelist_id: str
    liking_0_10: float | None = None
    familiarity_0_10: float | None = None
    luxury_0_10: float | None = None
    purchase_intent_0_10: float | None = None
    freshness_0_10: float | None = None
    wearability_0_10: float | None = None
    descriptors: tuple[str, ...] = ()
    rejection_flags: tuple[str, ...] = ()
    comments: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PanelResult":
        return cls(
            panelist_id=str(data["panelist_id"]),
            liking_0_10=_optional_float(data.get("liking_0_10")),
            familiarity_0_10=_optional_float(data.get("familiarity_0_10")),
            luxury_0_10=_optional_float(data.get("luxury_0_10")),
            purchase_intent_0_10=_optional_float(data.get("purchase_intent_0_10")),
            freshness_0_10=_optional_float(data.get("freshness_0_10")),
            wearability_0_10=_optional_float(data.get("wearability_0_10")),
            descriptors=_tuple_str(data.get("descriptors")),
            rejection_flags=_tuple_str(data.get("rejection_flags")),
            comments=str(data.get("comments") or ""),
        )


@dataclass(frozen=True, slots=True)
class CalibrationRecord:
    formula_name: str
    formula_hash: str
    context: dict[str, Any] = field(default_factory=lambda: dict(THAI_CLIMATE_CONTEXT))
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"))
    predicted: dict[str, Any] = field(default_factory=dict)
    observations: tuple[WearTestObservation, ...] = ()
    panel_results: tuple[PanelResult, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "formula_name": self.formula_name,
            "formula_hash": self.formula_hash,
            "context": dict(self.context),
            "created_at": self.created_at,
            "predicted": dict(self.predicted),
            "observations": [obs.to_dict() for obs in self.observations],
            "panel_results": [result.to_dict() for result in self.panel_results],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CalibrationRecord":
        return cls(
            formula_name=str(data["formula_name"]),
            formula_hash=str(data["formula_hash"]),
            context=dict(data.get("context") or THAI_CLIMATE_CONTEXT),
            created_at=str(data.get("created_at") or datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")),
            predicted=dict(data.get("predicted") or {}),
            observations=tuple(
                WearTestObservation.from_dict(obs)
                for obs in data.get("observations", [])
            ),
            panel_results=tuple(
                PanelResult.from_dict(result)
                for result in data.get("panel_results", [])
            ),
        )


def _tuple_str(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    return tuple(str(item) for item in value if str(item))


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
