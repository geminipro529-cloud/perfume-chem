"""Crowd pleasantness prior: one -1..+1 table built from a panel and hand values.

This is a heuristic prior ("crowd guess"), not a measurement of any formula or
of Kenny's taste. It never uses OAV and says nothing about intensity. Panel
values come from Keller & Vosshall (2016) single molecules in paraffin oil;
hand values come from the legacy tables in ``engine.hedonic_model`` and
``engine.ingredient_intelligence``. A hand value of exactly zero means the
legacy code had no opinion, so it is treated as unknown, never as neutral.

``build_crowd_table`` derives the committed JSON from a local copy of the
Keller stimulus aggregates; ``crowd_pleasantness`` reads that JSON.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from engine.inventory_parser import _identity_name

ROOT = Path(__file__).resolve().parents[2]
TABLE_PATH = ROOT / "data/formulation_knowledge/pleasantness_crowd_v1.json"
MATERIALS_DIR = ROOT / "data/materials"
GENERATOR_PATH = ROOT / "_generate_material_properties.py"

SCHEMA = "pleasantness_crowd_v1"
SCALE = (
    "-1 (most unpleasant) .. 0 (neutral) .. +1 (most pleasant); panel values are "
    "(mean - 50) / 50 of the Keller 0-100 rating with 50 = neutral"
)
LABEL = (
    "crowd guess: panel averages and hand estimates, not a measurement of this "
    "formula or of Kenny's taste"
)
CITATION = (
    "Keller A, Vosshall LB (2016) Olfactory perception of chemically diverse "
    "molecules. BMC Neuroscience. doi:10.1186/s12868-016-0287-2 (CC BY 4.0), via "
    "pyrfume-data keller_2016, retrieved 2026-10-09"
)
WEAK_SHARE = 0.10
STRONG_SHARE = 0.25
FLIP_STRONG_CEILING = -0.4
# Name fragments of materials pleasant in traces but unpleasant when strong.
FLIP_TOKENS = (
    "indole", "skatole", "cade", "birch tar", "isobutyl quinoline", "ibq",
    "castoreum", "civet", "hyraceum", "costus",
)
HAND_SOURCES = ("hedonic_model_table", "profile_override", "profile_direct")
# Raw scale of each hand source as stated in, and checked against, the code.
RAW_SCALES = {
    "hedonic_model_table": ("-1..+1", 1.0),
    "profile_override": ("-5..+5", 5.0),
    "profile_direct": ("-1..+1", 1.0),
    "character_heuristic": ("-5..+5 field, clamped +-3", 5.0),
}
MIN_CALIBRATION_N = 15
MIN_CALIBRATION_R = 0.3
_CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


@dataclass(frozen=True)
class CrowdValue:
    material: str
    value: float
    source: str
    confidence: str
    dose_dependent: bool
    family: str | None


def _name_key(name: str) -> str:
    """Casefold with hyphens and runs of spaces treated alike ("beta-Ionone" = "Beta Ionone")."""
    return re.sub(r"[\s\-]+", " ", name.casefold()).strip()


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _keller_groups(rows: list[dict]) -> dict[str, list[dict]]:
    """Group stimulus rows by molecule; four rows carry their CAS in ``cid``."""
    groups: dict[str, list[dict]] = {}
    for row in rows:
        cas = (row.get("cas") or "").strip()
        if not cas and _CAS_RE.match(str(row.get("cid") or "").strip()):
            cas = str(row["cid"]).strip()
        key = cas or f"cid:{row.get('cid')}"
        groups.setdefault(key, []).append(dict(row, cas=cas or None))
    return groups


def _keller_record(rows: list[dict], match_by: str) -> dict:
    ordered = sorted(rows, key=lambda r: float(r["concentration"]))
    weak_row, strong_row = ordered[0], ordered[-1]

    def point(row: dict) -> dict:
        return {
            "concentration": row["concentration"],
            "ratio": row.get("ratio"),
            "solvent": row.get("solvent"),
            "pleasantness_mean_0_100": row["pleasantness_mean_0_100"],
            "intensity_mean_0_100": row.get("intensity_mean_0_100"),
            "n_pleasant": row.get("n_pleasant"),
            "value": round((float(row["pleasantness_mean_0_100"]) - 50.0) / 50.0, 4),
        }

    return {
        "name": next((r.get("name") for r in rows if r.get("name")), None),
        "cas": next((r.get("cas") for r in rows if r.get("cas")), None),
        "match_by": match_by,
        "weak": point(weak_row),
        "strong": point(strong_row),
    }


def _parse_cas_map(path: Path) -> dict[str, str]:
    """Read CAS_MAP from the generator's text; that module is not import-safe."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        target = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target, value = node.target.id, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target, value = node.targets[0].id, node.value
        if target == "CAS_MAP" and value is not None:
            return {str(k).casefold(): str(v) for k, v in ast.literal_eval(value).items()}
    return {}


