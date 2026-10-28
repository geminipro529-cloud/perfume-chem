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
_NO_AIR_ODT_1025 = (
    "no published human detection threshold in air found; searched Nagata 2003, van Gemert "
    "2011 and Givaudan's PROC patent tables (2026-10-25)"
)
_ALL = ("logp", "mw", "odt", "vp")
_MSR_COSMETIC_EXTRACT = (
    "MySkinRecipes cosmetic extract in a propylene glycol carrier; no odorant data published"
)

HOLDS: dict[str, tuple[tuple[str, ...], str]] = {
    # Synthetics with MW, VP and log P but no air threshold (Rule 1: a water,
    # ethanol or usage-level number is not an air threshold).
    "Buccoxime": (("odt",), _NO_AIR_ODT),
    "Cis-3 Hexenyl Hexanoate": (("odt",), _NO_AIR_ODT),
    "Diethyl Malonate": (("odt",), _NO_AIR_ODT),
    "Fructone B": (("odt",), _NO_AIR_ODT),
    "Gamma Octalactone": (("odt",), _NO_AIR_ODT + "; a 6.5 ug/L water threshold exists and is not usable"),
    "Glycolierral": (("odt",), _NO_AIR_ODT),
    "Liffarome": (("odt",), _NO_AIR_ODT),
    "Linalool Oxide": (("odt",), _NO_AIR_ODT + " for any isomer"),
    "Rhubofix": (("odt",), _NO_AIR_ODT),
    "Veloutone": (("odt",), _NO_AIR_ODT),
    # Filled 2026-10-23 with RDKit MW and a labelled Crippen log P; still no air threshold.
    # Merged 2026-10-23 into the older entry, whose VP is a labelled TGSC estimate.
    "Aldehyde C16 EMPG": (("odt",), _NO_AIR_ODT_1023),
    "Para-Cresyl Phenyl Acetate": (("odt",), _NO_AIR_ODT_1023),
    "Peach Ketone": (("odt",), _NO_AIR_ODT_1023),
    # CAS confirmed on PubChem 2026-10-23; labelled Crippen log P added, still no air threshold.
    "Pear Valerate": (("odt",), _NO_AIR_ODT_1023),
    # (Methyl Laitone left this list on 2026-10-28 with the Givaudan SDS threshold; Ginger Lily
    # Oil the same day as H. spicatum rhizome oil, the closest identity.)
    # (Berry Hexanoate, Citronellyl Acetate, Cyclogalbanate, Decatone, Dupical, Magnolan,
    # Methyl Diantilis, Neryl Acetate and Velvione left this list on 2026-10-25, when the
    # literature batch loaded producer or Givaudan PROC air thresholds.)
    # Added 2026-10-25 from Kenny's PerfumersWorld order lines; their data has not been searched yet.
    # (Cis-3 Hexenyl Acetate, Manzanate and Phenoxy Ethyl Isobutyrate left this list the same day,
    # when the fruit batch loaded Givaudan US 12,340,876 air thresholds.)
    # Searched in the 2026-10-25 literature fill. (Anisyl Acetate, Cedroxyde and Cedryl Acetate left
    # this list on 2026-10-28: Givaudan VP and labelled analogue air ODTs.)
    "Ethyl Acetoacetate": (("odt",), _NO_AIR_ODT_1025),
    "Palm Dates Base": (_ALL, "PerfumersWorld compound base, not a pure chemical; no composition published"),
    # Proprietary bases: a mixture with no CAS has no single MW, VP or log P.
    "Black Tea Base": (_ALL, "PerfumersWorld blend, not a pure chemical; no composition published"),
    "Costus Olifac": (("logp", "mw", "vp"), "IFF proprietary base with no CAS; the old MW and VP were placeholders"),
    "Tuberose Base": (_ALL, "maker and composition of this base are not recorded"),
    # Caryophyllene Acetate, Dimethyl Benzyl Carbinol, Para-Acetanisole and Hindinol left
    # this list on 2026-10-28: labelled UNVERIFIED analogue air ODTs (Kenny's card choice).
    # Group 3 the same day: Acetoin, Canthoxal and Phenyl Ethyl Dimethyl Carbinyl Acetate
    # (UNVERIFIED analogue air ODTs) and Ethyl Linalyl Acetate (Givaudan PROC, PEER_EST) left too.
    "Sandalwood Base 3X": (_ALL, "PerfumersWorld 6WX24054, a partly declared base (Javanol and Sandalore 1-10% each); the invented 2026-08-07 values were removed 2026-10-28"),
    "Sandalwood Base X3": (_ALL, "PerfumersWorld 6WX24054, a partly declared base (Javanol and Sandalore 1-10% each); the invented 2026-08-07 values were removed 2026-10-28"),
    "Rum Ether": (
        _ALL,
        "CAS 8030-89-5 is a reaction-product mixture with no single MW or VP; the MSR COA's "
        "'main content 80% min' is unnamed and the MSR SDS has not been read (2026-10-25)",
    ),
    # Naturals with no peer-reviewed GC-MS of the same product type (Rule 4).
    # Lemon Terpeneless Oil Sicilian left this list on 2026-10-25 (citral 45%, BP grade estimate).
    "Mate Absolute": (
        _ALL,
        "PW declares only methyl heptadienone 0.23%; US 9434908 Table 5 (read 2026-10-25) is a "
        "dimethyl-carbonate leaf extract, 58.9% caffeine by GC area, not an absolute",
    ),
    "Red Saffron Infusion": (
        _ALL,
        "PerfumersWorld: saffron stigmas extracted in DPG; strength unpublished",
    ),
    "Cabbage Rose Extract": (_ALL, _MSR_COSMETIC_EXTRACT),
    "Magnolia Flower Extract": (_ALL, _MSR_COSMETIC_EXTRACT),
    "Iris Florentina Root Extract": (_ALL, _MSR_COSMETIC_EXTRACT),
    # MySkinRecipes orders 2200410 and 2200413, searched 2026-10-27.
    # (Cinnamyl Acetate left this list on 2026-10-28: labelled UNVERIFIED analogue air ODT.)
    # (Magnolia Absolute and White Sandalwood Oil (China) left this list on 2026-10-28, when Kenny
    # asked for the closest identity: they took the Michelia x alba concrete-oil and Santalum album
    # ISO 3518 profiles as labelled proxies.)
    # PerfumersWorld orders of 25 Oct 2026, arrived and searched 2026-10-28.
    "Beta Caryophyllene": (
        ("odt",),
        "no primary human detection threshold in air found; the only figure (0.535 mg/m3, Ruth "
        "1986) is second-hand via UBA 54/2024 'without further details' and is not loaded (2026-10-28)",
    ),
    "Isolongifolanone": (
        ("odt",),
        "no published human detection threshold in air found; Givaudan rates it 'Impactful' from "
        "its own measured threshold but prints no number (2026-10-28)",
    ),
    "Fixative 505": (
        _ALL,
        "PerfumersWorld proprietary base, probably Firmenich Fixateur 505 E; Firmenich's SDS gives "
        "ambroxide and rosin esters only as bands (15-<20%, 20-<30%), so no profile (2026-10-28)",
    ),
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
