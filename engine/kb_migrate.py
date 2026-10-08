"""Migration: read 7+ source data stores into the perfumery knowledge SQLite DB.

Usage::

    from engine.kb_migrate import migrate
    migrate("data/perfumery_kb.db")

Priority for material physics fields (highest to lowest):
    1. data/materials/*.yaml  (MW, logP, VP, density)
    2. ingredient_intelligence._PROFILES  (character, note, role, texture)
    3. odor_thresholds.ODT_DATA  (ODT values)
    4. material_properties.json  (gap-fill)
    5. data/regulatory/ifra_cat4_51.json via engine.ifra_standards  (IFRA limits;
       overrides the gap-fill for every material the sourced table knows)
"""

from __future__ import annotations

import glob
import json
import os
import sqlite3

import yaml

from engine.ifra_standards import load_ifra_table
from engine.kb_schema import create_database
from engine.name_utils import normalize_name

# ── Low-level helpers ────────────────────────────────────────────────


def _load_yaml_entries() -> dict[str, dict]:
    """Return dict[canonical_name, entry] from all data/materials/*.yaml files.

    Handles two edge cases:
    * Some entries use ``name`` instead of ``canonical_name``.
    * Some canonical_names appear multiple times (duplicates) — the
      in-inventory version is preferred.
    """
    entries: dict[str, dict] = {}
    for path in sorted(glob.glob("data/materials/*.yaml")):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data is None:
                continue
            for entry in data:
                name = entry.get("canonical_name") or entry.get("name")
                if not name:
                    continue
                # Prefer in-inventory entries over non-inventory duplicates
                if name in entries:
                    existing_inv = entries[name].get("user_in_inventory")
                    new_inv = entry.get("user_in_inventory")
                    if new_inv and not existing_inv:
                        entries[name] = entry
                    # If both are in-inventory, keep the first
                else:
                    entries[name] = entry
    return entries


def _load_material_properties() -> dict[str, dict]:
    """Read material_properties.json → dict[name, entry]."""
    path = "data/knowledge_graph/material_properties.json"
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, list):
        return {e.get("name", ""): e for e in raw if e.get("name")}
    return {}


def _load_json_list(path: str) -> list:
    """Load a JSON file as a list."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _load_json_dict(path: str) -> dict:
    """Load a JSON file as a dict."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


# ── Material merge helpers ───────────────────────────────────────────


def _build_odt_lookup(odt_data: dict) -> dict[str, dict]:
    """Build a normalized-name → ODT entry lookup from ODT_DATA.

    ODT_DATA keys are already lowercased (e.g. ``"hedione": {...}``),
    but some have compound keys like ``"hedione hc": {...}``.
    """
    lookup: dict[str, dict] = {}
    for key, val in odt_data.items():
        norm = normalize_name(key)
        lookup[norm] = val
    return lookup


def _get_profile_value(profiles: dict, name: str, key: str, default=None):
    """Safely get a value from a _PROFILES entry by material name.

    Tries exact match first, then normalized alias resolution.
    """
    profile = profiles.get(name)
    if profile is not None:
        return profile.get(key, default)
    # Try alias lookup in _PROFILES
    for pname, pdata in profiles.items():
        if normalize_name(pname) == normalize_name(name):
            return pdata.get(key, default)
    return default


