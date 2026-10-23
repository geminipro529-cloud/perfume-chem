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

from engine.inventory_parser import parse_current_inventory, parse_inventory
from engine.material_resolver import strip_stock_strength_suffix
from engine.pipeline import simulator

_NO_AIR_ODT = (
    "no published human detection threshold in air found; searched Nagata 2003, "
    "Abraham et al. 2012, Elsharif et al. 2015 and supplier pages (2026-10-14)"
)
_NO_AIR_ODT_1023 = (
    "no published human detection threshold in air found; searched RIFM and TGSC "
    "(2026-10-23); the Nagata 2003 table could not be read"
)
_ALL = ("logp", "mw", "odt", "vp")
_MSR_COSMETIC_EXTRACT = (
    "MySkinRecipes cosmetic extract in a propylene glycol carrier; no odorant data published"
)

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
    # Filled 2026-10-23 with RDKit MW and a labelled Crippen log P; still no air threshold.
    # Merged 2026-10-23 into the older entry, whose VP is a labelled TGSC estimate.
    "Aldehyde C16 EMPG": (("odt",), _NO_AIR_ODT_1023),
    "Canthoxal": (("odt",), _NO_AIR_ODT_1023),
    "Cedroxyde": (("odt",), _NO_AIR_ODT_1023),
    "Citronellyl Acetate": (("odt",), _NO_AIR_ODT_1023),
    "Cyclogalbanate": (("odt",), _NO_AIR_ODT_1023),
    "Dimethyl Benzyl Carbinol": (("odt",), _NO_AIR_ODT_1023),
    "Dupical": (("odt",), _NO_AIR_ODT_1023),
    "Neryl Acetate": (
        ("odt", "vp"),
        _NO_AIR_ODT_1023 + "; chemprops returned geranyl acetate's VP record, so no VP is used",
    ),
    "Para-Acetanisole": (("odt",), _NO_AIR_ODT_1023),
    "Para-Cresyl Phenyl Acetate": (("odt",), _NO_AIR_ODT_1023),
    "Peach Ketone": (("odt",), _NO_AIR_ODT_1023),
    "Phenoxy Ethyl Isobutyrate": (("odt",), _NO_AIR_ODT_1023),
    "Velvione": (("odt",), _NO_AIR_ODT_1023),
    # Structure not confirmed, so no calculated log P.
    "Decatone": (("logp", "odt"), "structure unconfirmed, so no Crippen log P; " + _NO_AIR_ODT_1023),
    "Pear Valerate": (("logp", "odt"), "structure unconfirmed, so no Crippen log P; " + _NO_AIR_ODT_1023),
    # Proprietary bases: a mixture with no CAS has no single MW, VP or log P.
    "Black Tea Base": (_ALL, "PerfumersWorld blend, not a pure chemical; no composition published"),
    "Costus Olifac": (("logp", "mw", "vp"), "IFF proprietary base with no CAS; the old MW and VP were placeholders"),
    "Tuberose Base": (_ALL, "maker and composition of this base are not recorded"),
    "Hindinol": (_ALL, "identity and CAS unknown; no PubChem match for the name (2026-10-23)"),
    "Rhodinol": (
        ("logp", "mw", "vp"),
        "MySkinRecipes 2760 citronellol + geraniol blend; COA CAS 6812-78-8 and page CAS "
        "141-25-3 disagree (MSR reply 2026-10-21 did not resolve it)",
    ),
    "Rum Ether": (_ALL, "CAS 8030-89-5 is a reaction-product mixture with no single MW or VP"),
    # Naturals with no peer-reviewed GC-MS of the same product type (Rule 4).
    "Frangipani Absolute": (
        _ALL,
        "only a Plumeria alba concrete re-extracted in ethanol was found, a different product",
    ),
    "Lemon Terpeneless Oil Sicilian": (_ALL, "no GC table for a terpeneless or folded lemon oil found"),
    "Mate Absolute": (_ALL, "the one absolute-type table (US 9434908, Table 5) could not be read"),
    "Fir Essential Oil": (_ALL, "PerfumersWorld 7KG07758 does not state the Abies species; no GC-MS"),
    "Ginger Lily Oil": (_ALL, "PerfumersWorld record is empty (SG 0.0000, CAS TBA)"),
    "Red Saffron Infusion": (
        _ALL,
        "PerfumersWorld: saffron stigmas extracted in DPG; strength unpublished",
    ),
    "Cabbage Rose Extract": (_ALL, _MSR_COSMETIC_EXTRACT),
    "Magnolia Flower Extract": (_ALL, _MSR_COSMETIC_EXTRACT),
    "Iris Florentina Root Extract": (_ALL, _MSR_COSMETIC_EXTRACT),
}


def _owned_names() -> list[str]:
    """inventory.txt plus the gate stock list (V5 snapshot, overlays, saved bottles)."""
    names: dict[str, None] = {}
    for records in (
        parse_inventory(include_solvents=False, include_unavailable=False, unique=False),
        parse_current_inventory(unique=False, include_solvents=False, include_unavailable=False),
    ):
        for record in records:
            for name in (record.name, record.identity_name):
                if name:
                    names.setdefault(name, None)
    return list(names)


def _held_name(label: str) -> str:
    """A stock label ("Dupical 10% in DPG", "Buccoxime (neat)") shares its material's hold."""
    bare = strip_stock_strength_suffix(label)
    return bare.removesuffix(" (neat)").strip()


def _gaps() -> dict[str, set[tuple[str, ...]]]:
    names = _owned_names()
    frame = simulator.simulate_formula({n: 10.0 for n in names}, {n: 1.0 for n in names})[0]
    gaps: dict[str, set[tuple[str, ...]]] = {}
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
            # Every stock label of a held material is compared, not just the first.
            gaps.setdefault(_held_name(material.name), set()).add(missing)
    return gaps


def test_every_owned_stock_has_physics_or_a_written_hold():
    gaps = _gaps()
    unexplained = {name: sorted(missing) for name, missing in gaps.items() if name not in HOLDS}
    assert not unexplained, f"owned stocks without physics or a hold: {unexplained}"
    wrong = {
        name: (sorted(variants), HOLDS[name][0])
        for name, variants in gaps.items()
        if name in HOLDS and variants != {HOLDS[name][0]}
    }
    assert not wrong, f"holds whose missing fields changed (found, held): {wrong}"
    filled = sorted(set(HOLDS) - set(gaps))
    assert not filled, f"holds whose data is now present; remove them from HOLDS: {filled}"
