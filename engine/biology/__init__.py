"""Biology layer: microbiome, OR genetics, retronasal pathway."""
from .microbiome import skin_microbiome_modifier, AxillaProfile
from .genetics import (
    OR_POLYMORPHISMS,
    apply_polymorphism,
    population_average_response,
)

__all__ = [
    "skin_microbiome_modifier", "AxillaProfile",
    "OR_POLYMORPHISMS", "apply_polymorphism", "population_average_response",
]