def _merge_material(
    name: str,
    yaml_e: dict,
    profiles: dict,
    odt_norm: dict,
    props: dict,
    ifra_limits: dict,
) -> dict:
    """Merge data from all sources for one material, with correct priority.

    Returns a dict of column → value suitable for INSERT.
    """
    norm = normalize_name(name)
    row: dict[str, object] = {"canonical_name": name}

    # ── 1. YAML (highest for physics) ──
    row["cas"] = yaml_e.get("cas")
    row["smiles"] = yaml_e.get("smiles")
    row["inchikey"] = yaml_e.get("inchikey")
    row["mw_g_mol"] = yaml_e.get("mw_g_mol")
    row["density_25c_g_ml"] = yaml_e.get("density_25c_g_ml")
    row["logp"] = yaml_e.get("logp")
    row["vp_25c_pa"] = yaml_e.get("vp_25c_pa")
    row["user_stock_dilution"] = (
        str(yaml_e.get("user_stock_dilution") or "") if yaml_e.get("user_stock_dilution") else None
    )
    row["user_in_inventory"] = 1 if yaml_e.get("user_in_inventory") else 0

    # YAML may also have ODT
    row["odt_air_ppb"] = yaml_e.get("odt_air_ppb")
    row["odt_eth_ppm"] = yaml_e.get("odt_eth_ppm")

    # ── 2. _PROFILES (character, note, role, texture) ──
    profile = profiles.get(name)
    if profile is None:
        # Try normalized lookup
        for pn, pd in profiles.items():
            if normalize_name(pn) == norm:
                profile = pd
                break

    if profile is not None:
        # Character fields
        row["note"] = profile.get("note", row.get("note"))
        row["role"] = profile.get("role", row.get("role"))
        row["texture"] = profile.get("texture", row.get("texture"))
        char = profile.get("character")
        if char:
            row["character_json"] = json.dumps(char)
        syns = profile.get("synergies")
        if syns:
            row["synergies_json"] = json.dumps(syns)

        # Physics from profile (only if YAML didn't provide)
        if row["mw_g_mol"] is None:
            row["mw_g_mol"] = profile.get("mw")
        if row["vp_25c_pa"] is None:
            row["vp_25c_pa"] = profile.get("vp")
        if row["logp"] is None:
            row["logp"] = profile.get("clogp")

        row["activity_coef"] = profile.get("activity_coef")
        row["hedonic"] = profile.get("hedonic")
        row["stevens_n"] = profile.get("stevens_n")
        row["vp_source"] = profile.get("vp_source")
        row["vp_flag"] = profile.get("vp_flag")

        # ODT from profile (if YAML didn't provide)
        if row["odt_air_ppb"] is None:
            row["odt_air_ppb"] = profile.get("odt")
        if row["odt_eth_ppm"] is None:
            row["odt_eth_ppm"] = profile.get("odt_ppm")

        # ⚠️ YAML always wins for VP (even over _VERIFIED_VP override)
        if yaml_e.get("vp_25c_pa") is not None:
            row["vp_25c_pa"] = yaml_e["vp_25c_pa"]
            row["vp_source"] = None
            row["vp_flag"] = None

    # ── 3. ODT_DATA (priority for ODT values, overrides profile but not YAML) ──
    odt_entry = odt_norm.get(norm)
    if odt_entry:
        if yaml_e.get("odt_air_ppb") is None:
            odt_air = odt_entry.get("odt_air") if isinstance(odt_entry, dict) else None
            if odt_air is None:
                odt_air = odt_entry.get("odt_air_ppb")
            if odt_air is not None:
                row["odt_air_ppb"] = odt_air

        if yaml_e.get("odt_eth_ppm") is None:
            odt_eth = odt_entry.get("odt_eth") if isinstance(odt_entry, dict) else None
            if odt_eth is None:
                odt_eth = odt_entry.get("odt_eth_ppm")
            if odt_eth is not None:
                row["odt_eth_ppm"] = odt_eth

    # ── 4. material_properties.json (gap-fill) ──
    prop = props.get(name)
    if prop is None:
        for pn in props:
            if normalize_name(pn) == norm:
                prop = props[pn]
                break
    if prop is not None:
        if row.get("mw_g_mol") is None:
            row["mw_g_mol"] = prop.get("mw")
        if row.get("vp_25c_pa") is None:
            row["vp_25c_pa"] = prop.get("vp")
        if row.get("logp") is None:
            row["logp"] = prop.get("clp")
        if row.get("odt_air_ppb") is None:
            row["odt_air_ppb"] = prop.get("odt")
        if row.get("odt_eth_ppm") is None:
            row["odt_eth_ppm"] = prop.get("odt_ethanol_ppm")
        if row.get("note") is None:
            row["note"] = prop.get("note")
        if row.get("role") is None:
            row["role"] = prop.get("role")
        if row.get("texture") is None:
            row["texture"] = prop.get("texture")
        if row.get("activity_coef") is None:
            row["activity_coef"] = prop.get("activity_coef")
        if row.get("hedonic") is None:
            row["hedonic"] = prop.get("hedonic")
        if row.get("odor_family") is None:
            row["odor_family"] = prop.get("odor_family")
        if row.get("stevens_n") is None:
            row["stevens_n"] = prop.get("hill_n")
        if row.get("character_json") is None:
            char = prop.get("character_shift")
            if char:
                if isinstance(char, dict):
                    row["character_json"] = json.dumps(char)
                else:
                    row["character_json"] = json.dumps({char: 1})
        if row.get("ifra_cat4_limit_pct") is None:
            row["ifra_cat4_limit_pct"] = prop.get("ifra_cat4_limit_pct")

    # ── 5. Sourced IFRA Cat 4 table (authoritative where it has the material) ──
    if name in ifra_limits:
        row["ifra_cat4_limit_pct"] = ifra_limits[name]
    else:
        for ifra_name, ifra_v in ifra_limits.items():
            if normalize_name(ifra_name) == norm:
                row["ifra_cat4_limit_pct"] = ifra_v
                break

    return row


# ── Population functions ─────────────────────────────────────────────


def _ifra_material_limits() -> dict[str, float | None]:
    """Materials-table IFRA column from the sourced Cat 4 table.

    Every name (canonical and alias) the table knows maps to its Category 4
    limit (% w/w finished product): the limit when restricted, 0.0 when
    prohibited, ``None`` for any other status (no numeric limit).
    """
    limits: dict[str, float | None] = {}
    for material in load_ifra_table().materials.values():
        if material.status == "restricted":
            value = material.cat4_limit_pct
        elif material.status == "prohibited":
            value = 0.0
        else:
            value = None
        for alias in (material.name, *material.aliases):
            limits[alias] = value
    return limits


