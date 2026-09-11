"""Verify every DOI in the Deep Architecture evidence registry resolves.

Uses the Crossref REST API (the DOI registration agency for these publishers).
Writes ``doi_verified`` + ``doi_verification`` summary back into the registry and
exits non-zero if any DOI fails (unless ``--allow-failures``).

Usage:
    python scripts/verify_literature_dois.py
    python scripts/verify_literature_dois.py --allow-failures
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "data" / "engine_data" / "deep_architecture_evidence.json"
CROSSREF = "https://api.crossref.org/works/"
HEADERS = {"User-Agent": "perfume-chem-deep-architecture/1.0 (mailto:research@example.com)"}


def _ok(doi: str, retries: int = 3) -> bool:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(CROSSREF + urllib.parse.quote(doi), headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return 200 <= resp.status < 300
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return False
        except Exception:
            pass
        time.sleep(1.0 * (attempt + 1))
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=str(DEFAULT))
    parser.add_argument("--allow-failures", action="store_true")
    args = parser.parse_args(argv)

    path = Path(args.path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    doppler: dict[str, dict] = {}
    for group in ("dimensions", "families", "subfamilies", "archetypes"):
        for refs in payload.get(group, {}).values():
            for ref in refs:
                doi = str(ref.get("doi") or "").strip().lower()
                if doi:
                    doppler[ref["key"]] = ref

    verified: dict[str, bool] = {}
    failed: list[str] = []
    keys = sorted(doppler)
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(_ok, doppler[key]["doi"]): key for key in keys}
        for i, fut in enumerate(as_completed(futures), 1):
            key = futures[fut]
            ok = False
            try:
                ok = bool(fut.result())
            except Exception:
                ok = False
            verified[key] = ok
            if not ok:
                failed.append(doppler[key]["doi"])
            if i % 50 == 0:
                print(f"  verified {i}/{len(keys)}")

    payload["doi_verified"] = verified
    payload["doi_verification"] = {
        "checked": len(verified),
        "resolved": sum(1 for v in verified.values() if v),
        "failed_dois": sorted(failed),
    }
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"checked={len(verified)} resolved={len(verified) - len(failed)} failed={len(failed)}")
    if failed:
        print("FAILED DOIs:", failed[:20])
    if failed and not args.allow_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
