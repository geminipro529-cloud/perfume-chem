#!/usr/bin/env python3
"""
Query the pairing rules knowledge graph for material combinations and synergies.

Usage:
    python scripts/query_pairings.py --material "Bergamot FCF"
    python scripts/query_pairings.py --pair "Bergamot FCF" "Cardamom EO"
    python scripts/query_pairings.py --list-all
    python scripts/query_pairings.py --type synergy
"""

import json
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PAIRING_FILES = [
    ROOT / "data/knowledge_graph/pairing_rules.json",
    ROOT / "data/knowledge_graph/pairing_rules_discovered.json",
]
SYNERGY_FILE = ROOT / "data/knowledge_graph/synergy_matrix.json"


def load_pairings() -> list[dict]:
    """Load all pairing rules from both files."""
    rules = []
    for f in PAIRING_FILES:
        if f.exists():
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    rules.extend(data)
                elif isinstance(data, dict):
                    rules.extend(data.values())
            except (json.JSONDecodeError, Exception) as e:
                print(f"⚠️  Could not parse {f.name}: {e}", file=sys.stderr)
    return rules


def load_synergies() -> dict:
    """Load synergy matrix."""
    if SYNERGY_FILE.exists():
        try:
            return json.loads(SYNERGY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, Exception) as e:
            print(f"⚠️  Could not parse synergy_matrix.json: {e}", file=sys.stderr)
    return {}


def normalize(s: str) -> str:
    return s.strip().lower()


def find_by_material(material: str, rules: list[dict]) -> list[dict]:
    """Find all pairings involving a specific material."""
    mat = normalize(material)
    results = []
    for r in rules:
        a = normalize(r.get("material_a", ""))
        b = normalize(r.get("material_b", ""))
        if mat in (a, b):
            results.append(r)
    return results


def find_pair(a: str, b: str, rules: list[dict]) -> list[dict]:
    """Find pairings between two specific materials."""
    na, nb = normalize(a), normalize(b)
    results = []
    for r in rules:
        ra = normalize(r.get("material_a", ""))
        rb = normalize(r.get("material_b", ""))
        if (na == ra and nb == rb) or (na == rb and nb == ra):
            results.append(r)
    return results


def print_material_results(material: str, results: list[dict]):
    synergies = [r for r in results if r.get("type") == "synergy"]
    pairings = [r for r in results if r.get("type") == "pairing"]

    print(f"\n🔗 PAIRINGS FOR: {material} ({len(results)} found)\n")

    if synergies:
        print("SYNERGIES (amplification documented):")
        print(f"| {'Paired With':<30} | {'Effect':<70} | {'Source':<35} |")
        print(f"|{'-' * 32}|{'-' * 72}|{'-' * 37}|")
        for r in synergies:
            partner = (
                r["material_b"]
                if normalize(r["material_a"]) == normalize(material)
                else r["material_a"]
            )
            effect = r.get("effect", "?")[:68]
            source = r.get("source", "?")[:33]
            print(f"| {partner:<30} | {effect:<70} | {source:<35} |")
        print()

    if pairings:
        print("PAIRINGS (complementary):")
        print(f"| {'Paired With':<30} | {'Effect':<70} | {'Source':<35} |")
        print(f"|{'-' * 32}|{'-' * 72}|{'-' * 37}|")
        for r in pairings:
            partner = (
                r["material_b"]
                if normalize(r["material_a"]) == normalize(material)
                else r["material_a"]
            )
            effect = r.get("effect", "?")[:68]
            source = r.get("source", "?")[:33]
            print(f"| {partner:<30} | {effect:<70} | {source:<35} |")
        print()

    if not results:
        print(f"No pairings found for '{material}'.")
        print(f"\nConsider running the appropriate pairing discovery agent:")
        print(f"  - agent-citrus-top (citrus, green, top notes)")
        print(f"  - agent-floral-heart (floral, heart notes)")
        print(f"  - agent-woody-base (woody, amber, base)")
        print(f"  - agent-musk-fixative (musks, fixatives, gourmand)")
        print(f"  - agent-spice-aromatic (spices, aromatics, specialty)")


def print_pair_results(a: str, b: str, results: list[dict]):
    print(f"\n🔗 PAIR: {a} + {b}\n")

    if results:
        for r in results:
            print(f"  Type:   {r.get('type', '?')}")
            print(f"  Effect: {r.get('effect', '?')}")
            print(f"  Source: {r.get('source', '?')}")
            print()
    else:
        print(f"No documented pairing found for '{a}' + '{b}'.")
        print("This doesn't mean they're incompatible — just not yet documented.")
        print("Consider running the relevant pairing discovery agent.")


def print_all(rules: list[dict]):
    print(f"\n📚 ALL PAIRING RULES ({len(rules)} total)\n")

    by_type = {}
    for r in rules:
        t = r.get("type", "unknown")
        by_type.setdefault(t, []).append(r)

    for t, items in sorted(by_type.items()):
        print(f"{t.upper()} ({len(items)}):")
        for r in items:
            print(
                f"  {r.get('material_a', '?')} + {r.get('material_b', '?')} → {r.get('effect', '?')}"
            )
        print()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Query perfume pairing rules knowledge graph"
    )
    parser.add_argument(
        "--material", "-m", type=str, help="Find pairings for a specific material"
    )
    parser.add_argument(
        "--pair", "-p", nargs=2, metavar=("A", "B"), help="Check a specific pair"
    )
    parser.add_argument(
        "--list-all", "-l", action="store_true", help="List all pairing rules"
    )
    parser.add_argument(
        "--type",
        "-t",
        type=str,
        choices=["synergy", "pairing"],
        help="Filter by rule type",
    )
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    rules = load_pairings()

    if args.type:
        rules = [r for r in rules if r.get("type") == args.type]

    if args.json:
        print(json.dumps(rules, indent=2, ensure_ascii=False))
        return

    if args.list_all:
        print_all(rules)
    elif args.pair:
        a, b = args.pair
        results = find_pair(a, b, rules)
        print_pair_results(a, b, results)
    elif args.material:
        results = find_by_material(args.material, rules)
        print_material_results(args.material, results)
    else:
        parser.print_help()
        print(f"\nLoaded {len(rules)} pairing rules from knowledge graph.")


if __name__ == "__main__":
    main()