def _populate_materials(conn: sqlite3.Connection) -> dict[str, int]:
    """Insert materials table.

    Returns dict[canonical_name → material_id].
    """
    yaml_entries = _load_yaml_entries()
    profiles: dict = {}
    props = _load_material_properties()
    ifra_limits = _ifra_material_limits()

    # Import engine modules (lazy, inside function)
    from engine.ingredient_intelligence import _PROFILES  # noqa: PLC0415
    from engine.odor_thresholds import ODT_DATA  # noqa: PLC0415

    profiles = _PROFILES
    odt_norm = _build_odt_lookup(ODT_DATA)

    insert_sql = """
        INSERT OR REPLACE INTO materials (
            canonical_name, cas, smiles, inchikey,
            mw_g_mol, density_25c_g_ml, logp, vp_25c_pa,
            odt_air_ppb, odt_eth_ppm,
            note, role, texture, character_json, synergies_json,
            activity_coef, hedonic, odor_family, ifra_cat4_limit_pct,
            user_stock_dilution, user_in_inventory,
            stevens_n, vp_source, vp_flag
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """

    name_to_id: dict[str, int] = {}

    # Track which names we've inserted
    inserted_names: set[str] = set()

    for name, yaml_e in yaml_entries.items():
        row = _merge_material(name, yaml_e, profiles, odt_norm, props, ifra_limits)
        conn.execute(
            insert_sql,
            (
                row.get("canonical_name"),
                row.get("cas"),
                row.get("smiles"),
                row.get("inchikey"),
                row.get("mw_g_mol"),
                row.get("density_25c_g_ml"),
                row.get("logp"),
                row.get("vp_25c_pa"),
                row.get("odt_air_ppb"),
                row.get("odt_eth_ppm"),
                row.get("note"),
                row.get("role"),
                row.get("texture"),
                row.get("character_json"),
                row.get("synergies_json"),
                row.get("activity_coef"),
                row.get("hedonic"),
                row.get("odor_family"),
                row.get("ifra_cat4_limit_pct"),
                row.get("user_stock_dilution"),
                row.get("user_in_inventory"),
                row.get("stevens_n"),
                row.get("vp_source"),
                row.get("vp_flag"),
            ),
        )
        name_to_id[name] = conn.execute(
            "SELECT id FROM materials WHERE canonical_name = ?", (name,)
        ).fetchone()[0]
        inserted_names.add(normalize_name(name))

    # Also add profile-only materials not in YAML
    for pname, pdata in profiles.items():
        pnorm = normalize_name(pname)
        if pnorm in inserted_names:
            continue
        row = _merge_material(pname, {}, profiles, odt_norm, props, ifra_limits)
        conn.execute(
            insert_sql,
            (
                row.get("canonical_name") or pname,
                row.get("cas"),
                row.get("smiles"),
                row.get("inchikey"),
                row.get("mw_g_mol"),
                row.get("density_25c_g_ml"),
                row.get("logp"),
                row.get("vp_25c_pa"),
                row.get("odt_air_ppb"),
                row.get("odt_eth_ppm"),
                row.get("note"),
                row.get("role"),
                row.get("texture"),
                row.get("character_json"),
                row.get("synergies_json"),
                row.get("activity_coef"),
                row.get("hedonic"),
                row.get("odor_family"),
                row.get("ifra_cat4_limit_pct"),
                row.get("user_stock_dilution"),
                row.get("user_in_inventory"),
                row.get("stevens_n"),
                row.get("vp_source"),
                row.get("vp_flag"),
            ),
        )
        cname = row.get("canonical_name") or pname
        name_to_id[cname] = conn.execute(
            "SELECT id FROM materials WHERE canonical_name = ?", (cname,)
        ).fetchone()[0]
        inserted_names.add(pnorm)

    # Also add ODT-only materials not yet inserted
    for odt_key, odt_val in odt_norm.items():
        if odt_key in inserted_names:
            continue
        # Find a usable canonical name
        cname = odt_key
        row = _merge_material(cname, {}, profiles, odt_norm, props, ifra_limits)
        conn.execute(
            insert_sql,
            (
                row.get("canonical_name") or cname,
                row.get("cas"),
                row.get("smiles"),
                row.get("inchikey"),
                row.get("mw_g_mol"),
                row.get("density_25c_g_ml"),
                row.get("logp"),
                row.get("vp_25c_pa"),
                row.get("odt_air_ppb"),
                row.get("odt_eth_ppm"),
                row.get("note"),
                row.get("role"),
                row.get("texture"),
                row.get("character_json"),
                row.get("synergies_json"),
                row.get("activity_coef"),
                row.get("hedonic"),
                row.get("odor_family"),
                row.get("ifra_cat4_limit_pct"),
                row.get("user_stock_dilution"),
                row.get("user_in_inventory"),
                row.get("stevens_n"),
                row.get("vp_source"),
                row.get("vp_flag"),
            ),
        )
        rcname = row.get("canonical_name") or cname
        name_to_id[rcname] = conn.execute(
            "SELECT id FROM materials WHERE canonical_name = ?", (rcname,)
        ).fetchone()[0]
        inserted_names.add(odt_key)

    conn.commit()
    return name_to_id