def _yaml_records(directory: Path) -> dict[str, dict]:
    import yaml

    records: dict[str, dict] = {}
    for path in sorted(directory.glob("*.yaml")):
        for item in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            if isinstance(item, dict) and item.get("canonical_name"):
                records.setdefault(str(item["canonical_name"]).casefold(), item)
    return records


def _fit(pairs: list[tuple[float, float]]) -> dict:
    """Least squares panel = a + b * hand, with Pearson r."""
    n = len(pairs)
    if n < 3:
        return {"n": n, "a": None, "b": None, "r": None}
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0 or syy == 0:
        return {"n": n, "a": None, "b": None, "r": None}
    b = sxy / sxx
    return {"n": n, "a": round(my - b * mx, 4), "b": round(b, 4), "r": round(sxy / math.sqrt(sxx * syy), 4)}


def _hand_values(name: str, profile: dict | None, valence: dict, overrides: dict) -> dict[str, float]:
    """Every non-zero hand value for one material, keyed by source, on its raw scale."""
    found: dict[str, float] = {}
    if name in valence:
        found["hedonic_model_table"] = float(valence[name])
    if profile is None:
        return found
    status = (profile.get("evidence") or {}).get("hedonic", {}).get("status")
    if status == "HEURISTIC_OVERRIDE" and overrides.get(name):
        found["profile_override"] = float(overrides[name])
    elif profile.get("hedonic") and status in (None, "DECLARED_UNVERIFIED"):
        found["profile_direct"] = float(profile["hedonic"])
    elif profile.get("hedonic") and status == "CHARACTER_DERIVED_HEURISTIC":
        found["character_heuristic"] = float(profile["hedonic"])
    return found


