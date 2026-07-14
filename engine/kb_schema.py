# allow: SIZE_OK — pure schema/data-table module

"""
SQLite database schema for the perfumery knowledge engine.

Creates all tables with IF NOT EXISTS. Every table has an auto-increment
integer primary key named ``id``.

Usage:
    from engine.kb_schema import create_database
    create_database("data/perfumery_kb.db")
"""

import sqlite3
import os


def _create_tables(conn: sqlite3.Connection) -> None:
    """Execute all CREATE TABLE IF NOT EXISTS statements."""
    cur = conn.cursor()

    # ── Material tables ──────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_name TEXT UNIQUE,
            cas TEXT,
            smiles TEXT,
            inchikey TEXT,
            mw_g_mol REAL,
            density_25c_g_ml REAL,
            logp REAL,
            vp_25c_pa REAL,
            odt_air_ppb REAL,
            odt_eth_ppm REAL,
            note TEXT,
            role TEXT,
            texture TEXT,
            character_json TEXT,
            synergies_json TEXT,
            activity_coef REAL,
            hedonic REAL,
            odor_family TEXT,
            ifra_cat4_limit_pct REAL,
            user_stock_dilution TEXT,
            user_in_inventory INTEGER,
            stevens_n REAL,
            vp_source TEXT,
            vp_flag TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS material_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER REFERENCES materials(id),
            alias_name TEXT UNIQUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS material_natural_decomposition (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER REFERENCES materials(id),
            constituent_name TEXT,
            weight_frac REAL,
            mw REAL,
            vp REAL,
            odt_air_ppb REAL,
            odt_eth_ppm REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name TEXT,
            field TEXT,
            db_value TEXT,
            pubchem_value TEXT,
            delta TEXT,
            action TEXT
        )
    """)

    # ── Interaction tables ───────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS material_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_a TEXT,
            material_b TEXT,
            type TEXT,
            effect TEXT,
            magnitude REAL,
            source TEXT,
            context TEXT
        )
    """)

    # ── Rules tables ─────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS family_archetypes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            family TEXT,
            label TEXT,
            role TEXT,
            forbidden_materials_json TEXT,
            forbidden_tokens_json TEXT,
            novelty_reference TEXT,
            novelty_message TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS archetype_anchors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archetype_id INTEGER REFERENCES family_archetypes(id),
            group_name TEXT,
            materials_json TEXT,
            basis TEXT,
            minimum REAL,
            maximum REAL,
            detail TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS archetype_drift_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archetype_id INTEGER REFERENCES family_archetypes(id),
            group_name TEXT,
            materials_json TEXT,
            basis TEXT,
            minimum REAL,
            maximum REAL,
            detail TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS archetype_oav_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archetype_id INTEGER REFERENCES family_archetypes(id),
            time_window TEXT,
            odor_family TEXT,
            target_oav REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS archetype_repair_pool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archetype_id INTEGER REFERENCES family_archetypes(id),
            material_name TEXT,
            dose REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pyramid_ratios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_key TEXT,
            bracket TEXT,
            top_pct REAL,
            heart_pct REAL,
            base_pct REAL,
            description TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS oav_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_key TEXT,
            time_window TEXT,
            odor_family TEXT,
            target_oav REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS material_role_ratios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            style TEXT,
            role TEXT,
            min_pct REAL,
            max_pct REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cross_family_compatibility (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_a TEXT,
            family_b TEXT,
            compatibility_level TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS family_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT,
            family_key TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS note_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT,
            note_tier TEXT
        )
    """)

    # ── Safety tables ────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ifra_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name TEXT UNIQUE,
            cat4_limit_pct REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS eu_allergens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name TEXT,
            cas TEXT,
            leave_on_threshold_pct REAL,
            rinse_off_threshold_pct REAL,
            risk TEXT,
            note TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sensitization (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name TEXT,
            ec3 REAL,
            potency TEXT,
            source TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS banned_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name TEXT UNIQUE,
            reason TEXT
        )
    """)

    # ── Dose-response tables ─────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS character_shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name TEXT,
            max_conc_pct REAL,
            character TEXT,
            quality TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS hill_params (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name TEXT,
            ec50 REAL,
            n REAL,
            rmax REAL
        )
    """)

    # ── Gate embedded tables ─────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS olfactory_fatigue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name TEXT,
            warn_oav REAL,
            fail_oav REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS jellinek_classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name TEXT,
            class TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS adaptation_tiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tier TEXT,
            materials_json TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS iconic_skeletons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family TEXT,
            marker_materials_json TEXT,
            source_reference TEXT
        )
    """)

    # ── Knowledge graph reference ────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS theory_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            key TEXT,
            value_json TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS accords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            key TEXT,
            value_json TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ingredient_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            identity_key TEXT,
            category TEXT,
            status TEXT,
            owned INTEGER,
            notes_json TEXT
        )
    """)

    # ── Formula memory tables ────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS formulas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            date TEXT,
            family_archetype TEXT,
            batch_size_ml REAL,
            concentrate_ul REAL,
            status TEXT,
            file_path TEXT,
            rationale TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS formula_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            formula_id INTEGER REFERENCES formulas(id),
            material_name TEXT,
            dilution TEXT,
            amount_ul REAL,
            role TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            formula_id INTEGER REFERENCES formulas(id),
            gate_name TEXT,
            status TEXT,
            detail TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            formula_id INTEGER REFERENCES formulas(id),
            rating REAL,
            feedback_text TEXT,
            feedback_tags_json TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            formula_id INTEGER,
            symptom TEXT,
            root_cause TEXT,
            fix TEXT,
            learning TEXT,
            applicable_materials_json TEXT
        )
    """)

    # ── Science knowledge tables (10 domains) ─────────────────────────

    # Domain 1: Olfactory receptor biophysics
    cur.execute("""
        CREATE TABLE IF NOT EXISTS or_biophysics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            finding TEXT,
            citation TEXT,
            practical_implication TEXT
        )
    """)

    # Specific anosmia rates
    cur.execute("""
        CREATE TABLE IF NOT EXISTS material_anosmia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name TEXT,
            anosmia_pct REAL,
            receptor TEXT,
            source TEXT
        )
    """)

    # Domain 2: Evaporation kinetics
    cur.execute("""
        CREATE TABLE IF NOT EXISTS evaporation_model (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parameter TEXT,
            material_name TEXT,
            value TEXT,
            citation TEXT
        )
    """)

    # Domain 3: UNIFAC activity coefficients
    cur.execute("""
        CREATE TABLE IF NOT EXISTS unifac_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT UNIQUE,
            group_smiles TEXT,
            contribution_vp REAL,
            contribution_logp REAL
        )
    """)

    # Domain 4: Skin chemistry
    cur.execute("""
        CREATE TABLE IF NOT EXISTS skin_chemistry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            parameter TEXT,
            value TEXT,
            citation TEXT
        )
    """)

    # Domain 5: Aging chemistry
    cur.execute("""
        CREATE TABLE IF NOT EXISTS aging_reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reaction_type TEXT,
            reactants TEXT,
            products TEXT,
            rate_constant TEXT,
            conditions TEXT,
            practical_implication TEXT,
            citation TEXT
        )
    """)

    # Domain 6: Mixture interaction physics
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mixture_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            finding TEXT,
            equation TEXT,
            citation TEXT
        )
    """)

    # Domain 7: Climate effects
    cur.execute("""
        CREATE TABLE IF NOT EXISTS climate_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_name TEXT,
            temperature_c REAL,
            humidity_pct REAL,
            vp_multiplier REAL,
            longevity_factor REAL,
            notes TEXT
        )
    """)

    # Domain 8: Fabric substantivity
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fabric_retention (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name TEXT,
            fabric_type TEXT,
            retention_coefficient REAL,
            log_k REAL,
            citation TEXT
        )
    """)

    # Domain 9: Masking rules
    cur.execute("""
        CREATE TABLE IF NOT EXISTS masking_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            masking_material TEXT,
            masks_what TEXT,
            mechanism TEXT,
            use_level_pct REAL,
            notes TEXT
        )
    """)

    # Domain 10: Dose-response cliffs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dose_response_cliffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name TEXT,
            concentration_pct REAL,
            character TEXT,
            quality TEXT,
            notes TEXT
        )
    """)

    conn.commit()


def create_database(db_path: str) -> str:
    """Create (or re-use) the SQLite database at *db_path*.

    Returns the absolute path of the created database.
    """
    abs_path = os.path.abspath(db_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    conn = sqlite3.connect(abs_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _create_tables(conn)
    finally:
        conn.close()
    return abs_path