def _populate_aliases(conn: sqlite3.Connection, name_to_id: dict[str, int]) -> None:
    """Insert material_aliases from YAML ``aliases`` field and inventory names.

    YAML aliases come from the ``aliases`` list in each material entry.
    Inventory names from ``inventory.txt`` are also added so that
    ``test_every_inventory_material_exists`` can resolve dilution-suffixed
    names like ``"Cinnamyl alcohol 50% in DPG"`` to their base material.
    """
    yaml_entries = _load_yaml_entries()

    # Collect YAML aliases
    for name, entry in yaml_entries.items():
        aliases = entry.get("aliases", []) or []
        mid = name_to_id.get(name)
        if mid is None:
            continue
        for alias in aliases:
            if alias and alias.strip():
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO material_aliases (material_id, alias_name) VALUES (?, ?)",
                        (mid, alias.strip()),
                    )
                except sqlite3.IntegrityError:
                    pass

    # Also add inventory-parsed names as aliases for materials they match
    from engine.inventory_parser import parse_inventory  # noqa: PLC0415

    inv_materials = parse_inventory(unique=False)
    for inv_mat in inv_materials:
        inv_name = inv_mat.name
        if inv_name in name_to_id:
            continue  # exact match, no alias needed
        # Find best match by substring overlap in normalized forms
        inv_norm = normalize_name(inv_name)
        best_mid = None
        best_score = 0
        for cname, mid in name_to_id.items():
            cname_norm = normalize_name(cname)
            # Exact norm match
            if cname_norm == inv_norm:
                best_mid = mid
                break
            # One contains the other
            if cname_norm in inv_norm or inv_norm in cname_norm:
                score = max(len(cname_norm), len(inv_norm)) / min(len(cname_norm), len(inv_norm))
                if score > best_score:
                    best_score = score
                    best_mid = mid
        if best_mid is not None:
            conn.execute(
                "INSERT OR IGNORE INTO material_aliases (material_id, alias_name) VALUES (?, ?)",
                (best_mid, inv_name),
            )

    conn.commit()


def _populate_natural_decomposition(conn: sqlite3.Connection, name_to_id: dict[str, int]) -> None:
    """Insert material_natural_decomposition from _ABSOLUTE_CONSTITUENTS."""
    from engine.pipeline.natural_absolute_decomposition import (  # noqa: PLC0415
        _ABSOLUTE_CONSTITUENTS,
    )

    insert_sql = """
        INSERT INTO material_natural_decomposition
            (material_id, constituent_name, weight_frac, mw, vp, odt_air_ppb, odt_eth_ppm)
        VALUES (?,?,?,?,?,?,?)
    """
    count = 0
    for mat_name, constituents in _ABSOLUTE_CONSTITUENTS.items():
        mid = name_to_id.get(mat_name)
        if mid is None:
            # Try normalized
            for canonical, cid in name_to_id.items():
                if normalize_name(canonical) == normalize_name(mat_name):
                    mid = cid
                    break
        if mid is None:
            continue
        for c in constituents:
            conn.execute(
                insert_sql,
                (
                    mid,
                    c[0],
                    c[1] if len(c) > 1 else None,
                    c[2] if len(c) > 2 else None,
                    c[3] if len(c) > 3 else None,
                    c[4] if len(c) > 4 else None,
                    c[5] if len(c) > 5 else None,
                ),
            )
            count += 1
    conn.commit()


def _populate_audit_flags(conn: sqlite3.Connection) -> None:
    """Insert audit_flags from audit_flags.json."""
    flags = _load_json_list("data/knowledge_graph/audit_flags.json")
    insert_sql = """
        INSERT INTO audit_flags (material_name, field, db_value, pubchem_value, delta, action)
        VALUES (?,?,?,?,?,?)
    """
    for entry in flags:
        name = entry.get("name", "")
        for flag in entry.get("flags", []):
            conn.execute(
                insert_sql,
                (
                    name,
                    flag.get("field"),
                    str(flag.get("db_value", "")),
                    str(flag.get("pubchem_value", "")),
                    str(flag.get("delta", "")),
                    flag.get("action"),
                ),
            )
    conn.commit()


