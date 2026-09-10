#!/usr/bin/env python3
"""PerfumersWorld intake — resolve inventory materials to SKUs and fetch their data.

This is an external-data intake tool, not a pipeline script. It never computes
or promotes a scientific result. Every fetched byte is cached and hashed, and
the parsed output carries supplier provenance so downstream consumers can bind
it as SUPPLIER_TECHNICAL evidence only.

Sources per material:
  - DuckDuckGo lite: resolve the material name to a perfumersworld.com SKU
  - view.php?pro_id=<SKU>: name, CAS, physical state, relative odor impact,
    odor life on the smelling strip, notes pyramid
  - ifra/COA/<SKU>.pdf, ifra/IFRA/IFRA_<SKU>.pdf, ifra/MSDS/<SKU>.pdf:
    supplier compliance documents (validated by PDF magic)
  - ifra/view-page.php?pro_id=<SKU>&ifra=defaultOpen: inline IFRA certificate

Usage:
  python tools/pw_enrich.py --materials "Hedione,Linalool,Coumarin" --limit 3
  python tools/pw_enrich.py --from-inventory --limit 20
"""

from __future__ import annotations

import argparse
import hashlib
import html as html_module
import http.client
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CACHE = REPO_ROOT / "data" / "external" / "perfumersworld"
DEFAULT_OUT = REPO_ROOT / "data" / "knowledge_graph" / "pw_material_data.json"
INVENTORY_PATH = REPO_ROOT / "inventory.txt"
USER_AGENT = "Mozilla/5.0 (compatible; perfume-chem intake; +local)"
MAX_HTML_BYTES = 6_000_000
MAX_PDF_BYTES = 20_000_000
_SKU_IN_URL = re.compile(r"perfumersworld\.com/(?:ifra/)?view-page\.php\?pro_id=([A-Za-z0-9]+)")
_SKU_VIEW = re.compile(r"perfumersworld\.com/view\.php\?pro_id=([A-Za-z0-9]+)")
_CAS = re.compile(r"\b\d{2,7}-\d{2}-\d\b")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _display_path(path: pathlib.Path) -> str:
    """Repo-relative display path that also works for relative or external inputs."""
    resolved = path.resolve()
    for base in (REPO_ROOT, pathlib.Path.cwd()):
        try:
            return str(resolved.relative_to(base.resolve())).replace("\\", "/")
        except ValueError:
            continue
    return str(resolved).replace("\\", "/")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strip_tags(text: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html_module.unescape(text)).strip()


