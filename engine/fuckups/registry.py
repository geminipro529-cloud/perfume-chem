"""Fuckup Registry — persistent store of formulation failures.

Stores FuckupEntry records as JSON for cross-session learning. Each new fuckup
is appended to the registry. The detector reads from this registry to build its
pattern rules.

Storage: engine/fuckups/registry.json (JSON array)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    CulpritMaterial,
    FuckupEntry,
    MissingDNA,
    RootCauseCategory,
)

_REGISTRY_PATH = Path(__file__).resolve().parent / "registry.json"


class FuckupRegistry:
    """Manages the persistent fuckup database."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _REGISTRY_PATH
        self._entries: list[FuckupEntry] = []
        self._load()

    def _load(self) -> None:
        """Load entries from JSON file."""
        if not self._path.exists():
            self._entries = []
            return

        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._entries = []
            return

        self._entries = []
        for item in raw:
            try:
                entry = self._dict_to_entry(item)
                self._entries.append(entry)
            except (KeyError, TypeError, ValueError):
                continue

    def _save(self) -> None:
        """Persist entries to JSON."""
        data = [entry.as_dict() for entry in self._entries]
        self._path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add(self, entry: FuckupEntry) -> None:
        """Add a new fuckup entry. Auto-saves."""
        existing_ids = {e.id for e in self._entries}
        if entry.id in existing_ids:
            return  # Don't duplicate
        self._entries.append(entry)
        self._save()

    def get(self, entry_id: str) -> FuckupEntry | None:
        """Retrieve a specific entry by ID."""
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        return None

    def list_all(self) -> list[FuckupEntry]:
        """Return all entries, most recent first."""
        return sorted(self._entries, key=lambda e: e.date, reverse=True)

    def by_category(self, category: RootCauseCategory) -> list[FuckupEntry]:
        """Filter entries by root cause category."""
        return [e for e in self._entries if category in e.root_causes]

    def count(self) -> int:
        """How many fuckups have been recorded."""
        return len(self._entries)

    def summary(self) -> dict[str, Any]:
        """Statistical summary of all recorded failures."""
        if not self._entries:
            return {"total": 0, "categories": {}, "severity_counts": {}}

        cats: dict[str, int] = {}
        sevs: dict[str, int] = {}
        for entry in self._entries:
            for cat in entry.root_causes:
                cats[cat.value] = cats.get(cat.value, 0) + 1
            sevs[entry.severity] = sevs.get(entry.severity, 0) + 1

        return {
            "total": len(self._entries),
            "categories": cats,
            "severity_counts": sevs,
        }

    # -- Serialization helpers --

    @staticmethod
    def _dict_to_entry(data: dict[str, Any]) -> FuckupEntry:
        """Deserialize a dict to FuckupEntry."""
        culprits = tuple(CulpritMaterial(**c) for c in data.get("culprits", []))
        missing = tuple(MissingDNA(**m) for m in data.get("missing_dna", []))
        root_causes = tuple(RootCauseCategory(rc) for rc in data.get("root_causes", []))
        return FuckupEntry(
            id=data["id"],
            formula_file=data["formula_file"],
            intended_character=data["intended_character"],
            actual_character=data["actual_character"],
            root_causes=root_causes,
            culprits=culprits,
            missing_dna=missing,
            pipeline_snapshot=data.get("pipeline_snapshot", {}),
            lesson=data["lesson"],
            detection_rules=tuple(data.get("detection_rules", [])),
            date=data["date"],
            severity=data.get("severity", "high"),
        )


# -- Singleton for convenience --

_registry: FuckupRegistry | None = None


def get_registry() -> FuckupRegistry:
    """Get or create the global fuckup registry singleton."""
    global _registry
    if _registry is None:
        _registry = FuckupRegistry()
    return _registry


# ═══════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP: Seed the registry with the first fuckup
# ═══════════════════════════════════════════════════════════════════════════════

