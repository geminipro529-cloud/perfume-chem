from __future__ import annotations

import math
from decimal import Decimal
from typing import Any, Iterable

from consultant_core import as_decimal, parent_identity, sha256_json


def _dstr(value: Decimal) -> str:
    s = format(value.normalize(), "f")
    return "0" if s in {"", "-0"} else s


def _row_material(row: dict[str, Any]) -> str:
    return str(
        row.get("material")
        or row.get("canonical_material")
        or row.get("build_material")
        or row.get("target_identity")
        or ""
    ).strip()


def _row_parts(row: dict[str, Any]) -> Decimal:
    for key in ("parts_per_1000", "current_parts_per_1000", "active_parts_per_1000"):
        if row.get(key) not in (None, ""):
            return as_decimal(row[key], key)
    return Decimal("0")


def _is_technical(row: dict[str, Any], material: str) -> bool:
    if bool(row.get("technical")):
        return True
    text = " ".join(
        str(row.get(k) or "") for k in ("sensory_system", "system", "primary_function", "module")
    ).casefold()
    return material.casefold() in {"dpg", "dep", "tec", "ipm", "ethanol", "etoh", "water"} or "technical" in text


def build_formula_signature(formula: dict[str, Any]) -> dict[str, Any]:
    rows = list(formula.get("rows") or formula.get("formula_rows") or [])
    supplied: dict[str, Decimal] = {}
    exact_stock: dict[str, Decimal] = {}
    active: dict[str, Decimal] = {}
    systems: set[str] = set()
    phases: set[str] = set()
    technical_parts = Decimal("0")
    unknown_active_rows: list[str] = []
    product_basis_rows: list[str] = []
    nontechnical_count = 0

    for index, row in enumerate(rows, start=1):
        material = _row_material(row)
        parts = _row_parts(row)
        if parts < 0:
            raise ValueError(f"row {index}: parts cannot be negative")
        if _is_technical(row, material):
            technical_parts += parts
            continue
        nontechnical_count += 1
        parent = parent_identity(material, row.get("parent_identity")) or f"unresolved-row-{index}"
        exact = material.casefold() or f"unresolved-row-{index}"
        supplied[parent] = supplied.get(parent, Decimal("0")) + parts
        exact_stock[exact] = exact_stock.get(exact, Decimal("0")) + parts

        system = str(row.get("sensory_system") or row.get("system") or row.get("module") or "").strip().casefold()
        if system:
            systems.add(system)
        raw_phases = row.get("phase_roles") or row.get("phase") or []
        if isinstance(raw_phases, str):
            raw_phases = [raw_phases]
        phases.update(str(x).strip().casefold() for x in raw_phases if str(x).strip())

        if bool(row.get("product_basis")):
            product_basis_rows.append(str(row.get("row_id") or material or index))
            continue
        fraction = row.get("active_fraction")
        if fraction in (None, ""):
            unknown_active_rows.append(str(row.get("row_id") or material or index))
            continue
        f = as_decimal(fraction, "active_fraction")
        if f < 0 or f > 1:
            raise ValueError(f"row {index}: active_fraction must be between 0 and 1")
        active[parent] = active.get(parent, Decimal("0")) + parts * f

    if unknown_active_rows:
        coverage = "PARTIAL_UNKNOWN_ACTIVE_FRACTIONS"
    elif product_basis_rows:
        coverage = "COMPLETE_FOR_KNOWN_ACTIVE_ROWS__PRODUCT_BASIS_ABSTAINS"
    else:
        coverage = "COMPLETE_FOR_NONTECHNICAL_ROWS"

    signature = {
        "formula_id": formula.get("formula_id"),
        "formula_version": formula.get("formula_version") or formula.get("version"),
        "formula_hash": formula.get("formula_hash") or sha256_json(formula),
        "row_count": len(rows),
        "nontechnical_row_count": nontechnical_count,
        "technical_parts": _dstr(technical_parts),
        "supplied_stock_vector": {k: _dstr(v) for k, v in sorted(supplied.items())},
        "exact_stock_vector": {k: _dstr(v) for k, v in sorted(exact_stock.items())},
        "known_active_vector": {k: _dstr(v) for k, v in sorted(active.items())},
        "known_active_coverage_state": coverage,
        "unknown_active_rows": unknown_active_rows,
        "product_basis_rows": product_basis_rows,
        "sensory_systems": sorted(systems),
        "phase_roles": sorted(phases),
        "boundary": "Formula-space distance is diagnostic. It cannot establish sensory equivalence, liking, or similarity.",
    }
    signature["signature_hash"] = sha256_json(signature)
    return signature


