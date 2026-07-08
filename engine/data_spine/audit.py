"""Field-completeness audit for the data spine.

Run::

    python -m engine.data_spine.audit

Reports per-material and per-field gap counts so an external AI (or
the user) can target exactly the missing data needed for a given
science axis to be active.
"""

from __future__ import annotations

from collections import Counter

from .loader import load_materials


def main() -> None:
    materials = load_materials()
    if not materials:
        print("no materials loaded — run `python -m engine.data_spine.migrate` first")
        return

    n = len(materials)
    print(f"materials: {n}")
    field_counts: Counter[str] = Counter()
    for m in materials:
        for k, has in m.completeness().items():
            if has:
                field_counts[k] += 1
    print("\nfield coverage (% materials with data):")
    for k in (
        "cas", "smiles", "mw", "logp", "vp_25c", "antoine", "dhvap",
        "hsp", "odt_air", "or_targets", "trp", "hedonic", "ifra", "supplier",
    ):
        cnt = field_counts.get(k, 0)
        bar = "#" * int(cnt / n * 40)
        print(f"  {k:<12} {cnt:>4}/{n}  {cnt/n:>5.0%}  {bar}")

    # by-letter breakdown
    print("\nby letter:")
    letter_counts: Counter[str] = Counter()
    for m in materials:
        letter_counts[m.canonical_name[:1].upper()] += 1
    for letter in sorted(letter_counts):
        print(f"  {letter}: {letter_counts[letter]}")

    # most-incomplete materials (priority backfill list)
    incomplete = sorted(
        materials,
        key=lambda x: sum(x.completeness().values()),
    )
    print("\ntop-20 most-incomplete materials (backfill priorities):")
    for m in incomplete[:20]:
        score = sum(m.completeness().values())
        print(f"  {score:>2}/14  {m.canonical_name}")


if __name__ == "__main__":
    main()