def _populate_interactions(conn: sqlite3.Connection) -> None:
    """Insert material_interactions from pairing_rules data files."""
    sources = [
        ("pairing_rules.json", "data/knowledge_graph/pairing_rules.json"),
        (
            "pairing_rules_discovered.json",
            "data/knowledge_graph/pairing_rules_discovered.json",
        ),
        ("synergy_matrix.json", "data/knowledge_graph/synergy_matrix.json"),
    ]
    insert_sql = """
        INSERT INTO material_interactions (material_a, material_b, type, effect, magnitude, source, context)
        VALUES (?,?,?,?,?,?,?)
    """
    total = 0
    for src_label, path in sources:
        data = _load_json_list(path)
        for entry in data:
            conn.execute(
                insert_sql,
                (
                    entry.get("material_a") or entry.get("ingredient_a", ""),
                    entry.get("material_b") or entry.get("ingredient_b", ""),
                    entry.get("type", "pairing"),
                    entry.get("effect", ""),
                    entry.get("magnitude"),
                    src_label,
                    json.dumps(entry),
                ),
            )
            total += 1
    conn.commit()


def _populate_archetypes(conn: sqlite3.Connection) -> dict[str, int]:
    """Insert family_archetypes + anchors, drift_limits, oav_targets, repair_pool.

    Returns dict[key → archetype_id].
    """
    from engine.families.registry import ARCHETYPES  # noqa: PLC0415

    key_to_id: dict[str, int] = {}

    arch_insert = """
        INSERT INTO family_archetypes (key, family, label, role, forbidden_materials_json, forbidden_tokens_json, novelty_reference, novelty_message)
        VALUES (?,?,?,?,?,?,?,?)
    """
    anchor_insert = """
        INSERT INTO archetype_anchors (archetype_id, group_name, materials_json, basis, minimum, maximum, detail)
        VALUES (?,?,?,?,?,?,?)
    """
    drift_insert = """
        INSERT INTO archetype_drift_limits (archetype_id, group_name, materials_json, basis, minimum, maximum, detail)
        VALUES (?,?,?,?,?,?,?)
    """
    oav_insert = """
        INSERT INTO archetype_oav_targets (archetype_id, time_window, odor_family, target_oav)
        VALUES (?,?,?,?)
    """
    repair_insert = """
        INSERT INTO archetype_repair_pool (archetype_id, material_name, dose)
        VALUES (?,?,?)
    """

    for spec in ARCHETYPES.values():
        # Access ArchetypeSpec fields
        key = spec.key if hasattr(spec, "key") else getattr(spec, "_key", str(spec))
        family = getattr(spec, "family", "")
        label = getattr(spec, "label", "")
        role = getattr(spec, "role", "")
        forbidden_materials = getattr(spec, "forbidden_materials", ())
        forbidden_tokens = getattr(spec, "forbidden_tokens", ())
        novelty_reference = getattr(spec, "novelty_reference", "")
        novelty_message = getattr(spec, "novelty_message", "")

        conn.execute(
            arch_insert,
            (
                key,
                family,
                label,
                role,
                json.dumps(list(forbidden_materials)) if forbidden_materials else None,
                json.dumps(list(forbidden_tokens)) if forbidden_tokens else None,
                novelty_reference,
                novelty_message,
            ),
        )
        aid = conn.execute("SELECT id FROM family_archetypes WHERE key = ?", (key,)).fetchone()[0]
        key_to_id[key] = aid

        # Anchors
        anchors = getattr(spec, "anchors", ())
        for grp in anchors:
            conn.execute(
                anchor_insert,
                (
                    aid,
                    getattr(grp, "name", ""),
                    json.dumps(list(getattr(grp, "materials", ()))),
                    getattr(grp, "basis", "active"),
                    getattr(grp, "minimum", None),
                    getattr(grp, "maximum", None),
                    getattr(grp, "detail", ""),
                ),
            )

        # Drift limits
        drift_limits = getattr(spec, "drift_limits", ())
        for grp in drift_limits:
            conn.execute(
                drift_insert,
                (
                    aid,
                    getattr(grp, "name", ""),
                    json.dumps(list(getattr(grp, "materials", ()))),
                    getattr(grp, "basis", "active"),
                    getattr(grp, "minimum", None),
                    getattr(grp, "maximum", None),
                    getattr(grp, "detail", ""),
                ),
            )

        # OAV targets
        oav_targets = getattr(spec, "oav_targets", {})
        if isinstance(oav_targets, dict):
            for time_window, odor_map in oav_targets.items():
                if isinstance(odor_map, dict):
                    for odor_family, target_oav in odor_map.items():
                        conn.execute(
                            oav_insert,
                            (aid, time_window, odor_family, float(target_oav)),
                        )

        # Repair pool
        repair_pool = getattr(spec, "repair_pool", {})
        if isinstance(repair_pool, dict):
            for mat_name, dose_val in repair_pool.items():
                conn.execute(
                    repair_insert,
                    (aid, mat_name, float(dose_val) if dose_val is not None else None),
                )

    conn.commit()
    return key_to_id


