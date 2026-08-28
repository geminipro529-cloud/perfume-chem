"""Validated, non-ranked rule and strategy registries for architecture design."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.perception.architecture_contracts import ArchitectureStrategyId

_RULE_REGISTRY_PATH = Path("configs/solforge/perfumery_rule_registry_v1.json")
_STRATEGY_REGISTRY_PATH = Path(
    "configs/solforge/architecture_strategy_registry_v1.json"
)


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _text_tuple(
    value: object,
    field_name: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a JSON array")
    result = tuple(_text(item, field_name) for item in value)
    if not allow_empty and not result:
        raise ValueError(f"{field_name} must be nonempty")
    if len(result) != len(set(result)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a JSON object")
    return value


def _load_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return _mapping(value, str(path))


@dataclass(frozen=True, slots=True)
class PerfumeryRuleRegistry:
    schema_version: str
    claim_ceiling: str
    ingredient_count_is_complexity: bool
    composition_score_has_hedonic_authority: bool
    predicted_oav_has_perceptual_authority: bool
    target_first_sequence: tuple[str, ...]
    separated_constructs: tuple[str, ...]
    prohibited_inferences: tuple[str, ...]
    compilation_gates: tuple[str, ...]
    inventory_gates: tuple[str, ...]
    hedonic_gates: tuple[str, ...]
    authority_flags: Mapping[str, bool]
    source_sha256: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> PerfumeryRuleRegistry:
        complexity = _mapping(value.get("complexity_firewall"), "complexity_firewall")
        inference = _mapping(value.get("inference_firewall"), "inference_firewall")
        gates = _mapping(value.get("gates"), "gates")
        authority = _mapping(value.get("authority_flags"), "authority_flags")
        if not all(isinstance(item, bool) for item in authority.values()):
            raise TypeError("authority_flags values must be boolean")
        if any(authority.values()):
            raise ValueError("architecture rule registry cannot grant authority")
        ingredient_count = complexity.get("ingredient_count_is_complexity")
        composition_hedonic = inference.get(
            "composition_score_has_hedonic_authority"
        )
        oav_perception = inference.get("predicted_oav_has_perceptual_authority")
        for field_name, field_value in (
            ("ingredient_count_is_complexity", ingredient_count),
            ("composition_score_has_hedonic_authority", composition_hedonic),
            ("predicted_oav_has_perceptual_authority", oav_perception),
        ):
            if field_value is not False:
                raise ValueError(f"{field_name} must be false")
        return cls(
            schema_version=_text(value.get("schema_version"), "schema_version"),
            claim_ceiling=_text(value.get("claim_ceiling"), "claim_ceiling"),
            ingredient_count_is_complexity=False,
            composition_score_has_hedonic_authority=False,
            predicted_oav_has_perceptual_authority=False,
            target_first_sequence=_text_tuple(
                value.get("target_first_sequence"),
                "target_first_sequence",
            ),
            separated_constructs=_text_tuple(
                value.get("separated_constructs"),
                "separated_constructs",
            ),
            prohibited_inferences=_text_tuple(
                inference.get("prohibited_inferences"),
                "prohibited_inferences",
            ),
            compilation_gates=_text_tuple(
                gates.get("architecture_compilation"),
                "gates.architecture_compilation",
            ),
            inventory_gates=_text_tuple(
                gates.get("inventory_and_execution"),
                "gates.inventory_and_execution",
            ),
            hedonic_gates=_text_tuple(
                gates.get("hedonic_evidence"),
                "gates.hedonic_evidence",
            ),
            authority_flags=MappingProxyType(dict(authority)),
            source_sha256=sha256_hex(canonical_json_bytes(value)),
        )


@dataclass(frozen=True, slots=True)
class ArchitectureStrategyDefinition:
    strategy_id: ArchitectureStrategyId
    name: str
    definition: str
    not_definition: str
    when_to_use: tuple[str, ...]
    when_not_to_use: tuple[str, ...]
    perceptual_depth_mechanisms: tuple[str, ...]
    target_signatures: tuple[str, ...]
    required_relations: tuple[str, ...]
    failure_modes: tuple[str, ...]
    causal_probe_types: tuple[str, ...]
    primary_endpoints: tuple[str, ...]
    failure_endpoints: tuple[str, ...]
    compatible_secondaries: tuple[ArchitectureStrategyId, ...]
    dhp_relation: str
    strategy_score: None

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> ArchitectureStrategyDefinition:
        strategy_score = value.get("strategy_score")
        if strategy_score is not None:
            raise ValueError("strategy_score must be null; strategies are not ranked")
        strategy_id = ArchitectureStrategyId(
            _text(value.get("strategy_id"), "strategy_id")
        )
        secondaries = tuple(
            ArchitectureStrategyId(item)
            for item in _text_tuple(
                value.get("compatible_secondaries"),
                "compatible_secondaries",
                allow_empty=True,
            )
        )
        if strategy_id in secondaries:
            raise ValueError("a strategy cannot list itself as a secondary")
        return cls(
            strategy_id=strategy_id,
            name=_text(value.get("name"), "name"),
            definition=_text(value.get("definition"), "definition"),
            not_definition=_text(value.get("not_definition"), "not_definition"),
            when_to_use=_text_tuple(value.get("when_to_use"), "when_to_use"),
            when_not_to_use=_text_tuple(
                value.get("when_not_to_use"),
                "when_not_to_use",
            ),
            perceptual_depth_mechanisms=_text_tuple(
                value.get("perceptual_depth_mechanisms"),
                "perceptual_depth_mechanisms",
            ),
            target_signatures=_text_tuple(
                value.get("target_signatures"),
                "target_signatures",
            ),
            required_relations=_text_tuple(
                value.get("required_relations"),
                "required_relations",
            ),
            failure_modes=_text_tuple(value.get("failure_modes"), "failure_modes"),
            causal_probe_types=_text_tuple(
                value.get("causal_probe_types"),
                "causal_probe_types",
            ),
            primary_endpoints=_text_tuple(
                value.get("primary_endpoints"),
                "primary_endpoints",
            ),
            failure_endpoints=_text_tuple(
                value.get("failure_endpoints"),
                "failure_endpoints",
            ),
            compatible_secondaries=secondaries,
            dhp_relation=_text(value.get("dhp_relation"), "dhp_relation"),
            strategy_score=None,
        )


class ArchitectureStrategyRegistry:
    def __init__(self, value: Mapping[str, Any]) -> None:
        self.schema_version = _text(value.get("schema_version"), "schema_version")
        self.selection_rule = _text(value.get("selection_rule"), "selection_rule")
        self.nonranking_rule = _text(value.get("nonranking_rule"), "nonranking_rule")
        self.primary_strategy_count = value.get("primary_strategy_count")
        self.maximum_secondary_strategies = value.get(
            "maximum_secondary_strategies"
        )
        if self.primary_strategy_count != 1:
            raise ValueError("primary_strategy_count must be exactly one")
        if self.maximum_secondary_strategies != 2:
            raise ValueError("maximum_secondary_strategies must be two")
        raw_strategies = value.get("strategies")
        if not isinstance(raw_strategies, list):
            raise TypeError("strategies must be a JSON array")
        definitions = tuple(
            ArchitectureStrategyDefinition.from_mapping(
                _mapping(item, "strategies[]")
            )
            for item in raw_strategies
        )
        identifiers = tuple(item.strategy_id for item in definitions)
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("strategy IDs must be unique")
        expected = set(ArchitectureStrategyId)
        observed = set(identifiers)
        if observed != expected:
            missing = sorted(item.value for item in expected - observed)
            extra = sorted(item.value for item in observed - expected)
            raise ValueError(
                f"strategy registry must contain the exact eight IDs; "
                f"missing={missing}, extra={extra}"
            )
        self._definitions = MappingProxyType(
            {item.strategy_id: item for item in definitions}
        )
        self.strategy_ids = tuple(item.strategy_id.value for item in definitions)
        self.source_sha256 = sha256_hex(canonical_json_bytes(value))

    def get(
        self,
        strategy_id: ArchitectureStrategyId | str,
    ) -> ArchitectureStrategyDefinition:
        return self._definitions[ArchitectureStrategyId(strategy_id)]


def load_default_architecture_registries(
    repository_root: str | Path,
) -> tuple[PerfumeryRuleRegistry, ArchitectureStrategyRegistry]:
    root = Path(repository_root)
    rules_value = _load_json(root / _RULE_REGISTRY_PATH)
    strategies_value = _load_json(root / _STRATEGY_REGISTRY_PATH)
    return (
        PerfumeryRuleRegistry.from_mapping(rules_value),
        ArchitectureStrategyRegistry(strategies_value),
    )


__all__ = [
    "ArchitectureStrategyDefinition",
    "ArchitectureStrategyRegistry",
    "PerfumeryRuleRegistry",
    "load_default_architecture_registries",
]