CASSIS_IRIS_SMOKE = FuckupEntry(
    id="cassis_iris_smoke_2026-07-05",
    formula_file="formulas/Cassis_Iris_Smoke_30mL_EdP.md",
    intended_character=(
        "Aventus-adjacent modern fruity chypre: cassis-forward fruit (instead of pineapple), "
        "iris signature heart (instead of Lyral-muguet), cade-guaiac-nagarmotha smoke triad "
        "(instead of birch tar), three-cedar wood, oakmoss-labdanum base, musk-amber scaffold."
    ),
    actual_character=(
        "Green 1880 chypre. Smells nothing like Aventus. Juniper Berry EO dominates the top "
        "(OAV 1,936) creating a gin-coniferous opening. Petitgrain adds bitter-green-neroli. "
        "Orivone (OAV 833, VP=8.6 Pa) floods the heart with buttery-orris 'old perfume' character. "
        "The oakmoss-labdanum-vetiver-cedar skeleton creates a classical chypre base (Coty, 1917). "
        "Nagarmotha adds earthy-musty rather than smoky character. The massive iris bloc "
        "(Alpha Irone 200 µL 30% + Orivone + Ultralia + Beta Ionone) creates soliflore-level "
        "iris that fundamentally re-routes the fragrance away from any Aventus resemblance. "
        "Pyramid collapse: T:1.9% H:87.1% B:11.0% — no temporal evolution, flat heart dominance."
    ),
    root_causes=(
        RootCauseCategory.MATERIAL_MISMATCH,
        RootCauseCategory.DOSE_OVERLOAD,
        RootCauseCategory.GENRE_COLLISION,
        RootCauseCategory.MISSING_DNA,
        RootCauseCategory.CHYPRE_DRIFT,
        RootCauseCategory.GREEN_DRIFT,
        RootCauseCategory.PYRAMID_COLLAPSE,
    ),
    culprits=(
        CulpritMaterial(
            name="Juniper Berry EO",
            dose_ul=50,
            dilution_pct=100,
            oav=1936,
            vp_pa=65.0,
            role="Smoke accord — gin-coniferous spark",
            why_wrong=(
                "At 50 µL neat (OAV 1,936, VP=65 Pa), Juniper Berry EO is the third-strongest "
                "material in the formula. It creates a massive gin-coniferous opening that defines "
                "the aromatic-green chypre character. This is a fougère material, not a chypre "
                "material. Aventus has zero juniper — this single material alone guarantees the "
                "formula won't read as Aventus-adjacent."
            ),
        ),
        CulpritMaterial(
            name="Orivone",
            dose_ul=30,
            dilution_pct=100,
            oav=833,
            vp_pa=8.6,
            role="Heart accord — buttery iris warmth",
            why_wrong=(
                "At 30 µL neat with VP=8.6 Pa, Orivone functions as a top-to-heart orris note "
                "(OAV 833, #7 by OAV). This warm, buttery, slightly fungal orris character is "
                "the defining note of early 20th-century perfumery (1880-1920). It is fundamentally "
                "incompatible with modern fruity chypre. At this dose, iris registers as a "
                "character note, not a structural accent. Aventus has zero detectable iris."
            ),
        ),
        CulpritMaterial(
            name="Petitgrain EO Paraguay",
            dose_ul=80,
            dilution_pct=100,
            oav=858,
            vp_pa=6.0,
            role="Top accord — green-neroli flash",
            why_wrong=(
                "At 80 µL neat (OAV 858), Petitgrain adds a bitter-green-neroli bite that, "
                "combined with Juniper, creates an aromatic-fougère opening reminiscent of "
                "Fougère Royale (1882). The bitter-green character contradicts the bright-fruity "
                "opening expected in Aventus-adjacent compositions. Reduce to ≤20 µL."
            ),
        ),
        CulpritMaterial(
            name="Nagarmotha Oil",
            dose_ul=200,
            dilution_pct=100,
            oav=0.1,
            vp_pa=0.005,
            role="Smoke accord — earthy dry mustakone smoke",
            why_wrong=(
                "At 200 µL neat, Nagarmotha is the largest single smoke material. Its earthy-musty "
                "cypriol character is nothing like birch tar's sharp oily-leather smoke. Even though "
                "pipeline OAV shows 0.1 (sub-threshold), the ODT data is flagged suspect — real "
                "perceptibility is likely higher. The earthy quality pulls toward classical chypre "
                "or oud territory rather than Aventus's smoky-leather signature."
            ),
        ),
        CulpritMaterial(
            name="Alpha Irone",
            dose_ul=200,
            dilution_pct=30,
            oav=22.7,
            vp_pa=0.559,
            role="Heart accord — cold iris butter SIGNATURE",
            why_wrong=(
                "At 200 µL of 30% (= 60 µL active), Alpha Irone creates the core of a soliflore-level "
                "iris heart. Combined with Orivone, Ultralia, and Beta Ionone, the total iris loading "
                "is 280 µL across four materials. This is appropriate for an iris fragrance — not for "
                "anything claiming Aventus DNA. Iris cold-buttery-powdery character is one of the most "
                "distinctive and genre-defining registers in perfumery. It cannot coexist with fruity chypre."
            ),
        ),
    ),
    missing_dna=(
        MissingDNA(
            name="Allyl Amyl Glycolate / Dynascone / Pineapple accord",
            role_in_target="Pineapple top note — THE defining Aventus opening character",
            alternative_used="Cassis Base 345B (sulfury blackcurrant — different fruit entirely)",
        ),
        MissingDNA(
            name="Birch Tar Rectified",
            role_in_target="Sharp oily-leather smoke — THE Aventus smoky signature",
            alternative_used="Cade Oil + Nagarmotha + Guaiacol (dry-earthy-clean instead of oily-leather)",
        ),
        MissingDNA(
            name="Patchouli EO / Clearwood",
            role_in_target="Earthy-camphoraceous bridge between fruit and base",
            alternative_used="Not present at all — the fruit-to-base bridge is missing",
        ),
        MissingDNA(
            name="Ambrox (proper dose)",
            role_in_target="Modern mineral amber anchor in the drydown",
            alternative_used="Ambrofix 30% at 390 µL (adequate dose but overwhelmed by chypre skeleton)",
        ),
    ),
    pipeline_snapshot={
        "pyramid": {"top_pct": 1.9, "heart_pct": 87.1, "base_pct": 11.0},
        "top_5_oav": {
            "Hedione": 2527,
            "Cassis Base 345B": 2111,
            "Juniper Berry EO": 1936,
            "Bergamot FCF": 1809,
            "Iso E Super": 1361,
        },
        "sub_threshold_count": 21,
        "total_materials": 46,
        "gate_failures": [
            "exact_subtotal",
            "material_spine_coverage",
            "physics_data_coverage",
            "odt_coverage",
            "opaque_preblends",
            "perfume_knowledge (pyramid off-target)",
            "literature_compliance (1/5)",
            "roudnitska_transparence (16%)",
            "master_perfumer_gate",
            "confidence_minimum (21.8)",
        ],
        "odor_families": {
            "fruity": "21.9%",
            "citrus": "21.3%",
            "floral": "20.7%",
            "aromatic": "15.4%",  # Juniper! This shouldn't be here for Aventus
            "woody": "12.1%",
            "iris": "7.0%",  # Iris! This shouldn't be here at all
            "musk": "0.0%",  # Musks imperceptible — wrong
            "smoky": "0.1%",  # Smoke imperceptible — wrong
        },
    },
    lesson=(
        "If a formula claims Aventus DNA, four conditions are non-negotiable: "
        "(1) pineapple accord in the top (Allyl Amyl Glycolate, Dynascone, or a built accord), "
        "(2) birch tar smoke in the heart (not cade, not nagarmotha, not guaiacol — birch tar), "
        "(3) patchouli or Clearwood bridging fruit to base, "
        "(4) a modern ambrox-musk base (not oakmoss-labdanum-vetiver-cedar). "
        "Deviate from any of these four and the formula becomes a different fragrance entirely. "
        "Additionally: juniper, petitgrain >40 µL, and orivone are genre-shifting materials that "
        "pull toward aromatic chypre/fougère territory. Iris at any perceptible dose fundamentally "
        "re-routes away from fruity chypre — the registers collide and iris wins because ionones "
        "are more tenacious than fruit esters. The pyramid must have actual temporal evolution "
        "(T:20% H:50% B:30%) — a flat heart (87%) means no top note separation."
    ),
    detection_rules=(
        "juniper_berry_eo > 30uL in non-fougere context → aromatic green drift",
        "orivone > 20uL in non-iris formula → buttery orris 'old perfume' character",
        "petitgrain > 60uL with juniper → aromatic-chypre opening",
        "nagarmotha > 100uL as smoke substitute → earthy-musty, not smoky",
        "alpha_irone active > 30uL in non-iris brief → soliflore-level iris collision",
        "oakmoss + labdanum + vetiver + cedar ≥ 3 present → classical chypre skeleton",
        "iris materials ≥ 3 in non-iris formula → genre collision (iris always wins)",
        "missing birch_tar when claiming aventus → wrong smoke character",
        "missing pineapple_accord when claiming aventus → wrong fruit character",
        "missing patchouli when claiming aventus → missing fruit-to-base bridge",
        "geosmin > 5uL of 0.1% → petrichor adds 'damp cellar' quality",
        "cassis_base > 30uL in non-cassis-forward → sulfury blackcurrant dominates drydown",
    ),
    date="2026-07-05",
    severity="catastrophic",
)


def _bootstrap() -> None:
    """Seed the registry with the Cassis Iris Smoke fuckup if empty."""
    reg = get_registry()
    if reg.count() == 0:
        reg.add(CASSIS_IRIS_SMOKE)


# Auto-bootstrap on import
_bootstrap()