def _populate_pyramid(conn: sqlite3.Connection) -> None:
    """Insert pyramid_ratios, oav_targets, material_role_ratios, cross_family_compatibility."""
    from engine.knowledge.pyramid_targets import (  # noqa: PLC0415
        CROSS_FAMILY_COMPATIBILITY,
        MATERIAL_ROLE_RATIOS,
        OAV_TARGETS_BY_FAMILY,
        PYRAMID_RATIOS,
    )

    pyr_sql = """
        INSERT INTO pyramid_ratios (family_key, bracket, top_pct, heart_pct, base_pct, description)
        VALUES (?,?,?,?,?,?)
    """
    for family_key, bracket_map in PYRAMID_RATIOS.items():
        if hasattr(bracket_map, "items"):
            for bracket, ratio in bracket_map.items():
                conn.execute(
                    pyr_sql,
                    (
                        family_key,
                        str(bracket),
                        getattr(ratio, "top", getattr(ratio, "top_pct", 0)),
                        getattr(ratio, "heart", getattr(ratio, "heart_pct", 0)),
                        getattr(ratio, "base", getattr(ratio, "base_pct", 0)),
                        getattr(ratio, "description", ""),
                    ),
                )
        elif isinstance(bracket_map, (list, tuple)):
            for bracket_data in bracket_map:
                if isinstance(bracket_data, dict):
                    conn.execute(
                        pyr_sql,
                        (
                            family_key,
                            bracket_data.get("bracket", "universal"),
                            bracket_data.get("top_pct", bracket_data.get("top", 0)),
                            bracket_data.get("heart_pct", bracket_data.get("heart", 0)),
                            bracket_data.get("base_pct", bracket_data.get("base", 0)),
                            bracket_data.get("description", ""),
                        ),
                    )

    oav_sql = """
        INSERT INTO oav_targets (family_key, time_window, odor_family, target_oav)
        VALUES (?,?,?,?)
    """
    for family_key, time_data in OAV_TARGETS_BY_FAMILY.items():
        if isinstance(time_data, dict):
            for time_window, odor_map in time_data.items():
                if isinstance(odor_map, dict):
                    for odor_family, target_oav in odor_map.items():
                        conn.execute(
                            oav_sql,
                            (family_key, time_window, odor_family, float(target_oav)),
                        )

    role_sql = """
        INSERT INTO material_role_ratios (style, role, min_pct, max_pct)
        VALUES (?,?,?,?)
    """
    # MATERIAL_ROLE_RATIOS: dict[str, dict[str, tuple[float, float]]]
    if isinstance(MATERIAL_ROLE_RATIOS, dict):
        for style, roles in MATERIAL_ROLE_RATIOS.items():
            if isinstance(roles, dict):
                for role_name, (lo, hi) in roles.items():
                    conn.execute(
                        role_sql,
                        (style, role_name, float(lo), float(hi)),
                    )

    compat_sql = """
        INSERT INTO cross_family_compatibility (family_a, family_b, compatibility_level)
        VALUES (?,?,?)
    """
    # CROSS_FAMILY_COMPATIBILITY: dict[tuple[str, str], str]
    if isinstance(CROSS_FAMILY_COMPATIBILITY, dict):
        for (fam_a, fam_b), level in CROSS_FAMILY_COMPATIBILITY.items():
            conn.execute(
                compat_sql,
                (str(fam_a), str(fam_b), str(level)),
            )

    conn.commit()


def _populate_tokens(conn: sqlite3.Connection) -> None:
    """Insert family_tokens and note_tokens."""
    from engine.knowledge.perfume_knowledge import (  # noqa: PLC0415
        _FAMILY_TOKEN_MAP,
        _default_note_map,
    )

    # ── Family tokens (dict[str, str]) ──
    ft_sql = "INSERT INTO family_tokens (token, family_key) VALUES (?,?)"
    for token, family_key in _FAMILY_TOKEN_MAP.items():
        conn.execute(ft_sql, (token.lower(), family_key))

    # ── Note tokens ──
    note_map = _default_note_map()
    nt_sql = "INSERT INTO note_tokens (token, note_tier) VALUES (?,?)"
    for token in note_map.top_tokens:
        conn.execute(nt_sql, (token, "top"))
    for token in note_map.heart_tokens:
        conn.execute(nt_sql, (token, "heart"))
    for token in note_map.base_tokens:
        conn.execute(nt_sql, (token, "base"))

    conn.commit()


