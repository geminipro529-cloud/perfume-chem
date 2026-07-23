"""Database initialization and JSON-to-SQLite migration.

Creates all tables and loads the existing flat JSON knowledge graph files
into the new database schema with provenance tracking.
"""

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Resolve paths before anything else
PROJECT_ROOT = Path(__file__).resolve().parent.parent
KG_DIR = PROJECT_ROOT / "data" / "knowledge_graph"

# Adjust sys.path so we can import backend modules
import sys

sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.models.base import Base

# Only import the models we're actually populating (avoid importing
# existing models that may have issues like reserved column names)
from app.models.knowledge_graph import (
    ConfidenceLevel,
    Material,
    PairingRule,
    RuleType,
    SynergyRule,
    TheoryFramework,
)

# Corruption detection patterns
CORRUPTION_PATTERNS = [
    re.compile(r"\.\w{2,4}[a-z]", re.IGNORECASE),
    re.compile(r"\.md"),
    re.compile(r"\.txt"),
]

DATABASE_URL = f"sqlite+aiosqlite:///{PROJECT_ROOT / 'perfume_chem.db'}"


def _load_json(name: str):
    path = KG_DIR / name
    if not path.exists():
        return [] if name != "theory_rules.json" else {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _is_corrupted(name: str) -> bool:
    """Check if a material name looks like it has filename fragments."""
    if not name:
        return True
    for pat in CORRUPTION_PATTERNS:
        if pat.search(name):
            return True
    return len(name) > 100


def _map_rule_type(raw: str | None) -> RuleType:
    if raw and "antag" in raw.lower():
        return RuleType.ANTAGONISM
    if raw and "neutral" in raw.lower():
        return RuleType.NEUTRAL
    return RuleType.SYNERGY


def _compute_completeness(mat_dict: dict) -> float:
    props = [
        "mw", "bp", "vp", "clp", "odt",
        "odor_family", "odor_profile",
        "sar_class", "olfactophore",
        "arctander_character", "arctander_tenacity",
        "carles_position", "jellinek_quadrant",
        "typical_pct_range", "best_with",
    ]
    filled = sum(1 for p in props if mat_dict.get(p) is not None)
    return round(filled / len(props) * 100, 1)


async def init_db():
    """Create all tables and load JSON data into the database."""
    engine = create_async_engine(DATABASE_URL, echo=False)

    # Rebuild the knowledge tables on every run so source-data edits propagate.
    # Preserve other tables such as formulation_outcomes.
    async with engine.begin() as conn:
        await conn.run_sync(PairingRule.__table__.drop, checkfirst=True)
        await conn.run_sync(SynergyRule.__table__.drop, checkfirst=True)
        await conn.run_sync(TheoryFramework.__table__.drop, checkfirst=True)
        await conn.run_sync(Material.__table__.drop, checkfirst=True)
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        async with session.begin():
            # ── Load materials ──────────────────────────────────────
            materials_raw = _load_json("material_properties.json")
            name_to_id: dict[str, int] = {}
            now = datetime.now(timezone.utc)

            print(f"Loading {len(materials_raw)} materials...")
            for m in materials_raw:
                mat = Material(
                    name=m["name"],
                    alt_name=m.get("alt_name"),
                    cas=m.get("cas"),
                    formula_str=m.get("formula_str"),
                    mw=m.get("mw"),
                    bp=m.get("bp"),
                    vp=m.get("vp"),
                    clp=m.get("clp"),
                    odt=m.get("odt"),
                    odor_family=m.get("odor_family"),
                    odor_profile=m.get("odor_profile"),
                    sar_class=m.get("sar_class"),
                    olfactophore=m.get("olfactophore"),
                    arctander_character=m.get("arctander_character"),
                    arctander_tenacity=m.get("arctander_tenacity"),
                    carles_position=m.get("carles_position"),
                    carles_pairing_rule=m.get("carles_pairing_rule"),
                    roudnitska_function=m.get("roudnitska_function"),
                    roudnitska_craft_note=m.get("roudnitska_craft_note"),
                    jellinek_axis=m.get("jellinek_axis"),
                    jellinek_quadrant=m.get("jellinek_quadrant"),
                    jellinek_effect=m.get("jellinek_effect"),
                    typical_pct_range=m.get("typical_pct_range"),
                    max_safe_pct=m.get("max_safe_pct"),
                    stock_form=m.get("stock_form"),
                    best_with=m.get("best_with"),
                    avoid=m.get("avoid"),
                    handle_as=m.get("handle_as"),
                    source="knowledge_graph_v1",
                    confidence=ConfidenceLevel.MEDIUM,
                    last_verified=now,
                    completeness_pct=_compute_completeness(m),
                )
                session.add(mat)

            # Flush to get IDs
            await session.flush()

            # Build name→id lookup
            from sqlalchemy import select
            result = await session.execute(select(Material.id, Material.name, Material.alt_name))
            for row in result:
                name_to_id[row.name.upper()] = row.id
                if row.alt_name:
                    name_to_id[row.alt_name.upper()] = row.id

            # ── Load pairing rules ──────────────────────────────────
            pairings_raw = _load_json("pairing_rules.json")
            print(f"Loading {len(pairings_raw)} pairing rules...")
            for p in pairings_raw:
                a_name = p.get("material_a", "")
                b_name = p.get("material_b", "")
                session.add(PairingRule(
                    material_a_id=name_to_id.get(a_name.upper()),
                    material_b_id=name_to_id.get(b_name.upper()),
                    material_a_name=a_name,
                    material_b_name=b_name,
                    effect=p.get("effect"),
                    rule_type=_map_rule_type(p.get("type")),
                    source=p.get("source"),
                    confidence=ConfidenceLevel.MEDIUM,
                    last_verified=now,
                ))

            # ── Load synergy rules (with corruption detection) ──────
            synergy_raw = _load_json("synergy_matrix.json")
            print(f"Loading {len(synergy_raw)} synergy rules...")
            corrupted_count = 0
            for s in synergy_raw:
                a_name = s.get("material_a", "")
                b_name = s.get("material_b", "")
                corrupted = _is_corrupted(a_name) or _is_corrupted(b_name)
                if corrupted:
                    corrupted_count += 1

                session.add(SynergyRule(
                    material_a_name=a_name,
                    material_b_name=b_name,
                    effect=s.get("effect"),
                    ratio=s.get("ratio"),
                    rule_type=_map_rule_type(s.get("type")),
                    source=s.get("source"),
                    confidence=ConfidenceLevel.LOW if corrupted else ConfidenceLevel.MEDIUM,
                    last_verified=now,
                    is_corrupted=corrupted,
                    corruption_notes="Auto-flagged: name contains filename fragment" if corrupted else None,
                ))
            if corrupted_count:
                print(f"  WARNING: {corrupted_count} corrupted synergy entries flagged")

            # ── Load theory frameworks ──────────────────────────────
            theory_raw = _load_json("theory_rules.json")
            print(f"Loading {len(theory_raw)} theory frameworks...")
            for name, data in theory_raw.items():
                session.add(TheoryFramework(
                    name=name,
                    description=data.get("description"),
                    principle=data.get("principle"),
                    rules_json=data,
                    source="knowledge_graph_v1",
                    confidence=ConfidenceLevel.HIGH,
                ))

        # Commit is automatic via context manager

    await engine.dispose()
    print("Database initialized and populated successfully")
    return True


if __name__ == "__main__":
    asyncio.run(init_db())