def build_crowd_table(keller_stimuli_path: str) -> dict:
    """Build the crowd table from the Keller 2016 stimulus aggregates (no writes)."""
    from engine import ingredient_intelligence as ii
    from engine.hedonic_model import HEDONIC_VALENCE

    raw = Path(keller_stimuli_path).read_bytes()
    rows = json.loads(raw)
    groups = _keller_groups(rows)
    by_cas = {key: grp for key, grp in groups.items() if _CAS_RE.match(key)}
    by_name: dict[str, list[dict]] = {}
    for grp in groups.values():
        for row in grp:
            if row.get("name"):
                by_name.setdefault(_name_key(str(row["name"])), grp)

    profiles = ii._PROFILES
    overrides = ii._HEDONIC_OVERRIDES
    yaml_records = _yaml_records(MATERIALS_DIR)
    cas_map = _parse_cas_map(GENERATOR_PATH)
    profile_by_fold = {k.casefold(): k for k in profiles}

    # Entry names: every profile, plus table names with no exact/casefold profile.
    names: dict[str, str | None] = {k: k for k in profiles}
    table_names: dict[str, str] = {}
    for name in HEDONIC_VALENCE:
        key = name if name in profiles else profile_by_fold.get(name.casefold())
        if key is None:
            names[name] = None
        else:
            table_names[key] = name

    drafts: dict[str, dict] = {}
    for name, profile_key in sorted(names.items(), key=lambda kv: kv[0].casefold()):
        profile = profiles.get(profile_key) if profile_key else None
        yaml_rec = yaml_records.get(name.casefold())
        aliases = sorted({str(a) for a in (yaml_rec or {}).get("aliases") or [] if str(a).strip() and str(a) != name})
        if name in table_names and table_names[name] != name:
            aliases = sorted(set(aliases) | {table_names[name]})
        family = None
        if profile is not None:
            family = profile.get("or_family") or profile.get("odor_family")
        family = family or ii._OR_FAMILY_OVERRIDES.get(name)

        cas_candidates = [c for c in (
            (yaml_rec or {}).get("cas"),
            (profile or {}).get("cas"),
            cas_map.get(name.casefold()),
        ) if c]
        keller = None
        for cas in cas_candidates:
            if str(cas).strip() in by_cas:
                keller = _keller_record(by_cas[str(cas).strip()], "cas")
                break
        if keller is None and _name_key(name) in by_name:
            keller = _keller_record(by_name[_name_key(name)], "name")

        hand_name = table_names.get(name, name)
        hand = _hand_values(name, profile, HEDONIC_VALENCE, overrides)
        if hand_name != name and hand_name in HEDONIC_VALENCE:
            hand["hedonic_model_table"] = float(HEDONIC_VALENCE[hand_name])
        drafts[name] = {"aliases": aliases, "family": family, "keller": keller, "hand": hand}

    # Calibration of hand values (sources 2-4) against panel values.
    def unit(source: str, raw_value: float) -> float:
        return raw_value / RAW_SCALES[source][1]

    per_source: dict[str, list[tuple[float, float]]] = {s: [] for s in (*HAND_SOURCES, "character_heuristic")}
    pooled: list[tuple[float, float]] = []
    for draft in drafts.values():
        if draft["keller"] is None:
            continue
        panel = (draft["keller"]["weak"]["value"] + draft["keller"]["strong"]["value"]) / 2
        for source, raw_value in draft["hand"].items():
            per_source[source].append((unit(source, raw_value), panel))
        first = next((s for s in HAND_SOURCES if s in draft["hand"]), None)
        if first is not None:
            pooled.append((unit(first, draft["hand"][first]), panel))
    pooled_fit = _fit(pooled)
    applied = (
        pooled_fit["n"] >= MIN_CALIBRATION_N
        and pooled_fit["r"] is not None
        and pooled_fit["r"] >= MIN_CALIBRATION_R
    )
    calibration = {
        "model": "panel = a + b * hand, least squares; hand on -1..+1 after raw-scale division",
        "pooled_rule": "one pair per material, using its highest-precedence hand source",
        "per_source": {s: _fit(p) for s, p in per_source.items()},
        "pooled": pooled_fit,
        "thresholds": {"min_n": MIN_CALIBRATION_N, "min_r": MIN_CALIBRATION_R},
        "applied": applied,
        "applied_to": ["hedonic_model_table", "profile_override", "profile_direct", "character_heuristic"] if applied else [],
        "note": (
            "pooled fit applied to every hand-derived value; character_heuristic is "
            "excluded from the fit but mapped with it so all values share one scale"
            if applied else
            f"not applied: pooled n={pooled_fit['n']} r={pooled_fit['r']} below thresholds; hand values stored unscaled"
        ),
    }

    materials: dict[str, dict] = {}
    for name, draft in drafts.items():
        entry: dict[str, Any] = {
            "value": None,
            "source": "unknown",
            "confidence": None,
            "aliases": draft["aliases"],
            "family": draft["family"],
            "dose_points": None,
            "dose_source": None,
        }
        keller = draft["keller"]
        if keller is not None:
            weak, strong = keller["weak"]["value"], keller["strong"]["value"]
            entry.update(
                value=round((weak + strong) / 2, 4),
                source="keller_vosshall_2016",
                confidence="panel",
                dose_points={"weak": weak, "strong": strong},
                dose_source="keller",
                keller=keller,
            )
        else:
            source = next((s for s in (*HAND_SOURCES, "character_heuristic") if s in draft["hand"]), None)
            if source is not None:
                raw_value = draft["hand"][source]
                scaled = unit(source, raw_value)
                if applied:
                    scaled = pooled_fit["a"] + pooled_fit["b"] * scaled
                entry.update(
                    value=round(_clamp(scaled), 4),
                    source=source,
                    confidence="low" if source == "character_heuristic" else "hand",
                    raw_value=raw_value,
                    raw_scale=RAW_SCALES[source][0],
                )
        if entry["value"] is not None and keller is None and any(t in name.casefold() for t in FLIP_TOKENS):
            entry["dose_points"] = {"weak": entry["value"], "strong": min(entry["value"], FLIP_STRONG_CEILING)}
            entry["dose_source"] = "heuristic_unmeasured"
        materials[name] = entry

    counts: dict[str, int] = {}
    for entry in materials.values():
        counts[entry["source"]] = counts.get(entry["source"], 0) + 1
    return {
        "schema": SCHEMA,
        "scale": SCALE,
        "label": LABEL,
        "source_citation": CITATION,
        "dose_rule": (
            f"strength_share <= {WEAK_SHARE} -> weak, >= {STRONG_SHARE} -> strong, linear between; "
            "heuristic_unmeasured flips set strong = min(value, -0.4)"
        ),
        "counts": dict(sorted(counts.items())),
        "calibration": calibration,
        "generated_by": {
            "function": "engine.formulation_intelligence.pleasantness_table.build_crowd_table",
            "keller_input_sha256": hashlib.sha256(raw).hexdigest(),
            "keller_rows": len(rows),
        },
        "materials": dict(sorted(materials.items(), key=lambda kv: kv[0].casefold())),
    }