def _populate_safety(conn: sqlite3.Connection) -> None:
    """Insert ifra_limits, eu_allergens, sensitization, banned_materials."""
    from engine.ifra_safety import (  # noqa: PLC0415
        BANNED_MATERIALS,
        EU_FRAGRANCE_ALLERGENS,
        SENSITIZATION_DATA,
    )

    table = load_ifra_table()

    # IFRA limits: restricted materials of the sourced Cat 4 table, one row per
    # canonical name and alias as written. The ifra_limits schema has no status
    # column, so specification and no-standard materials get no row.
    ifra_sql = "INSERT OR IGNORE INTO ifra_limits (material_name, cat4_limit_pct) VALUES (?,?)"
    for name, limit in table.cat4_limits().items():
        conn.execute(ifra_sql, (name, float(limit)))

    # EU allergens (dict[str, dict])
    eu_sql = """
        INSERT INTO eu_allergens (material_name, cas, leave_on_threshold_pct, rinse_off_threshold_pct, risk, note)
        VALUES (?,?,?,?,?,?)
    """
    for name, entry in EU_FRAGRANCE_ALLERGENS.items():
        if isinstance(entry, dict):
            conn.execute(
                eu_sql,
                (
                    name,
                    entry.get("cas", ""),
                    entry.get("leave_on_threshold_pct", 0.001),
                    entry.get("rinse_off_threshold_pct", 0.01),
                    entry.get("risk", ""),
                    entry.get("note", ""),
                ),
            )
        elif isinstance(entry, str):
            # Legacy format: entry is just CAS or description
            conn.execute(eu_sql, (name, "", 0.001, 0.01, "", ""))

    # Sensitization (dict[str, dict])
    sens_sql = "INSERT INTO sensitization (material_name, ec3, potency, source) VALUES (?,?,?,?)"
    for name, entry in SENSITIZATION_DATA.items():
        if isinstance(entry, dict):
            conn.execute(
                sens_sql,
                (
                    name,
                    entry.get("ec3", 0),
                    entry.get("potency", ""),
                    entry.get("source", ""),
                ),
            )

    # Banned materials: IFRA prohibitions from the sourced table first (with
    # their standard as the reason), then the legacy banned list.
    ban_sql = "INSERT OR IGNORE INTO banned_materials (material_name, reason) VALUES (?,?)"
    for material in table.materials.values():
        if material.status == "prohibited":
            reason = f"IFRA 51st Amendment prohibition (standard {material.standard})"
            for name in (material.name, *material.aliases):
                conn.execute(ban_sql, (name, reason))
    if isinstance(BANNED_MATERIALS, dict):
        for name, reason in BANNED_MATERIALS.items():
            conn.execute(ban_sql, (name, str(reason)))
    elif hasattr(BANNED_MATERIALS, "__iter__"):
        for item in BANNED_MATERIALS:
            if isinstance(item, str):
                conn.execute(ban_sql, (item, ""))
            elif isinstance(item, dict):
                conn.execute(ban_sql, (item.get("name", ""), item.get("reason", "")))

    conn.commit()


def _populate_dose_response(conn: sqlite3.Connection) -> None:
    """Insert character_shifts and hill_params."""
    from engine.dose_response import (  # noqa: PLC0415
        CHARACTER_SHIFT_DATA,
        HILL_PARAMS,
    )

    # Character shifts
    cs_sql = "INSERT INTO character_shifts (material_name, max_conc_pct, character, quality) VALUES (?,?,?,?)"
    for mat_name, zones in CHARACTER_SHIFT_DATA.items():
        if hasattr(zones, "__iter__"):
            for zone in zones:
                if hasattr(zone, "max_conc_pct"):
                    conn.execute(
                        cs_sql,
                        (
                            mat_name,
                            getattr(zone, "max_conc_pct", None),
                            getattr(zone, "character", ""),
                            getattr(zone, "quality", ""),
                        ),
                    )
                elif isinstance(zone, dict):
                    conn.execute(
                        cs_sql,
                        (
                            mat_name,
                            zone.get("max_conc_pct", zone.get("max_conc")),
                            zone.get("character", ""),
                            zone.get("quality", ""),
                        ),
                    )

    # Hill params
    hp_sql = "INSERT INTO hill_params (material_name, ec50, n, rmax) VALUES (?,?,?,?)"
    for mat_name, params in HILL_PARAMS.items():
        if isinstance(params, dict):
            conn.execute(
                hp_sql,
                (
                    mat_name,
                    params.get("ec50", params.get("ec_50")),
                    params.get("n", params.get("hill_n")),
                    params.get("rmax", params.get("hill_rmax")),
                ),
            )
        elif hasattr(params, "ec50"):
            conn.execute(
                hp_sql,
                (
                    mat_name,
                    getattr(params, "ec50", None),
                    getattr(params, "n", None),
                    getattr(params, "rmax", None),
                ),
            )

    conn.commit()


