"""Central non-promotion boundary for the standalone closure candidate."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Mapping


AUTHORITY_NAMES: tuple[str, ...] = (
    "source_admission",
    "package_installation",
    "formula_authority",
    "inventory_mutation",
    "stock_authority",
    "bottle_authority",
    "physical_execution",
    "sensory_authority",
    "analytical_authority",
    "strict_empirical_oav",
    "safety_authority",
    "procurement_authority",
    "compounding_authority",
    "publication_authority",
    "repository_promotion",
    "release_authority",
)


@dataclass(frozen=True)
class AuthorityFlags:
    source_admission: bool = False
    package_installation: bool = False
    formula_authority: bool = False
    inventory_mutation: bool = False
    stock_authority: bool = False
    bottle_authority: bool = False
    physical_execution: bool = False
    sensory_authority: bool = False
    analytical_authority: bool = False
    strict_empirical_oav: bool = False
    safety_authority: bool = False
    procurement_authority: bool = False
    compounding_authority: bool = False
    publication_authority: bool = False
    repository_promotion: bool = False
    release_authority: bool = False

    def assert_all_false(self) -> None:
        enabled = [name for name, state in asdict(self).items() if state]
        if enabled:
            raise ValueError(f"authority promotion prohibited: {enabled}")

    def as_mapping(self) -> Mapping[str, bool]:
        self.assert_all_false()
        return asdict(self)


FALSE_AUTHORITY_FLAGS = AuthorityFlags()
