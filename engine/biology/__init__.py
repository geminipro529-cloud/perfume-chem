"""Biology layer: microbiome, OR genetics, retronasal pathway."""
from .genetics import (
    OR_POLYMORPHISMS,
    apply_polymorphism,
    population_average_response,
)
from .microbiome import AxillaProfile, skin_microbiome_modifier

__all__ = [
    "skin_microbiome_modifier", "AxillaProfile",
    "OR_POLYMORPHISMS", "apply_polymorphism", "population_average_response",
]