def _populate_gate_data(conn: sqlite3.Connection) -> None:
    """Insert olfactory_fatigue, jellinek_classes, adaptation_tiers, iconic_skeletons."""
    from engine.pipeline.gates import (  # noqa: PLC0415
        _ADAPTATION_TIERS,
        _JELLINEK_CLASSES,
        _OLFACTORY_FATIGUE_THRESHOLDS,
        _SKELETONS,
    )

    # Olfactory fatigue
    of_sql = "INSERT INTO olfactory_fatigue (material_name, warn_oav, fail_oav) VALUES (?,?,?)"
    for mat_name, thresholds in _OLFACTORY_FATIGUE_THRESHOLDS.items():
        if isinstance(thresholds, (list, tuple)) and len(thresholds) >= 2:
            conn.execute(of_sql, (mat_name, float(thresholds[0]), float(thresholds[1])))
        elif isinstance(thresholds, dict):
            conn.execute(
                of_sql,
                (
                    mat_name,
                    thresholds.get("warn_oav", thresholds.get("warn")),
                    thresholds.get("fail_oav", thresholds.get("fail")),
                ),
            )

    # Jellinek classes
    jc_sql = "INSERT INTO jellinek_classes (material_name, class) VALUES (?,?)"
    for mat_name, cls in _JELLINEK_CLASSES.items():
        conn.execute(jc_sql, (mat_name, str(cls)))

    # Adaptation tiers
    at_sql = "INSERT INTO adaptation_tiers (tier, materials_json) VALUES (?,?)"
    for tier_name, materials_set in _ADAPTATION_TIERS.items():
        materials_list = list(materials_set) if hasattr(materials_set, "__iter__") else []
        conn.execute(at_sql, (tier_name, json.dumps(materials_list)))

    # Iconic skeletons
    sk_sql = "INSERT INTO iconic_skeletons (family, marker_materials_json, source_reference) VALUES (?,?,?)"
    for family_name, skeleton in _SKELETONS.items():
        if isinstance(skeleton, (list, tuple)):
            marker_materials = skeleton[1] if len(skeleton) > 1 else skeleton[0]
            source_ref = skeleton[3] if len(skeleton) > 3 else ""
            conn.execute(
                sk_sql,
                (
                    family_name,
                    json.dumps(marker_materials)
                    if isinstance(marker_materials, dict)
                    else str(marker_materials),
                    source_ref,
                ),
            )

    conn.commit()


def _populate_knowledge_graph(conn: sqlite3.Connection) -> None:
    """Insert theory_rules, accords, ingredient_catalog."""
    # Theory rules
    theory = _load_json_dict("data/knowledge_graph/theory_rules.json")
    tr_sql = "INSERT INTO theory_rules (category, key, value_json) VALUES (?,?,?)"
    for category, data in theory.items():
        if isinstance(data, dict):
            for key, value in data.items():
                conn.execute(
                    tr_sql,
                    (
                        category,
                        key,
                        json.dumps(value) if not isinstance(value, str) else value,
                    ),
                )
        elif isinstance(data, list):
            for item in data:
                conn.execute(
                    tr_sql,
                    (
                        category,
                        "",
                        json.dumps(item) if not isinstance(item, str) else item,
                    ),
                )

    # Accords
    accords = _load_json_dict("data/knowledge_graph/accords.json")
    ac_sql = "INSERT INTO accords (type, key, value_json) VALUES (?,?,?)"
    for accord_type, data in accords.items():
        if isinstance(data, dict):
            for key, value in data.items():
                conn.execute(
                    ac_sql,
                    (
                        accord_type,
                        key,
                        json.dumps(value) if not isinstance(value, str) else value,
                    ),
                )
        else:
            conn.execute(
                ac_sql,
                (
                    accord_type,
                    "",
                    json.dumps(data) if not isinstance(data, str) else data,
                ),
            )

    # Ingredient catalog
    catalog = _load_json_dict("data/knowledge_graph/ingredient_catalog.json")
    ic_sql = """
        INSERT INTO ingredient_catalog (name, identity_key, category, status, owned, notes_json)
        VALUES (?,?,?,?,?,?)
    """
    ingredients = catalog.get("ingredients", []) if isinstance(catalog, dict) else catalog
    if isinstance(ingredients, list):
        for entry in ingredients:
            if isinstance(entry, dict):
                conn.execute(
                    ic_sql,
                    (
                        entry.get("name", ""),
                        entry.get("identity_key", entry.get("key", "")),
                        entry.get("category", ""),
                        entry.get("status", ""),
                        1 if entry.get("owned") else 0,
                        json.dumps(entry.get("notes", entry.get("meta", {}))),
                    ),
                )

    conn.commit()


# ── Public entry point ───────────────────────────────────────────────


def migrate(db_path: str = "data/perfumery_kb.db") -> str:
    """Create and populate the perfumery knowledge SQLite database.

    Returns the absolute path of the database.
    """
    abs_path = os.path.abspath(db_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    # Drop old DB for clean migration
    if os.path.exists(abs_path):
        os.remove(abs_path)

    create_database(abs_path)
    conn = sqlite3.connect(abs_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=OFF")  # bulk insert

    try:
        # Materials (must be first — other tables FK-reference it)
        name_to_id = _populate_materials(conn)

        # Material secondary tables
        _populate_aliases(conn, name_to_id)
        _populate_natural_decomposition(conn, name_to_id)
        _populate_audit_flags(conn)

        # Interactions
        _populate_interactions(conn)

        # Rules
        _populate_archetypes(conn)
        _populate_pyramid(conn)
        _populate_tokens(conn)

        # Safety
        _populate_safety(conn)

        # Dose response
        _populate_dose_response(conn)

        # Gate embedded
        _populate_gate_data(conn)

        # Knowledge graph
        _populate_knowledge_graph(conn)

    finally:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.close()

    return abs_path
