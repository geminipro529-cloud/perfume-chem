"""Canonical material data spine.

Single source of truth for per-material physical, chemical, perceptual,
and supplier data. Backs every downstream physics/perception module.

Layout
------
data/materials/<LETTER>.yaml   — canonical entries, sorted by name
data/materials/_index.json     — name/alias → (letter_file, position) lookup
data/materials/_sources/       — raw parsed source snapshots

Schema
------
See :class:`engine.data_spine.material.Material` for the full field list.

CLI
---
    python -m engine.data_spine.migrate         # rebuild A-Z files
    python -m engine.data_spine.audit           # report field-completeness gaps
"""

from .material import Material, MaterialRegistry
from .loader import load_registry

__all__ = ["Material", "MaterialRegistry", "load_registry"]
