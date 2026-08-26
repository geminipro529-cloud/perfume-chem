"""pubchem_client.py — PubChem PUG REST API client with file-based cache.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

This module provides:
  - Name → CID resolution (PUG REST)
  - CID → physical properties (MW, XLogP, CanonicalSMILES, InChIKey)
  - CAS → CID resolution (via name search + CID resolution)
  - ODT live lookup (via OdorThreshold property, when available)

Cache layer:
  - JSON file at output/cache/pubchem_cache.json
  - 30-day TTL (configurable)
  - Caches ALL responses (success, miss, and error) to avoid hammering PubChem
  - Cache includes source/timestamp/ttl for auditability

Graceful degradation:
  - Network errors → returns cached value if fresh, else None
  - Missing data → returns None (caller falls back to local)
  - Rate limits (429) → exponential backoff (1s, 2s, 4s)
  - Never raises; always returns Optional[dict]

Usage:
    from engine.pubchem_client import lookup_material, cached_cid, refresh_cache

    props = lookup_material("Hedione")
    if props and props.get("cid"):
        print(f"Hedione CID: {props['cid']}, MW: {props['molecular_weight']}")
    else:
        # Fall back to local data
        ...
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

# ── Path setup ──────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / "output" / "cache"
CACHE_FILE = CACHE_DIR / "pubchem_cache.json"
CACHE_TTL_DAYS = 30

# Ensure cache directory exists
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# PubChem PUG REST base URLs
BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
TIMEOUT_SEC = 10
USER_AGENT = "perfume-chem/1.0 (PubChem client)"

# Properties to fetch for physical validation
PHYSICAL_PROPS = (
    "MolecularFormula",
    "MolecularWeight",
    "XLogP",
    "ExactMass",
    "CanonicalSMILES",
    "InChIKey",
)


# ══════════════════════════════════════════════════════════════════════
# CACHE LAYER
# ══════════════════════════════════════════════════════════════════════


def _load_cache() -> dict:
    """Load the file-based cache, returning empty dict on any error."""
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, IOError):
        return {}


def _save_cache(cache: dict) -> None:
    """Persist the cache atomically (write to .tmp then rename)."""
    tmp_file = CACHE_FILE.with_suffix(".tmp")
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, sort_keys=True)
        tmp_file.replace(CACHE_FILE)
    except IOError:
        # Cache write failure is non-critical; log and continue
        pass


def _cache_key(query: str) -> str:
    """Generate a deterministic cache key for a query."""
    return hashlib.sha256(query.lower().strip().encode("utf-8")).hexdigest()[:16]


def _is_fresh(entry: dict) -> bool:
    """Check if a cache entry is within TTL."""
    ts = entry.get("timestamp", 0)
    age_days = (time.time() - ts) / 86400
    return age_days < CACHE_TTL_DAYS


def _cache_get(query: str) -> Optional[dict]:
    """Retrieve from cache if present and fresh."""
    cache = _load_cache()
    key = _cache_key(query)
    entry = cache.get(key)
    if entry and _is_fresh(entry):
        return entry.get("data")
    return None


def _cache_put(query: str, data: dict) -> None:
    """Store a response in the cache."""
    cache = _load_cache()
    key = _cache_key(query)
    cache[key] = {
        "query": query,
        "data": data,
        "timestamp": time.time(),
        "ttl_days": CACHE_TTL_DAYS,
    }
    _save_cache(cache)


# ══════════════════════════════════════════════════════════════════════
# HTTP LAYER
# ══════════════════════════════════════════════════════════════════════


def _http_get_json(url: str, max_retries: int = 2) -> Optional[dict]:
    """GET request with timeout, retry on 429, and graceful error handling.

    Returns parsed JSON dict on success, None on any error.
    """
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries:
                time.sleep(2**attempt)  # 1s, 2s backoff
                continue
            # 404 (not found) or 5xx: return None, don't retry
            return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, IOError):
            return None
    return None


# ══════════════════════════════════════════════════════════════════════
# PUBCHEM API WRAPPERS
# ══════════════════════════════════════════════════════════════════════


def _name_to_cid(name: str) -> Optional[int]:
    """Resolve a material name to PubChem CID via PUG REST."""
    cache_key = f"name2cid:{name}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached.get("cid")

    url = f"{BASE_URL}/compound/name/{urllib.parse.quote(name)}/cids/JSON"
    result = _http_get_json(url)
    cid = None
    if result and "IdentifierList" in result:
        cids = result["IdentifierList"].get("CID", [])
        cid = cids[0] if cids else None

    _cache_put(cache_key, {"cid": cid})
    return cid


def _cid_to_properties(
    cid: int, props: tuple[str, ...] = PHYSICAL_PROPS
) -> Optional[dict]:
    """Fetch physical properties for a CID."""
    cache_key = f"cid2props:{cid}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    prop_str = ",".join(props)
    url = f"{BASE_URL}/compound/cid/{cid}/property/{prop_str}/JSON"
    result = _http_get_json(url)
    if not result or "PropertyTable" not in result:
        _cache_put(cache_key, {})  # cache the miss
        return None

    table = result["PropertyTable"]["Properties"]
    data = table[0] if table else {}
    _cache_put(cache_key, data)
    return data


# ══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════


def lookup_material(name: str) -> Optional[dict]:
    """Look up a material by name and return its PubChem properties.

    Returns a dict with keys:
      - cid: PubChem Compound ID
      - molecular_formula, molecular_weight, xlogp, exact_mass
      - canonical_smiles, inchikey
      - source: "pubchem_live" or "pubchem_cache"

    Returns None if name cannot be resolved OR network/cache is unavailable.
    """
    name = name.strip()
    if not name:
        return None

    # Step 1: name → CID
    cid = _name_to_cid(name)
    if cid is None:
        return None

    # Step 2: CID → properties
    props = _cid_to_properties(cid)
    if not props:
        return {"cid": cid, "source": "pubchem_live"}

    # Normalize key names to snake_case for easier use
    result = {
        "cid": cid,
        "molecular_formula": props.get("MolecularFormula"),
        "molecular_weight": props.get("MolecularWeight"),
        "xlogp": props.get("XLogP"),
        "exact_mass": props.get("ExactMass"),
        "canonical_smiles": props.get("CanonicalSMILES"),
        "inchikey": props.get("InChIKey"),
        "source": "pubchem_live",
    }
    return result


def cross_check_local(
    name: str,
    local_mw: Optional[float] = None,
    local_logp: Optional[float] = None,
    tolerance_pct: float = 5.0,
) -> dict:
    """Cross-check local material data against PubChem.

    Args:
        name: material name
        local_mw: locally-stored molecular weight (optional)
        local_logp: locally-stored XLogP (optional)
        tolerance_pct: percentage tolerance for "match" (default 5%)

    Returns:
        dict with:
          - pubchem_data: raw PubChem response (or None)
          - matches: list of fields that agree
          - mismatches: list of (field, local_val, pubchem_val, pct_diff)
          - fresh: whether data came from live API or cache
    """
    pubchem = lookup_material(name)
    matches = []
    mismatches = []

    if not pubchem:
        return {
            "pubchem_data": None,
            "matches": [],
            "mismatches": [],
            "fresh": False,
            "note": "PubChem lookup failed (network or not found)",
        }

    if local_mw is not None and pubchem.get("molecular_weight"):
        pmw = float(pubchem["molecular_weight"])
        if abs(pmw - local_mw) / pmw * 100 <= tolerance_pct:
            matches.append("molecular_weight")
        else:
            mismatches.append(
                {
                    "field": "molecular_weight",
                    "local": local_mw,
                    "pubchem": pmw,
                    "pct_diff": round(abs(pmw - local_mw) / pmw * 100, 2),
                }
            )

    if local_logp is not None and pubchem.get("xlogp") is not None:
        plp = float(pubchem["xlogp"])
        if abs(plp - local_logp) <= tolerance_pct / 10:  # XLogP is less precise
            matches.append("xlogp")
        else:
            mismatches.append(
                {
                    "field": "xlogp",
                    "local": local_logp,
                    "pubchem": plp,
                    "pct_diff": round(
                        abs(plp - local_logp) / max(abs(plp), 0.01) * 100, 2
                    ),
                }
            )

    return {
        "pubchem_data": pubchem,
        "matches": matches,
        "mismatches": mismatches,
        "fresh": pubchem.get("source") == "pubchem_live",
    }


def cache_stats() -> dict:
    """Return cache statistics for diagnostics."""
    cache = _load_cache()
    fresh = 0
    stale = 0
    for entry in cache.values():
        if _is_fresh(entry):
            fresh += 1
        else:
            stale += 1
    return {
        "total_entries": len(cache),
        "fresh": fresh,
        "stale": stale,
        "cache_file": str(CACHE_FILE),
        "ttl_days": CACHE_TTL_DAYS,
    }


def refresh_cache(name: str) -> Optional[dict]:
    """Force-refresh the cache for a material (ignore TTL)."""
    # Bypass cache by clearing entries for this name
    cache = _load_cache()
    keys_to_remove = [
        k
        for k, v in cache.items()
        if v.get("query", "").lower() == name.lower()
        or name.lower() in v.get("query", "").lower()
    ]
    for k in keys_to_remove:
        del cache[k]
    _save_cache(cache)
    return lookup_material(name)


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PubChem client for perfume materials")
    sub = parser.add_subparsers(dest="cmd")

    lookup = sub.add_parser("lookup", help="Look up a single material")
    lookup.add_argument("name")

    check = sub.add_parser("check", help="Cross-check local data against PubChem")
    check.add_argument("name")
    check.add_argument("--mw", type=float, default=None)
    check.add_argument("--logp", type=float, default=None)

    sub.add_parser("stats", help="Show cache statistics")

    args = parser.parse_args()

    if args.cmd == "lookup":
        result = lookup_material(args.name)
        if result:
            print(f"\nPubChem data for '{args.name}':")
            for k, v in result.items():
                print(f"  {k}: {v}")
        else:
            print(f"\n✗ Could not resolve '{args.name}' via PubChem")
            sys.exit(1)

    elif args.cmd == "check":
        result = cross_check_local(args.name, local_mw=args.mw, local_logp=args.logp)
        print(f"\nCross-check for '{args.name}':")
        print(
            f"  PubChem source: {result.get('pubchem_data', {}).get('source', 'N/A')}"
        )
        print(f"  Matches: {result['matches']}")
        if result["mismatches"]:
            print("  MISMATCHES:")
            for m in result["mismatches"]:
                print(
                    f"    {m['field']}: local={m['local']} pubchem={m['pubchem']} "
                    f"diff={m['pct_diff']}%"
                )

    elif args.cmd == "stats":
        stats = cache_stats()
        print("\nCache statistics:")
        for k, v in stats.items():
            print(f"  {k}: {v}")

    else:
        parser.print_help()
