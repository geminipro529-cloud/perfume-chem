r"""Build .opencode/library/perfume_kb.jsonl from existing structured data.

Sources:
  1. Perfumer's World parsed.json -> pw_sku_* entries
  2. inventory.txt -> local_inv_* entries + in_local_inventory flag
  3. engine.odor_thresholds.ODT_DATA -> odt_* entries
  4. engine.reference_contracts.REFERENCE_CONTRACTS -> ref_* entries
  5. engine.families.registry.ARCHETYPES -> fam_* entries

Stdlib only. No external deps beyond engine/ imports.
"""

import hashlib
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUTPUT = ROOT / ".opencode" / "library" / "perfume_kb.jsonl"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)


def slugify(s):
    return re.sub(r"[^a-z0-9_]", "_", s.lower().strip())[:80]


def sha8(s):
    return hashlib.sha256(s.encode()).hexdigest()[:8]


def emit_jsonl(entry: Mapping[str, object]):
    with open(OUTPUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_inventory():
    path = ROOT / "inventory.txt"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    result = {}
    current_category = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("---") and stripped.endswith("---"):
            current_category = stripped.strip("- ").strip()
            continue
        if not stripped.startswith("- "):
            continue
        material_line = stripped[2:].strip()
        dilution_pct = 1.0
        solvent = "neat"
        if "(" in material_line and "%" in material_line:
            match = re.search(r"\((\d+)%\s*(?:in\s+)?(\w+)?\)", material_line)
            if match:
                dilution_pct = int(match.group(1)) / 100.0
                solvent = match.group(2) or "unknown"
        name = re.sub(r"\s*\(\d+%[^)]*\)", "", material_line).strip()
        result[name.lower()] = {
            "name": name,
            "dilution": "neat"
            if dilution_pct >= 1.0
            else f"{int(dilution_pct * 100)}%{(' in ' + solvent) if solvent != 'unknown' else ''}",
            "dilution_pct": dilution_pct,
            "category": current_category,
            "in_stock": True,
        }
    return result


def main():
    if OUTPUT.exists():
        OUTPUT.unlink()

    inventory = load_inventory()
    pw_names_lower = set()

    # Phase 1: Perfumer's World
    pw_path = ROOT / "data" / "materials" / "_sources" / "perfumersworld_stock.parsed.json"
    if pw_path.exists():
        pw_data = json.loads(pw_path.read_text(encoding="utf-8"))
        for entry in pw_data:
            name = entry.get("base_name", "")
            name_lower = name.lower()
            pw_names_lower.add(name_lower)
            in_inv = name_lower in inventory or any(
                inv_name.lower() in name_lower or name_lower in inv_name.lower()
                for inv_name in inventory
            )

            price_total = None
            if entry.get("price_unit") == "gram":
                price_total = entry.get("price_usd")

            emit_jsonl(
                {
                    "id": f"pw_sku_{entry.get('sku', sha8(name))}",
                    "source": "perfumersworld",
                    "base_name": name,
                    "dilution_pct": entry.get("dilution_pct"),
                    "solvent": entry.get("dilution_solvent"),
                    "sku": entry.get("sku"),
                    "price_usd_per_gram": price_total,
                    "in_local_inventory": in_inv,
                }
            )

    # Phase 2: Local inventory
    for name_lower, inv in inventory.items():
        in_pw = name_lower in pw_names_lower
        emit_jsonl(
            {
                "id": f"local_inv_{slugify(inv['name'])}",
                "source": "inventory",
                "name": inv["name"],
                "dilution": inv["dilution"],
                "dilution_pct": inv["dilution_pct"],
                "category": inv["category"],
                "in_stock": inv["in_stock"],
                "in_perfumersworld": in_pw,
            }
        )

    # Phase 3: ODT data
    try:
        from engine.odor_thresholds import ODT_DATA

        for name, vals in ODT_DATA.items():
            if isinstance(vals, dict):
                emit_jsonl(
                    {
                        "id": f"odt_{slugify(name)}",
                        "source": "odor_thresholds",
                        "name": name,
                        **{k: v for k, v in vals.items() if k not in ("_note", "_source")},
                    }
                )
    except ImportError as e:
        print(f"  ODT import failed: {e}")

    # Phase 4: Reference contracts
    try:
        from engine.reference_contracts import REFERENCE_CONTRACTS

        for cid, contract in REFERENCE_CONTRACTS.items():
            ref_entry: dict[str, object] = {
                "id": f"ref_{cid}",
                "source": "reference_contracts",
                "contract_id": cid,
                "display_name": contract.display_name,
                "source_url": contract.source_url,
                "evidence_class": contract.evidence_class,
            }
            if getattr(contract, "marker_groups", None):
                ref_entry["marker_groups"] = [
                    {"name": mg.name, "alternatives": list(mg.alternatives)}
                    for mg in contract.marker_groups
                ]
            if getattr(contract, "target_aliases", None):
                ref_entry["target_aliases"] = list(contract.target_aliases)
            emit_jsonl(ref_entry)
    except ImportError as e:
        print(f"  reference_contracts import failed: {e}")

    # Phase 5: Family archetypes
    try:
        from engine.families.registry import ARCHETYPES

        for key, spec in ARCHETYPES.items():
            fam_entry: dict[str, object] = {
                "id": f"fam_{slugify(key)}",
                "source": "families_registry",
                "archetype": key,
            }
            for attr in (
                "family",
                "key",
                "label",
                "role",
                "novelty_reference",
                "forbidden_materials",
            ):
                val = getattr(spec, attr, None)
                if val is not None:
                    fam_entry[attr] = val if not isinstance(val, (list, tuple)) else list(val)

            for attr in ("anchors", "drift_limits"):
                val = getattr(spec, attr, None)
                if val:
                    fam_entry[attr] = [
                        {
                            "name": gr.name,
                            "materials": list(gr.materials),
                            "basis": getattr(gr, "basis", "active"),
                            "minimum": getattr(gr, "minimum", None),
                            "maximum": getattr(gr, "maximum", None),
                        }
                        for gr in val
                    ]

            for attr in ("repair_pool", "oav_targets"):
                val = getattr(spec, attr, None)
                if val is not None:
                    entry[attr] = val

            emit_jsonl(entry)
    except ImportError as e:
        print(f"  families_registry import failed: {e}")

    # Report
    line_count = sum(1 for _ in open(OUTPUT, encoding="utf-8"))
    size_kb = OUTPUT.stat().st_size / 1024
    print(f"Built {OUTPUT}")
    print(f"  {line_count} entries, {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
