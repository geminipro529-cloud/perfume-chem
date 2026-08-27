# allow: SIZE_OK — science knowledge population + query API

"""
Science knowledge base for 10 perfumery domains.

Provides ``populate_science_kb()`` to create (if not exists) and populate
10 science-domain tables, plus query functions for each domain.

Usage::

    from engine.science_kb import populate_science_kb
    populate_science_kb("data/perfumery_kb.db")

    from engine.science_kb import get_climate_profile
    bangkok = get_climate_profile("Bangkok")
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────

_DB_DEFAULT = "data/perfumery_kb.db"


# ── Helpers ────────────────────────────────────────────────────────────


def _get_conn(db_path: str, *, writable: bool = False) -> sqlite3.Connection:
    abs_path = os.path.abspath(db_path)
    if writable:
        conn = sqlite3.connect(abs_path)
        conn.execute("PRAGMA journal_mode=WAL")
    else:
        conn = sqlite3.connect(
            f"file:{Path(abs_path).as_posix()}?mode=ro&immutable=1",
            uri=True,
        )
        conn.execute("PRAGMA query_only = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]


# ── Populate functions ─────────────────────────────────────────────────


def _populate_or_biophysics(conn: sqlite3.Connection) -> None:
    """Insert olfactory receptor biophysics data."""
    data = [
        (
            "vibration_theory",
            "Odorants may be recognized by electron tunneling vibrations in receptors, not just shape",
            "Turin 1996 Chem Senses",
            "Enantiomers with different vibrational spectra may smell different",
        ),
        (
            "shape_theory",
            "OR binding pocket interactions (H-bonding, sterics, molecular volume) determine odorant recognition",
            "Malnic et al 1999 Cell",
            "Combinatorial OR activation codes create odor identity",
        ),
        (
            "or_antagonism",
            "Competitive antagonism between odorants at OR binding sites is the RULE, not exception",
            "Reddy et al 2018 eLife",
            "Mixture interactions must be modeled, not just individual odorants",
        ),
        (
            "cryo_em",
            "First direct structural evidence of odorant-OR binding (OR51E2 with propionate)",
            "Billesbølle et al 2023 Nature",
            "Enables structure-based odorant prediction",
        ),
        (
            "combinatorial_coding",
            "~400 functional human ORs create combinatorial odorant codes; only ~50 have known ligands",
            "Malnic et al 1999",
            "Odor space is vast and sparsely mapped",
        ),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO or_biophysics (topic, finding, citation, practical_implication) VALUES (?,?,?,?)",
        data,
    )
    conn.commit()


def _populate_material_anosmia(conn: sqlite3.Connection) -> None:
    """Insert specific anosmia rates."""
    data = [
        ("Galaxolide (HHCB)", 32.5, "OR5AN1", "polymorphisms in musk receptor"),
        ("Androstenone", 40.0, "OR7D4", "genetic variation in androstenone receptor"),
        ("Iso E Super", 30.0, "Unknown", "structural class anosmia"),
        ("Ambrox", 12.5, "Unknown", "ambergris anosmia"),
        ("beta-Ionone", 7.5, "OR5AN1", "some populations cannot smell beta-ionone"),
        ("Musk ketone", 7.5, "Unknown", "nitro musk anosmia"),
    ]
    conn.executemany(
        "INSERT INTO material_anosmia (material_name, anosmia_pct, receptor, source) VALUES (?,?,?,?)",
        data,
    )
    conn.commit()


def _populate_evaporation_model(conn: sqlite3.Connection) -> None:
    """Insert evaporation kinetics data."""
    data = [
        (
            "k1_evaporation",
            None,
            "k1 ∝ f(T, airflow, Pvp, MW, Slip)",
            "Saiyasombati & Kasting 2003",
        ),
        (
            "k2_absorption",
            None,
            "k2 ∝ f(T, Pvp, MW, Koct·Sw)",
            "Saiyasombati & Kasting 2003",
        ),
        (
            "fixative_effect",
            None,
            "Fixatives reduce thermodynamic activity of volatiles; single exponential with fixative, biexponential without",
            "Berthier et al 2023",
        ),
        (
            "permeability_linalool",
            "linalool",
            "2.15e-3 cm/h",
            "Almeida et al 2021",
        ),
        (
            "permeability_limonene",
            "limonene",
            "8.25e-6 cm/h",
            "Almeida et al 2021",
        ),
        (
            "permeability_alpha_pinene",
            "alpha-pinene",
            "1.08e-5 cm/h",
            "Almeida et al 2021",
        ),
        ("dhvap_default", None, "60 kJ/mol", "general"),
    ]
    conn.executemany(
        "INSERT INTO evaporation_model (parameter, material_name, value, citation) VALUES (?,?,?,?)",
        data,
    )
    conn.commit()


def _populate_unifac_groups(conn: sqlite3.Connection) -> None:
    """Insert UNIFAC functional groups."""
    data = [
        ("CH3", "C", 1.0, 1.0),
        ("CH2", "C", 1.0, 1.0),
        ("Aromatic CH", "c", 1.5, 1.5),
        ("OH", "O", 3.5, 3.5),
        ("COOH", "C(=O)O", 5.0, 5.0),
        ("Ester", "C(=O)O", 3.0, 3.0),
        ("NH2", "N", 2.5, 2.5),
        ("Ketone", "C=O", 2.5, 2.5),
        ("Aldehyde", "CHO", 2.0, 2.0),
        ("Ether", "O", 1.5, 1.5),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO unifac_groups (group_name, group_smiles, contribution_vp, contribution_logp) VALUES (?,?,?,?)",
        data,
    )
    conn.commit()


def _populate_skin_chemistry(conn: sqlite3.Connection) -> None:
    """Insert skin chemistry data."""
    data = [
        (
            "sebum_composition",
            "squalene_pct",
            "15.0",
            "general",
        ),
        (
            "sebum_composition",
            "triglycerides_pct",
            "45.0",
            "general",
        ),
        (
            "sebum_composition",
            "wax_esters_pct",
            "25.0",
            "general",
        ),
        (
            "sebum_composition",
            "ffa_pct",
            "11.4",
            "general",
        ),
        (
            "sebum_composition",
            "cholesterol_pct",
            "1.2",
            "general",
        ),
        (
            "skin_ph",
            "ph_range",
            "4.5-6.0",
            "acidic mantle, Cutibacterium acnes secretes propionic acid",
        ),
        (
            "microbiome",
            "corynebacterium_activity",
            "Corynebacterium degrades aldehydes in axilla",
            "avoid aldehyde-heavy formulas for underarm use",
        ),
        (
            "microbiome",
            "staphylococcus_hominis_activity",
            "Staphylococcus hominis produces 3M3SH thioalcohol",
            "key body odor pathway",
        ),
        (
            "pro_fragrance",
            "glycosidase_hydrolysis",
            "Glycosidase enzymes hydrolyze GBVs to sustained release",
            "pro-fragrance delivery systems",
        ),
        (
            "site_recommendation",
            "wrist",
            "citrus preferred",
            "high blood flow near surface enhances citrus projection",
        ),
        (
            "site_recommendation",
            "neck",
            "musky preferred",
            "warmth enhances musk diffusion",
        ),
        (
            "site_recommendation",
            "behind_ears",
            "floral-musk preferred",
            "low airflow, intimate sillage",
        ),
    ]
    conn.executemany(
        "INSERT INTO skin_chemistry (topic, parameter, value, citation) VALUES (?,?,?,?)",
        data,
    )
    conn.commit()


def _populate_aging_reactions(conn: sqlite3.Connection) -> None:
    """Insert aging chemistry data."""
    data = [
        (
            "schiff_base",
            "aldehyde + methyl anthranilate",
            "imine",
            "k=0.00035 L/(mol·s)",
            "50% at 6.5 days, 90% at 90 days, rate doubles per 10°C",
            "causes yellow/brown discoloration",
            "general perfumery chemistry",
        ),
        (
            "acetal",
            "aldehyde + ethanol",
            "hemiacetal -> acetal",
            None,
            "competing with Schiff base, reversible on skin",
            "reversible protection of aldehydes",
            "general perfumery chemistry",
        ),
        (
            "ester_hydrolysis",
            "ester + water",
            "acid + alcohol",
            None,
            "acid-catalyzed at skin pH",
            "minimize water in concentrates",
            "general perfumery chemistry",
        ),
        (
            "terpene_oxidation",
            "limonene",
            "carvone",
            None,
            "autooxidation via free radicals",
            "prevent with BHT",
            "general perfumery chemistry",
        ),
        (
            "terpene_oxidation",
            "linalool",
            "linalool oxides",
            None,
            "autooxidation via free radicals",
            "earthy woody off-note",
            "general perfumery chemistry",
        ),
        (
            "transesterification",
            "ester + alcohol",
            "different ester",
            None,
            "~3 months equilibrium",
            "long-term storage changes profile",
            "general perfumery chemistry",
        ),
    ]
    conn.executemany(
        "INSERT INTO aging_reactions (reaction_type, reactants, products, rate_constant, conditions, practical_implication, citation) VALUES (?,?,?,?,?,?,?)",
        data,
    )
    conn.commit()


def _populate_mixture_models(conn: sqlite3.Connection) -> None:
    """Insert mixture interaction physics data."""
    data = [
        (
            "component_limit",
            "Humans identify max 4±1 odorants in mixture",
            None,
            "Livermore & Laing 1998",
        ),
        (
            "interaction_types",
            "Hypoadditivity (suppression) is MOST COMMON; hyperadditivity rare, only near threshold",
            None,
            "Rospars et al 2008",
        ),
        (
            "competitive_antagonism",
            "Competitive antagonism between odorants at OR binding sites follows binding kinetics",
            "F(U,V) = F_max / [1 + (K_U_app / (U + K_U_app/K_V * V))^n]",
            "Reddy et al 2018",
        ),
        (
            "configural_perception",
            "Familiar accords processed as single entities; unfamiliar mixtures analyzed by component",
            None,
            "Wilson & Stevenson 2006",
        ),
    ]
    conn.executemany(
        "INSERT INTO mixture_models (topic, finding, equation, citation) VALUES (?,?,?,?)",
        data,
    )
    conn.commit()


def _populate_climate_profiles(conn: sqlite3.Connection) -> None:
    """Insert climate effect profiles."""
    data = [
        ("Paris", 22.0, 50.0, 1.0, 1.0, "baseline"),
        (
            "Bangkok",
            35.0,
            80.0,
            2.8,
            0.5,
            "top notes burn off in minutes, overall longevity reduced 40-50%",
        ),
        (
            "Dubai",
            42.0,
            20.0,
            3.6,
            0.3,
            "extreme heat, very fast evaporation",
        ),
        ("New York", 25.0, 60.0, 1.2, 0.9, "mild climate"),
    ]
    conn.executemany(
        "INSERT INTO climate_profiles (profile_name, temperature_c, humidity_pct, vp_multiplier, longevity_factor, notes) VALUES (?,?,?,?,?,?)",
        data,
    )
    conn.commit()


def _populate_fabric_retention(conn: sqlite3.Connection) -> None:
    """Insert fabric substantivity data."""
    data = [
        (None, "cotton", None, 0.36, "Escher & Oliveros 1994"),
        (None, "polyester", None, None, "Escher & Oliveros 1994"),
        (None, "microencapsulation", None, None, "general"),
    ]
    conn.executemany(
        "INSERT INTO fabric_retention (material_name, fabric_type, retention_coefficient, log_k, citation) VALUES (?,?,?,?,?)",
        data,
    )
    conn.commit()


def _populate_masking_rules(conn: sqlite3.Connection) -> None:
    """Insert masking rules data."""
    data = [
        (
            "Patchouli",
            "citrus oxidation (carvone)",
            "competitive",
            10.0,
            "strong character overwhelms off-notes",
        ),
        (
            "Vanillin",
            "sour/acidic notes",
            "non-competitive",
            3.0,
            "sweetness covers",
        ),
        (
            "Coumarin",
            "harsh aldehydes",
            "non-competitive",
            5.5,
            "creamy-sweet blanket",
        ),
        (
            "Iso E Super",
            "synthetic harshness",
            "non-competitive",
            25.0,
            "molecular cocoon",
        ),
        (
            "Hedione",
            "harsh top notes",
            "non-competitive",
            12.5,
            "radiance amplifier",
        ),
        (
            "Benzyl Salicylate",
            "harsh florals",
            "non-competitive",
            10.0,
            "cosmetic cushion",
        ),
        (
            "Ambrox",
            "metallic notes",
            "competitive",
            3.0,
            "mineral transparency",
        ),
        (
            "Citronellal",
            "amines via Schiff base",
            "chemical_neutralization",
            0.55,
            "reactive masking",
        ),
        (
            "Zinc ricinoleate",
            "sulfur compounds",
            "chemical_neutralization",
            1.25,
            "deodorant counteractant",
        ),
        (
            "Cyclodextrins",
            "malodor molecules",
            "chemical_neutralization",
            0.55,
            "physical encapsulation",
        ),
    ]
    conn.executemany(
        "INSERT INTO masking_rules (masking_material, masks_what, mechanism, use_level_pct, notes) VALUES (?,?,?,?,?)",
        data,
    )
    conn.commit()


def _populate_dose_response_cliffs(conn: sqlite3.Connection) -> None:
    """Insert dose-response cliff data."""
    data = [
        ("Indole", 0.01, "faint powdery", "positive", None),
        ("Indole", 0.1, "narcotic creamy floral", "positive", None),
        ("Indole", 1.0, "floral with animalic edge", "neutral", None),
        (
            "Indole",
            1.0,
            "fecal repulsive",
            "dangerous",
            "sharp cliff, not gradual",
        ),
        ("Galaxolide", 0.1, "invisible fixative", "neutral", None),
        ("Galaxolide", 1.0, "clean musk", "positive", None),
        ("Galaxolide", 5.0, "rich floral-woody musk", "positive", None),
        (
            "Galaxolide",
            15.0,
            "transparent overdose (Grojsman technique)",
            "positive",
            "paradoxically transparent at extreme dose",
        ),
        ("Ambrox", 1.0, "clean mineral", "positive", None),
        ("Ambrox", 5.0, "urinous animalic", "negative", "turn"),
        ("Coumarin", 1.0, "sweet hay", "positive", None),
        ("Coumarin", 10.0, "bitter medicinal", "negative", None),
        (
            "Iso E Super",
            1.0,
            "imperceptible",
            "neutral",
            None,
        ),
        (
            "Iso E Super",
            10.0,
            "woody skin-scent",
            "positive",
            "the 'what are you wearing' effect",
        ),
        ("Skatole", 0.1, "fecal", "negative", "always fecal, no transition"),
        ("Civetone", 0.01, "floral-fruity trace", "positive", None),
        ("Civetone", 0.1, "animalic fecal", "negative", None),
    ]
    # The >1% indole entry has same concentration_pct=1.0 but different character/quality
    # Use INSERT explicitly to avoid dedup conflict
    for row in data:
        conn.execute(
            "INSERT INTO dose_response_cliffs (material_name, concentration_pct, character, quality, notes) VALUES (?,?,?,?,?)",
            row,
        )
    conn.commit()


# ── Public population entry point ──────────────────────────────────────


def populate_science_kb(db_path: str = _DB_DEFAULT) -> str:
    """Create (if not exists) and populate all 10 science-domain tables.

    Ensures tables exist via IF NOT EXISTS (from :mod:`engine.kb_schema`),
    then inserts data.  Safe to call multiple times — data rows may
    duplicate on re-run for tables without UNIQUE constraints.
    """
    abs_path = os.path.abspath(db_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    from engine.kb_schema import create_database

    create_database(abs_path)
    conn = _get_conn(abs_path, writable=True)

    try:
        _populate_or_biophysics(conn)
        _populate_material_anosmia(conn)
        _populate_evaporation_model(conn)
        _populate_unifac_groups(conn)
        _populate_skin_chemistry(conn)
        _populate_aging_reactions(conn)
        _populate_mixture_models(conn)
        _populate_climate_profiles(conn)
        _populate_fabric_retention(conn)
        _populate_masking_rules(conn)
        _populate_dose_response_cliffs(conn)
    finally:
        conn.close()

    return abs_path


# ═══════════════════════════════════════════════════════════════════════
# Query API
# ═══════════════════════════════════════════════════════════════════════


def _query(
    sql: str,
    params: tuple = (),
    db_path: str | None = None,
) -> list[dict]:
    """Execute a SELECT and return results as list of dicts."""
    conn = _get_conn(db_path or _DB_DEFAULT)
    try:
        rows = conn.execute(sql, params).fetchall()
        return _rows_to_dicts(rows)
    finally:
        conn.close()


def _query_one(
    sql: str,
    params: tuple = (),
    db_path: str | None = None,
) -> dict | None:
    """Execute a SELECT and return a single dict or None."""
    conn = _get_conn(db_path or _DB_DEFAULT)
    try:
        row = conn.execute(sql, params).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


# ── Domain 1: OR biophysics ────────────────────────────────────────────


def get_or_biophysics(topic: str | None = None) -> list[dict]:
    """Return OR biophysics entries, optionally filtered by *topic*."""
    if topic:
        return _query(
            "SELECT * FROM or_biophysics WHERE topic = ? ORDER BY id", (topic,)
        )
    return _query("SELECT * FROM or_biophysics ORDER BY id")


def get_anosmia_rate(material: str) -> dict | None:
    """Return anosmia data for *material*, or ``None``."""
    return _query_one(
        "SELECT * FROM material_anosmia WHERE LOWER(material_name) LIKE ? ORDER BY id LIMIT 1",
        (f"%{material.lower()}%",),
    )


# ── Domain 2: Evaporation ──────────────────────────────────────────────


def get_evaporation_model(parameter: str | None = None) -> list[dict]:
    """Return evaporation-model entries, optionally filtered by *parameter*."""
    if parameter:
        return _query(
            "SELECT * FROM evaporation_model WHERE parameter = ? ORDER BY id",
            (parameter,),
        )
    return _query("SELECT * FROM evaporation_model ORDER BY id")


# ── Domain 3: UNIFAC groups ────────────────────────────────────────────


def get_unifac_groups() -> list[dict]:
    """Return all UNIFAC functional groups."""
    return _query("SELECT * FROM unifac_groups ORDER BY group_name")


# ── Domain 4: Skin chemistry ───────────────────────────────────────────


def get_skin_chemistry(topic: str | None = None) -> list[dict]:
    """Return skin-chemistry entries, optionally filtered by *topic*."""
    if topic:
        return _query(
            "SELECT * FROM skin_chemistry WHERE topic = ? ORDER BY id", (topic,)
        )
    return _query("SELECT * FROM skin_chemistry ORDER BY id")


# ── Domain 5: Aging reactions ──────────────────────────────────────────


def get_aging_reactions(reaction_type: str | None = None) -> list[dict]:
    """Return aging-reaction entries, optionally filtered by *reaction_type*."""
    if reaction_type:
        return _query(
            "SELECT * FROM aging_reactions WHERE reaction_type = ? ORDER BY id",
            (reaction_type,),
        )
    return _query("SELECT * FROM aging_reactions ORDER BY id")


# ── Domain 6: Mixture models ───────────────────────────────────────────


def get_mixture_models(topic: str | None = None) -> list[dict]:
    """Return mixture-model entries, optionally filtered by *topic*."""
    if topic:
        return _query(
            "SELECT * FROM mixture_models WHERE topic = ? ORDER BY id", (topic,)
        )
    return _query("SELECT * FROM mixture_models ORDER BY id")


# ── Domain 7: Climate effects ──────────────────────────────────────────


def get_climate_profile(name: str) -> dict | None:
    """Return a single climate profile by *name*, or ``None``."""
    return _query_one(
        "SELECT * FROM climate_profiles WHERE LOWER(profile_name) = LOWER(?)",
        (name,),
    )


def get_climate_profiles() -> list[dict]:
    """Return all climate profiles."""
    return _query("SELECT * FROM climate_profiles ORDER BY profile_name")


# ── Domain 8: Fabric retention ─────────────────────────────────────────


def get_fabric_retention(fabric_type: str | None = None) -> list[dict]:
    """Return fabric-retention entries, optionally filtered by *fabric_type*."""
    if fabric_type:
        return _query(
            "SELECT * FROM fabric_retention WHERE LOWER(fabric_type) = LOWER(?) ORDER BY id",
            (fabric_type,),
        )
    return _query("SELECT * FROM fabric_retention ORDER BY id")


# ── Domain 9: Masking rules ────────────────────────────────────────────


def get_masking_rules() -> list[dict]:
    """Return all masking rules."""
    return _query("SELECT * FROM masking_rules ORDER BY id")


def get_masking_for_material(material: str) -> list[dict]:
    """Return masking rules where *material* is the masking_material."""
    return _query(
        "SELECT * FROM masking_rules WHERE LOWER(masking_material) LIKE LOWER(?) ORDER BY id",
        (f"%{material}%",),
    )


# ── Domain 10: Dose-response cliffs ────────────────────────────────────


def get_dose_response_cliffs(material: str) -> list[dict]:
    """Return dose-response cliff entries for *material*."""
    return _query(
        "SELECT * FROM dose_response_cliffs WHERE LOWER(material_name) LIKE LOWER(?) ORDER BY id",
        (f"%{material}%",),
    )


# ── Summary ────────────────────────────────────────────────────────────


def get_all_science(db_path: str | None = None) -> dict:
    """Return a summary dict with row counts for each science domain."""
    conn = _get_conn(db_path or _DB_DEFAULT)
    try:
        tables = [
            "or_biophysics",
            "material_anosmia",
            "evaporation_model",
            "unifac_groups",
            "skin_chemistry",
            "aging_reactions",
            "mixture_models",
            "climate_profiles",
            "fabric_retention",
            "masking_rules",
            "dose_response_cliffs",
        ]
        summary: dict[str, int] = {}
        for tbl in tables:
            row = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
            summary[tbl] = row[0] if row else 0
        return summary
    finally:
        conn.close()