def _decimal_vector(mapping: dict[str, Any], keys: Iterable[str]) -> list[float]:
    return [float(as_decimal(mapping.get(k, "0"))) for k in keys]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _js_distance(a: list[float], b: list[float]) -> float:
    sa, sb = sum(a), sum(b)
    if sa <= 0 or sb <= 0:
        return 1.0 if sa != sb else 0.0
    p = [x / sa for x in a]
    q = [x / sb for x in b]
    m = [(x + y) / 2 for x, y in zip(p, q)]

    def kl(x: list[float], y: list[float]) -> float:
        return sum(xi * math.log(xi / yi, 2) for xi, yi in zip(x, y) if xi > 0 and yi > 0)

    return math.sqrt(max(0.0, (kl(p, m) + kl(q, m)) / 2))


def compare_signatures(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    av = a.get("supplied_stock_vector") or {}
    bv = b.get("supplied_stock_vector") or {}
    keys = sorted(set(av) | set(bv))
    va, vb = _decimal_vector(av, keys), _decimal_vector(bv, keys)
    aset, bset = set(av), set(bv)
    intersection = aset & bset
    union = aset | bset
    jaccard = len(intersection) / len(union) if union else 1.0
    smaller_overlap = len(intersection) / min(len(aset), len(bset)) if aset and bset else 0.0
    cosine = _cosine(va, vb)
    js = _js_distance(va, vb)

    aa = a.get("known_active_vector") or {}
    ba = b.get("known_active_vector") or {}
    akeys = sorted(set(aa) | set(ba))
    active_cosine = _cosine(_decimal_vector(aa, akeys), _decimal_vector(ba, akeys)) if akeys else None

    system_a, system_b = set(a.get("sensory_systems") or []), set(b.get("sensory_systems") or [])
    system_jaccard = len(system_a & system_b) / len(system_a | system_b) if system_a | system_b else 1.0
    phase_a, phase_b = set(a.get("phase_roles") or []), set(b.get("phase_roles") or [])
    phase_jaccard = len(phase_a & phase_b) / len(phase_a | phase_b) if phase_a | phase_b else 1.0

    if cosine >= 0.97 or smaller_overlap >= 0.95:
        alert = "VERY_HIGH"
    elif cosine >= 0.93 or smaller_overlap >= 0.85:
        alert = "HIGH"
    elif cosine >= 0.80 or jaccard >= 0.60:
        alert = "MODERATE"
    else:
        alert = "LOW"

    result = {
        "formula_a": a.get("formula_id"),
        "formula_b": b.get("formula_id"),
        "shared_materials": sorted(intersection),
        "material_jaccard": round(jaccard, 9),
        "overlap_of_smaller": round(smaller_overlap, 9),
        "supplied_stock_cosine": round(cosine, 9),
        "supplied_stock_js_distance": round(js, 9),
        "known_active_cosine": None if active_cosine is None else round(active_cosine, 9),
        "system_jaccard": round(system_jaccard, 9),
        "phase_jaccard": round(phase_jaccard, 9),
        "structural_alert": alert,
        "sensory_equivalence": "NOT ESTABLISHED",
        "physical_anti_collapse_required": alert in {"HIGH", "VERY_HIGH"},
        "boundary": "No universal cosine or Jensen-Shannon threshold establishes perceptual sameness.",
    }
    result["comparison_hash"] = sha256_json(result)
    return result


def portfolio_report(signatures: list[dict[str, Any]]) -> dict[str, Any]:
    if not signatures:
        result = {
            "formula_count": 0,
            "common_materials": [],
            "pairwise": [],
            "state": "EMPTY",
            "sensory_equivalence": "NOT ESTABLISHED",
        }
        result["report_hash"] = sha256_json(result)
        return result

    material_sets = [set(s.get("supplied_stock_vector") or {}) for s in signatures]
    common = set.intersection(*material_sets) if material_sets else set()
    union = set.union(*material_sets) if material_sets else set()
    pairwise = [compare_signatures(signatures[i], signatures[j]) for i in range(len(signatures)) for j in range(i + 1, len(signatures))]
    common_mass: dict[str, str] = {}
    for s in signatures:
        vector = s.get("supplied_stock_vector") or {}
        total = sum(as_decimal(v) for v in vector.values())
        cmass = sum(as_decimal(vector[m]) for m in common)
        common_mass[str(s.get("formula_id"))] = _dstr(cmass / total if total else Decimal("0"))

    alerts = [p["structural_alert"] for p in pairwise]
    result = {
        "formula_count": len(signatures),
        "formula_ids": [s.get("formula_id") for s in signatures],
        "material_union_count": len(union),
        "common_material_count": len(common),
        "common_materials": sorted(common),
        "common_core_fraction_by_formula": common_mass,
        "pairwise": pairwise,
        "portfolio_alert": "VERY_HIGH" if "VERY_HIGH" in alerts else "HIGH" if "HIGH" in alerts else "MODERATE" if "MODERATE" in alerts else "LOW",
        "sensory_equivalence": "NOT ESTABLISHED",
        "state": "DIAGNOSTIC_ONLY",
    }
    result["report_hash"] = sha256_json(result)
    return result