@lru_cache(maxsize=1)
def load_crowd_table() -> dict:
    return json.loads(TABLE_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _name_index() -> dict[str, str]:
    materials = load_crowd_table()["materials"]
    index: dict[str, str] = {}
    ambiguous: set[str] = set()
    for name, entry in materials.items():
        for alias in entry.get("aliases") or []:
            key = _name_key(alias)
            if key in index and index[key] != name:
                ambiguous.add(key)
            index.setdefault(key, name)
    for key in ambiguous:
        index.pop(key, None)
    for name in materials:  # canonical names outrank aliases
        index[_name_key(name)] = name
    return index


def _resolve(name: str) -> str | None:
    materials = load_crowd_table()["materials"]
    index = _name_index()
    for candidate in (name.strip(), _identity_name(name.strip())):
        if candidate in materials:
            return candidate
        if _name_key(candidate) in index:
            return index[_name_key(candidate)]
    return None


def crowd_pleasantness(name: str, strength_share: float | None = None) -> CrowdValue | None:
    """Crowd prior for one material, or None when unknown. Not a measurement."""
    key = _resolve(name)
    if key is None:
        return None
    entry = load_crowd_table()["materials"][key]
    if entry["value"] is None:
        return None
    value = float(entry["value"])
    points = entry.get("dose_points")
    if strength_share is not None and points:
        weak, strong = float(points["weak"]), float(points["strong"])
        if strength_share <= WEAK_SHARE:
            value = weak
        elif strength_share >= STRONG_SHARE:
            value = strong
        else:
            t = (strength_share - WEAK_SHARE) / (STRONG_SHARE - WEAK_SHARE)
            value = weak + t * (strong - weak)
    return CrowdValue(
        material=key,
        value=value,
        source=entry["source"],
        confidence=entry["confidence"],
        dose_dependent=points is not None,
        family=entry.get("family"),
    )
