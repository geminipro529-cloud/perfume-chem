"""Parser for ``knowledge/perfumersworld_stock.md``.

The catalogue is a free-text dump where each entry is a single line of
the form::

    <Material Name><SKU> @ US$<price>/<unit>

The SKU is *concatenated to* the material name with no separator. SKUs
follow a stable pattern: a digit prefix (1–6), a 2-letter family code
(EW, EN, ES, NL, AN, …), a 5-digit numeric tail.

We split each line into (name, sku, price, unit) using a regex anchored
on the ``@ US$`` token and a SKU regex that walks back from the end of
the name+SKU prefix.

Dilutions ("X 1% in DPG", "X 10% in DPG", "X in DEP", …) are parsed
separately — they map to the same canonical material as their parent
but are recorded as alternative supplier forms.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

# SKU pattern: optional digit, 2 alpha (family), 5 digits.
# Some SKUs deviate (e.g. ISNIFF10, WU21414) — fallback regex handles those.
_SKU_RE = re.compile(r"([0-9][A-Z]{2}\d{5}|I[A-Z]+\d+|[A-Z]{2}\d{5})$")
_LINE_RE = re.compile(
    r"^(?P<head>.+?)\s*@\s*US\$\s*(?P<price>\d+(?:\.\d+)?)\s*/\s*(?P<unit>\S+)\s*$"
)
_DILUTION_RE = re.compile(
    r"^(?P<base>.+?)\s+(?P<pct>\d+(?:\.\d+)?)\s*%\s+in\s+(?P<solvent>\w+)\s*$",
    re.IGNORECASE,
)


@dataclass
class PWEntry:
    raw_name: str               # "Linalool 10% in DPG"
    base_name: str              # "Linalool"
    dilution_pct: float | None  # 10.0 (None for neat)
    dilution_solvent: str | None  # "DPG" / "TEC" / "DEP"
    sku: str | None
    price_usd: float | None
    price_unit: str | None      # "gram" / "set" / "bottle"


def _split_name_sku(head: str) -> tuple[str, str | None]:
    """Walk the SKU off the end of the concatenated name+SKU string."""
    m = _SKU_RE.search(head)
    if not m:
        return head.strip(), None
    sku = m.group(1)
    name = head[: m.start()].strip()
    return name, sku


def parse_pw_stock(path: str | Path) -> list[PWEntry]:
    """Parse the PerfumersWorld stock dump.

    Returns one :class:`PWEntry` per catalogue SKU line. Non-SKU lines
    (bare numbers like "10" indicating MOQ, blank lines, prose) are
    skipped silently.
    """
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    entries: list[PWEntry] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or "@ US$" not in line:
            continue
        m = _LINE_RE.match(line)
        if not m:
            continue
        head = m.group("head")
        price = float(m.group("price"))
        unit = m.group("unit").rstrip(".,")
        name, sku = _split_name_sku(head)
        # dilution split
        dm = _DILUTION_RE.match(name)
        if dm:
            base = dm.group("base").strip()
            pct = float(dm.group("pct"))
            solvent = dm.group("solvent").upper()
        else:
            base, pct, solvent = name, None, None
        entries.append(
            PWEntry(
                raw_name=name,
                base_name=base,
                dilution_pct=pct,
                dilution_solvent=solvent,
                sku=sku,
                price_usd=price,
                price_unit=unit,
            )
        )
    return entries


def index_by_base(entries: list[PWEntry]) -> dict[str, list[PWEntry]]:
    """Group entries by their base (non-diluted) material name."""
    out: dict[str, list[PWEntry]] = {}
    for e in entries:
        out.setdefault(e.base_name, []).append(e)
    return out


def write_parsed_snapshot(entries: list[PWEntry], out_path: str | Path) -> None:
    """Persist a parsed JSON snapshot for diffing future catalog updates."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps([asdict(e) for e in entries], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    import sys

    src = Path("knowledge/perfumersworld_stock.md")
    dst = Path("data/materials/_sources/perfumersworld_stock.parsed.json")
    entries = parse_pw_stock(src)
    write_parsed_snapshot(entries, dst)
    print(f"parsed {len(entries)} entries from {src}")
    base_idx = index_by_base(entries)
    print(f"unique base materials: {len(base_idx)}")
    print(f"snapshot → {dst}")
    # show first few groupings
    for name, items in list(base_idx.items())[:5]:
        print(f"  {name}: {[e.raw_name for e in items]}")