class Cache:
    def __init__(self, root: pathlib.Path) -> None:
        self.root = root
        self.raw = root / "raw"
        self.raw.mkdir(parents=True, exist_ok=True)
        self.index_path = root / "cache_index.json"
        self.index: dict[str, dict[str, object]] = {}
        if self.index_path.is_file():
            self.index = json.loads(self.index_path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.index_path.write_text(
            json.dumps(self.index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def get(self, url: str) -> bytes | None:
        entry = self.index.get(url)
        if not entry:
            return None
        path = self.raw / str(entry["sha256"])
        if not path.is_file():
            return None
        return path.read_bytes()

    def put(self, url: str, data: bytes) -> None:
        digest = _sha256(data)
        (self.raw / digest).write_bytes(data)
        self.index[url] = {
            "sha256": digest,
            "bytes": len(data),
            "fetched_at": _now(),
        }
        self.save()


def fetch(
    url: str,
    cache: Cache,
    *,
    limit: int,
    throttle: float,
    last_request: list[float],
) -> tuple[int, bytes]:
    cached = cache.get(url)
    if cached is not None:
        return 200, cached
    attempts = 3
    for attempt in range(attempts):
        wait = throttle - (time.time() - last_request[0])
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                data = response.read(limit)
                last_request[0] = time.time()
                cache.put(url, data)
                return response.status, data
        except http.client.IncompleteRead as exc:
            last_request[0] = time.time()
            partial = bytes(exc.partial or b"")
            if partial and attempt == attempts - 1:
                cache.put(url, partial)
                return 206, partial
            continue
        except urllib.error.HTTPError as exc:
            last_request[0] = time.time()
            return exc.code, b""
        except (urllib.error.URLError, TimeoutError, OSError, ConnectionError):
            last_request[0] = time.time()
            continue
    return 0, b""


def _norm_name(name: str) -> str:
    name = html_module.unescape(name).lower()
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def _compact(name: str) -> str:
    """Normalise to alphanumerics only so C-10, C 10 and C10 all match."""
    return re.sub(r"[^a-z0-9]+", "", html_module.unescape(name).lower())


def build_catalogue_index(
    cache: Cache, *, throttle: float, last_request: list[float]
) -> dict[str, str]:
    """Fetch the full supplies table once and cache the name -> SKU index.

    `perfume-supplies.php` lists every product as a table row with the product
    name, SKU and shop category; it is more complete than the A-Z class pages.
    """
    url = "https://www.perfumersworld.com/perfume-supplies.php"
    status, data = fetch(
        url, cache, limit=30_000_000, throttle=throttle, last_request=last_request
    )
    if status != 200 or not data:
        raise RuntimeError(f"catalogue fetch failed: status {status}")
    text = data.decode("utf-8", errors="replace")
    index: dict[str, str] = {}
    meta: dict[str, dict[str, str]] = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S):
        match = re.search(r'href="view\.php\?pro_id=([A-Za-z0-9]+)"\s+title="([^"]*)"', row)
        if not match:
            continue
        sku, raw_name = match.group(1), match.group(2)
        name = html_module.unescape(re.sub(r"\s+", " ", raw_name)).strip()
        if not name or not sku:
            continue
        index.setdefault(name, sku)
        category = re.search(r'name="product_category"[^>]*value="([^"]*)"', row)
        price = re.search(r"@ US\$([\d.,]+)/", row)
        meta.setdefault(
            name,
            {
                "sku": sku,
                "category": html_module.unescape(category.group(1)) if category else "",
                "price_usd_per_g": price.group(1) if price else "",
            },
        )
    if len(index) < 100:
        raise RuntimeError(f"catalogue parse looks wrong: {len(index)} rows")
    (cache.root / "catalogue_index.json").write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (cache.root / "catalogue_meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return index


def load_catalogue_index(cache: Cache) -> dict[str, str]:
    path = cache.root / "catalogue_index.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_aliases(cache: Cache) -> dict[str, str]:
    """Optional name -> PerfumersWorld catalogue-name corrections."""
    path = cache.root / "aliases.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_manual_skus(cache: Cache) -> dict[str, str]:
    """Optional name -> SKU pins for products the catalogue index omits.

    Out-of-stock items are absent from the supplies table but still have a
    product page; a DDG-lite lookup resolves them and the SKU is pinned here so
    later runs stay deterministic.
    """
    path = cache.root / "manual_skus.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


_SUFFIX_WHITELIST = {"synthetic", "undiluted", "100", "neat", "pure", "natural"}


def resolve_from_index(
    name: str, index: dict[str, str], aliases: dict[str, str]
) -> tuple[str | None, str | None, str]:
    query = _norm_name(name)
    if not query:
        return None, None, "empty"
    compact = {_compact(catalogue): (catalogue, sku) for catalogue, sku in index.items()}
    if name in aliases:
        target = aliases[name]
        if target in index:
            return index[target], target, "alias"
        match = compact.get(_compact(target))
        if match:
            return match[1], match[0], "alias"
    match = compact.get(_compact(query))
    if match:
        return match[1], match[0], "exact"
    query_compact = _compact(query)
    whitelist = {_compact(suffix) for suffix in _SUFFIX_WHITELIST}
    for candidate, (catalogue, sku) in compact.items():
        if not candidate.startswith(query_compact):
            continue
        suffix = candidate[len(query_compact) :]
        if suffix in whitelist:
            return sku, catalogue, "suffix"
    return None, None, "containment"


def resolve_containment(
    name: str, index: dict[str, str], aliases: dict[str, str]
) -> tuple[str | None, str | None]:
    query = _norm_name(name)
    candidates = [
        (catalogue, sku) for catalogue, sku in index.items() if query in _norm_name(catalogue)
    ]
    if not candidates:
        tokens = [t for t in query.split() if len(t) > 2]
        candidates = [
            (catalogue, sku)
            for catalogue, sku in index.items()
            if tokens and all(t in _norm_name(catalogue) for t in tokens)
        ]
    if not candidates:
        return None, None
    candidates.sort(key=lambda item: (len(item[0]), item[0]))
    return candidates[0][1], candidates[0][0]


def resolve_via_pw_search(
    name: str, cache: Cache, *, throttle: float, last_request: list[float]
) -> tuple[str | None, str | None]:
    """Site-native search for products the catalogue index does not list.

    Out-of-stock items are absent from the supplies table but still have a
    product page, so a search is the fallback for them.
    """
    url = "https://www.perfumersworld.com/product-search.php?" + urllib.parse.urlencode(
        {"query": name, "submit": ""}
    )
    status, data = fetch(
        url, cache, limit=30_000_000, throttle=throttle, last_request=last_request
    )
    if status not in (200, 206) or not data:
        return None, None
    text = data.decode("utf-8", errors="replace")
    target = _compact(name)
    for match in re.finditer(r"view\.php\?pro_id=([A-Za-z0-9]+)", text):
        window = text[match.end() : match.end() + 200]
        title = re.search(r'title="([^"]*)"', window)
        if title and target and target in _compact(html_module.unescape(title.group(1))):
            return match.group(1), html_module.unescape(title.group(1))
    return None, None


def resolve_via_ddg(
    name: str, *, throttle: float, last_request: list[float]
) -> tuple[str | None, str | None]:
    """DuckDuckGo-lite lookup for products the catalogue index omits.

    Uses raw requests (not the evidence cache) with backoff, because the lite
    endpoint serves an anti-bot page that must not be cached as a result.
    """
    forms = [
        f"perfumersworld {name}",
        f"site:perfumersworld.com {name}",
        f"{name} perfumersworld view.php",
    ]
    for form in forms:
        for attempt in range(3):
            wait = throttle - (time.time() - last_request[0])
            if wait > 0:
                time.sleep(wait)
            query = urllib.parse.quote_plus(form)
            url = f"https://lite.duckduckgo.com/lite/?q={query}"
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            data = b""
            try:
                with urllib.request.urlopen(req, timeout=45) as response:
                    data = response.read(2_000_000)
            except (urllib.error.URLError, urllib.error.HTTPError, OSError, http.client.HTTPException):
                data = b""
            last_request[0] = time.time()
            text = data.decode("utf-8", errors="replace")
            target = _compact(name)
            for match in re.finditer(r"uddg=([^&\"]+)|(https?://[^\"\s]+)", text):
                candidate = match.group(1) or match.group(2) or ""
                candidate = urllib.parse.unquote(candidate)
                sku = re.search(r"perfumersworld\.com/view\.php\?pro_id=([A-Za-z0-9]+)", candidate)
                if sku:
                    return sku.group(1), None
            if "perfumersworld" in text.lower() and target in _compact(text):
                time.sleep(4)
                continue
            time.sleep(6 * (attempt + 1))
    return None, None


def resolve_sku(
    name: str,
    cache: Cache,
    index: dict[str, str],
    aliases: dict[str, str],
    manual: dict[str, str],
    *,
    throttle: float,
    last_request: list[float],
    ddg_fallback: bool,
    strict: bool = False,
    pw_search: bool = False,
) -> tuple[str | None, str | None, str]:
    if name in manual:
        return manual[name], None, "manual_sku"
    sku, catalogue_name, confidence = resolve_from_index(name, index, aliases)
    if sku:
        return sku, catalogue_name, confidence
    if pw_search:
        sku, title = resolve_via_pw_search(
            name, cache, throttle=throttle, last_request=last_request
        )
        if sku:
            return sku, title, "pw_search"
    if ddg_fallback:
        sku, title = resolve_via_ddg(name, throttle=throttle, last_request=last_request)
        if sku:
            return sku, title, "ddg_lite"
    if strict:
        return None, None, confidence
    sku, catalogue_name = resolve_containment(name, index, aliases)
    if sku:
        return sku, catalogue_name, "containment_low_confidence"
    return None, None, confidence


def parse_product(text: str) -> dict[str, object]:
    title_match = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
    title = _strip_tags(title_match.group(1)) if title_match else ""
    flat = _strip_tags(text)
    impact = re.search(r"Relative Odor Impact\s+([\d,]+(?:\.\d+)?)", flat)
    life = re.search(r"Odor Life \(Smelling Strip\)\s+([\d.]+)\s*hrs?", flat)
    state = re.search(r"Physical State\s+([A-Za-z][A-Za-z /-]{1,30})", flat)
    cas_match = re.search(r"CAS\s*[:#]?\s*(\d{2,7}-\d{2}-\d)", flat) or re.search(
        r"(\d{2,7}-\d{2}-\d)", flat
    )
    pyramid = re.search(r"Notes Pyramid([^|]{0,120})", flat)
    return {
        "title": title.split("|")[0].strip(),
        "cas": cas_match.group(1) if cas_match else None,
        "relative_impact": impact.group(1) if impact else None,
        "odour_life_hrs": life.group(1) if life else None,
        "physical_state": state.group(1).strip() if state else None,
        "notes_pyramid_raw": pyramid.group(0)[:140] if pyramid else None,
    }


def parse_ifra_page(text: str) -> dict[str, object]:
    flat = _strip_tags(text)
    version = re.search(r"IFRA\s+(\d+(?:st|nd|rd|th)\s+Amendment\s+\d{4})", flat)
    maxima = re.findall(
        r"([A-Za-z][A-Za-z /&()-]{3,60}?)\s+(\d+)\s+(<?[\d.]+|Not suitable)", flat
    )
    return {
        "standard": version.group(1) if version else None,
        "class_maxima": maxima[:20],
    }


def parse_inventory(path: pathlib.Path) -> list[str]:
    names: list[str] = []
    state_words = re.compile(
        r"\([^)]*(?:%|neat|crystal|solid|powder|w/w|v/v|nominal|dilution)[^)]*\)\s*$", re.I
    )
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("- "):
            continue
        name = line[2:].split("#", 1)[0].strip()
        name = re.sub(r"\s*\[[^\]]*\]\s*$", "", name)
        for _ in range(3):
            cleaned = state_words.sub("", name).strip(" .,")
            cleaned = re.sub(
                r"\s+\d+(?:\.\d+)?%\s*(?:v/v|w/w|nominal)?\s*(?:in\s+[A-Za-z0-9 /()'-]+)?\s*$",
                "",
                cleaned,
                flags=re.I,
            ).strip(" .,")
            if cleaned == name:
                break
            name = cleaned
        if name:
            names.append(name)
    return names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--materials", type=str, default=None, help="Comma-separated material names")
    parser.add_argument(
        "--materials-file",
        type=pathlib.Path,
        default=None,
        help="Read one material name per line (use for names containing commas)",
    )
    parser.add_argument("--from-inventory", action="store_true", help="Parse names from inventory.txt")
    parser.add_argument("--limit", type=int, default=0, help="Max materials this run (0 = all)")
    parser.add_argument("--cache-dir", type=pathlib.Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--throttle", type=float, default=1.2, help="Seconds between live requests")
    parser.add_argument("--no-docs", action="store_true", help="Skip compliance PDF fetch")
    parser.add_argument("--resolve-only", action="store_true", help="Resolve SKUs, no page fetches")
    parser.add_argument("--build-index", action="store_true", help="(Re)build the PW catalogue index")
    parser.add_argument(
        "--no-ddg", action="store_false", dest="ddg_fallback", help="Do not use DuckDuckGo lite fallback"
    )
    parser.add_argument("--strict", action="store_true", help="Accept exact/alias/suffix only; no containment")
    parser.add_argument("--search", action="store_true", help="Use PW site search for unresolved names")
    parser.add_argument("--refresh", action="store_true", help="Refetch materials already marked OK")
    args = parser.parse_args(argv)

    if args.materials_file:
        names = [
            n.strip()
            for n in args.materials_file.read_text(encoding="utf-8-sig").splitlines()
            if n.strip()
        ]
    elif args.materials:
        names = [n.strip() for n in args.materials.split(",") if n.strip()]
    elif args.from_inventory:
        names = parse_inventory(INVENTORY_PATH)
    else:
        parser.error("pass --materials, --materials-file, or --from-inventory")
    if args.limit:
        names = names[: args.limit]
    if not names:
        print("no materials selected", file=sys.stderr)
        return 2

    cache = Cache(args.cache_dir)
    last_request = [0.0]
    catalogue = load_catalogue_index(cache)
    aliases = load_aliases(cache)
    manual = load_manual_skus(cache)
    if args.build_index or not catalogue:
        print("building PW catalogue index ...")
        catalogue = build_catalogue_index(cache, throttle=args.throttle, last_request=last_request)
        print(f"catalogue index: {len(catalogue)} materials")
    out_path = pathlib.Path(args.out)
    existing: dict[str, dict[str, object]] = {}
    if out_path.is_file():
        prior = json.loads(out_path.read_text(encoding="utf-8"))
        for record in prior.get("materials", []):
            name = record.get("inventory_name")
            if name:
                existing[name] = record
    records = []
    processed: set[str] = set()
    for index, name in enumerate(names, 1):
        if name in processed:
            continue
        processed.add(name)
        prior = existing.get(name)
        if not args.refresh and prior and prior.get("status") in ("OK", "RESOLVED"):
            records.append(prior)
            print(f"[{index}/{len(names)}] {name} — cached ({prior.get('sku')})")
            continue
        print(f"[{index}/{len(names)}] {name}", flush=True)
        record: dict[str, object] = {
            "inventory_name": name,
            "source": "perfumersworld.com",
            "evidence_class": "SUPPLIER_TECHNICAL",
            "retrieved_at": _now(),
        }
        sku, catalogue_name, origin = resolve_sku(
            name,
            cache,
            catalogue,
            aliases,
            manual,
            throttle=args.throttle,
            last_request=last_request,
            ddg_fallback=args.ddg_fallback,
            strict=args.strict,
            pw_search=args.search,
        )
        record["sku"] = sku
        record["resolution"] = origin
        if catalogue_name:
            record["pw_name"] = catalogue_name
        if not sku:
            record["status"] = "UNRESOLVED"
            records.append(record)
            print("   UNRESOLVED")
            continue
        record["pw_url"] = f"https://www.perfumersworld.com/view.php?pro_id={sku}"
        if args.resolve_only:
            record["status"] = "RESOLVED"
            records.append(record)
            print(f"   SKU {sku}")
            continue
        status, data = fetch(
            str(record["pw_url"]), cache, limit=MAX_HTML_BYTES, throttle=args.throttle, last_request=last_request
        )
        record["product_status"] = status
        record["fields"] = parse_product(data.decode("utf-8", errors="replace")) if data else {}
        docs: dict[str, object] = {}
        if not args.no_docs:
            doc_urls = {
                "coa": f"https://www.perfumersworld.com/ifra/COA/{sku}.pdf",
                "ifra": f"https://www.perfumersworld.com/ifra/IFRA/IFRA_{sku}.pdf",
                "msds": f"https://www.perfumersworld.com/ifra/MSDS/{sku}.pdf",
            }
            for kind, url in doc_urls.items():
                doc_status, doc_data = fetch(
                    url, cache, limit=MAX_PDF_BYTES, throttle=args.throttle, last_request=last_request
                )
                docs[kind] = {
                    "url": url,
                    "status": doc_status,
                    "bytes": len(doc_data),
                    "sha256": _sha256(doc_data) if doc_data else None,
                    "pdf": doc_data[:5] == b"%PDF-",
                }
            ifr_url = f"https://www.perfumersworld.com/ifra/view-page.php?pro_id={sku}&ifra=defaultOpen"
            ifr_status, ifr_data = fetch(
                ifr_url, cache, limit=MAX_HTML_BYTES, throttle=args.throttle, last_request=last_request
            )
            docs["ifra_page"] = {
                "url": ifr_url,
                "status": ifr_status,
                "bytes": len(ifr_data),
                "sha256": _sha256(ifr_data) if ifr_data else None,
            }
            if ifr_data:
                record["ifra"] = parse_ifra_page(ifr_data.decode("utf-8", errors="replace"))
        record["docs"] = docs
        record["status"] = "OK" if data else "PAGE_FETCH_FAILED"
        records.append(record)
        fields = record.get("fields", {})
        print(f"   SKU {sku} | impact={fields.get('relative_impact')} life={fields.get('odour_life_hrs')}h")

    merged: dict[str, dict[str, object]] = dict(existing)
    for record in records:
        merged[str(record["inventory_name"])] = record
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "pw-material-data-v1",
        "generated_at": _now(),
        "source": "https://www.perfumersworld.com",
        "evidence_class": "SUPPLIER_TECHNICAL",
        "cache_dir": _display_path(args.cache_dir),
        "materials": [merged[name] for name in sorted(merged)],
    }
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ok = sum(1 for record in merged.values() if record.get("status") == "OK")
    print(f"\nwrote {out_path} ({len(merged)} records, {ok} ok)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
