"""Every owned stock has the physics the gate needs, or a written reason why not.

The gate needs molecular weight, vapour pressure, log P and a human air
detection threshold for a single molecule. A natural with a modelled
composition counts once its composite OAV can be computed. Anything else must
sit in HOLDS with the fields it lacks and why: the 2026-10-14 search found no
usable value (material-data-gaps-2026-10-14 in the project files).

A new stock without physics fails this test until its data or a hold is added.
A hold whose data has since been filled fails it too, so the list stays true.
"""

from __future__ import annotations

from engine.inventory_parser import parse_inventory
from engine.pipeline import simulator

_NO_AIR_ODT = (
    "no published human detection threshold in air found; searched Nagata 2003, "
    "Abraham et al. 2012, Elsharif et al. 2015 and supplier pages (2026-10-14)"
)
_ALL = ("logp", "mw", "odt", "vp")

HOLDS: dict[str, tuple[tuple[str, ...], str]] = {
    # Synthetics with MW, VP and log P but no air threshold (Rule 1: a water,
    # ethanol or usage-level number is not an air threshold).
    "Acetoin": (("odt",), _NO_AIR_ODT),
    "Berry Hexanoate (BerryFlor)": (("odt",), _NO_AIR_ODT),
    "Buccoxime": (("odt",), _NO_AIR_ODT),
    "Caryophyllene Acetate": (("odt",), _NO_AIR_ODT),
    "Cedryl Acetate": (("odt",), _NO_AIR_ODT + "; IFF gives a qualitative impact only"),
    "Cis-3 Hexenyl Acetate": (("odt",), _NO_AIR_ODT),
    "Cis-3 Hexenyl Hexanoate": (("odt",), _NO_AIR_ODT),
    "Diethyl Malonate": (("odt",), _NO_AIR_ODT),
    "Ethyl Linalyl Acetate": (("odt",), _NO_AIR_ODT),
    "Fructone B": (("odt",), _NO_AIR_ODT),
    "Gamma Octalactone": (("odt",), _NO_AIR_ODT + "; a 6.5 ug/L water threshold exists and is not usable"),
    "Glycolierral": (("odt",), _NO_AIR_ODT),
    "Liffarome": (("odt",), _NO_AIR_ODT),
    "Linalool Oxide": (("odt",), _NO_AIR_ODT + " for any isomer"),
    "Magnolan": (("odt",), _NO_AIR_ODT),
    "Manzanate": (("odt",), _NO_AIR_ODT),
    "Methyl Diantilis": (("odt",), _NO_AIR_ODT),
    "Methyl Laitone": (("odt",), _NO_AIR_ODT + "; Givaudan gives a qualitative impact only"),
    "Rhubofix": (("odt",), _NO_AIR_ODT),
    "Veloutone": (("odt",), _NO_AIR_ODT),
    # Proprietary bases: a mixture with no CAS has no single MW, VP or log P.
    "Black Tea Base": (_ALL, "PerfumersWorld blend, not a pure chemical; no composition published"),
    "Costus Olifac": (("logp", "mw", "vp"), "IFF proprietary base with no CAS; the old MW and VP were placeholders"),
    # Naturals with no peer-reviewed GC-MS of the same product type (Rule 4).
    "Frangipani Absolute": (
        _ALL,
        "only a Plumeria alba concrete re-extracted in ethanol was found, a different product",
    ),
    "Lemon Terpeneless Oil Sicilian": (_ALL, "no GC table for a terpeneless or folded lemon oil found"),
    "Mate Absolute": (_ALL, "the one absolute-type table (US 9434908, Table 5) could not be read"),
}


def _owned_names() -> list[str]:
    records = parse_inventory(include_solvents=False, include_unavailable=False, unique=False)
    names: dict[str, None] = {}
    for record in records:
        for name in (record.name, record.identity_name):
            if name:
                names.setdefault(name, None)
    return list(names)


def _gaps() -> dict[str, tuple[str, ...]]:
    names = _owned_names()
    frame = simulator.simulate_formula({n: 10.0 for n in names}, {n: 1.0 for n in names})[0]
    gaps: dict[str, tuple[str, ...]] = {}
    for material in frame.state.materials:
        if material.natural_composite_metadata and material.oav is not None:
            continue
        values = {
            "logp": material.logp,
            "mw": material.mw_g_mol,
            "odt": material.odt_air_ppm,
            "vp": material.vp_pure_pa,
        }
        missing = tuple(sorted(field for field, value in values.items() if value is None))
        if missing:
            gaps[material.name] = missing
    return gaps


def test_every_owned_stock_has_physics_or_a_written_hold():
    gaps = _gaps()
    unexplained = {name: missing for name, missing in gaps.items() if name not in HOLDS}
    assert not unexplained, f"owned stocks without physics or a hold: {unexplained}"
    wrong = {
        name: (missing, HOLDS[name][0])
        for name, missing in gaps.items()
        if name in HOLDS and missing != HOLDS[name][0]
    }
    assert not wrong, f"holds whose missing fields changed (found, held): {wrong}"
    filled = sorted(set(HOLDS) - set(gaps))
    assert not filled, f"holds whose data is now present; remove them from HOLDS: {filled}"
