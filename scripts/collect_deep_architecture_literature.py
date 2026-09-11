"""Collect peer-reviewed literature for the Deep Architecture evidence registry.

Google Scholar has no API and blocks automated access (HTTP 429), so discovery
uses Europe PMC (field-restricted title/abstract queries, ``resultType=core``)
with a strict local relevance filter, plus Crossref for DOI verification. Both
index the same peer-reviewed journals.

Every reference must satisfy:
  * a DOI, a year, a journal;
  * at least one *must* term AND one *context* term in title/abstract.

Output: ``data/engine_data/deep_architecture_evidence.json``
Run:    python scripts/collect_deep_architecture_literature.py [--verify] [--smoke]
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "engine_data" / "deep_architecture_evidence.json"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
CROSSREF = "https://api.crossref.org/works/"
HEADERS = {"User-Agent": "perfume-chem-deep-architecture/1.0 (mailto:research@example.com)"}

OLFACTORY_CONTEXT = ["odor", "odour", "aroma", "olfact", "smell", "scent",
                     "fragrance", "perfume", "volatile", "gc-ms", "gc-o", "aed"]

# ---------------------------------------------------------------------------
# Discovery specs:  must = required topical terms,  context = domain terms
# ---------------------------------------------------------------------------

DIMENSION_SPECS: dict[str, dict[str, list[str]]] = {
    "texture": {
        "must": ["texture", "haptic", "tactile", "smoothness", "roughness", "crossmodal", "cross-modal"],
        "context": ["perception", "touch", "sensory", "crossmodal", "cross-modal", "material"],
    },
    "depth_stacking": {
        "must": ["configural", "odor object", "odour object", "perceptual blending", "mixture suppression", "elemental"],
        "context": OLFACTORY_CONTEXT,
    },
    "temporal_layering": {
        "must": ["evaporation", "release", "adaptation", "habituation", "persistence", "headspace"],
        "context": OLFACTORY_CONTEXT,
    },
    "spatial_projection": {
        "must": ["diffusion", "dispersion", "headspace", "airborne", "sillage", "projection"],
        "context": OLFACTORY_CONTEXT,
    },
    "integration_capacity": {
        "must": ["mixture", "identification", "capacity", "integration", "convergence", "working memory"],
        "context": OLFACTORY_CONTEXT,
    },
    "function_balance": {
        "must": ["suppression", "interaction", "binary mixture", "blending", "masking"],
        "context": OLFACTORY_CONTEXT,
    },
    "legibility_coherence": {
        "must": ["congruence", "congruency", "valence", "pleasantness", "suppression", "clarity"],
        "context": OLFACTORY_CONTEXT,
    },
}

FAMILY_SPECS: dict[str, dict[str, list[str]]] = {
    "citrus": {"must": ["bergamot", "limonene", "citral", "nootkatone", "grapefruit", "lemon", "neroli", "petitgrain"], "context": OLFACTORY_CONTEXT},
    "fougere": {"must": ["lavender", "coumarin", "oakmoss", "tonka", "linalool", "fougere"], "context": OLFACTORY_CONTEXT},
    "floral": {"must": ["rose", "jasmine", "ionone", "geraniol", "indole", "osmanthus", "tuberose"], "context": OLFACTORY_CONTEXT},
    "chypre": {"must": ["oakmoss", "evernia", "labdanum", "patchouli", "cistus"], "context": OLFACTORY_CONTEXT},
    "oriental": {"must": ["benzoin", "frankincense", "boswellia", "vanillin", "labdanum", "myrrh", "cistus"], "context": OLFACTORY_CONTEXT},
    "woody": {"must": ["sandalwood", "santalol", "vetiver", "agarwood", "oud", "cedarwood", "patchoulol"], "context": OLFACTORY_CONTEXT},
    "leather": {"must": ["isobutyl quinoline", "birch tar", "castoreum", "pyralone", "leather"], "context": OLFACTORY_CONTEXT},
    "marine_aquatic": {"must": ["calone", "ozone", "marine", "aquatic", "sea"], "context": OLFACTORY_CONTEXT},
    "gourmand": {"must": ["vanillin", "ethyl maltol", "maltol", "cocoa", "coffee", "heliotropin"], "context": OLFACTORY_CONTEXT},
    "musk": {"must": ["galaxolide", "muscone", "habanolide", "exaltolide", "muscenone", "macrocyclic musk"], "context": OLFACTORY_CONTEXT},
    "green": {"must": ["hexenol", "hexenal", "galbanum", "leaf alcohol", "triplal"], "context": OLFACTORY_CONTEXT},
    "aldehydic": {"must": ["aldehyde", "aldehydic", "decanal", "dodecanal"], "context": OLFACTORY_CONTEXT},
    "aromatic": {"must": ["lavender", "rosemary", "sage", "thyme", "clary", "herbal"], "context": OLFACTORY_CONTEXT},
}

# One defining-chemistry phrase per subtype; combined with its family terms.
SUBFAMILY_EXTRA: dict[str, str] = {
    "citrus_classical": "neroli petitgrain cologne",
    "citrus_aromatic": "lavender rosemary thyme",
    "citrus_floral": "orange blossom neroli",
    "citrus_woody": "vetiver cedar bergamot",
    "citrus_green": "galbanum violet leaf",
    "citrus_spicy": "ginger cardamom",
    "fougere_classical": "lavender coumarin oakmoss",
    "fougere_aromatic": "lavender coumarin citrus",
    "fougere_modern_mineral": "mineral fougere amberwood",
    "fougere_modern_tonka": "tonka coumarin vanilla",
    "fougere_green": "galbanum green fougere",
    "fougere_leathery": "leather coumarin isoquinoline",
    "floral_soliflore": "single flower",
    "floral_white": "tuberose gardenia jasmine",
    "floral_rose": "rose citronellol geraniol",
    "floral_muguet": "hydroxycitronellal lily valley",
    "floral_aldehydic": "aldehyde rose jasmine",
    "floral_green": "galbanum hyacinth",
    "floral_fruity": "peach lactone fruity",
    "floral_powdery": "orris ionone powdery",
    "floral_oriental": "floral amber vanilla",
    "chypre_classical": "bergamot labdanum oakmoss",
    "chypre_floral": "rose jasmine oakmoss",
    "chypre_fruity": "peach lactone oakmoss",
    "chypre_green": "galbanum green oakmoss",
    "chypre_leathery": "leather oakmoss",
    "chypre_modern": "evernyl clearwood bergamot",
    "oriental_classical": "vanilla resin spice",
    "oriental_amber": "benzoin labdanum vanillin amber",
    "oriental_spicy": "cinnamon clove spice",
    "oriental_woody": "sandalwood oud amber",
    "oriental_gourmand": "ethyl maltol vanilla tonka",
    "oriental_floral": "floral amber resin",
    "oriental_fresh": "citrus amber hedione",
    "woody_classical": "sandalwood cedar vetiver",
    "woody_amber": "ambrox iso e super",
    "woody_aromatic": "lavender cedar herbal",
    "woody_citrus": "vetiver bergamot",
    "woody_floral": "cedar rose jasmine",
    "woody_leathery": "cedar leather suede",
    "woody_mineral": "mineral amberwood timberol",
    "woody_smoky": "birch tar guaiac smoky",
    "woody_oriental": "oud amber resin",
    "leather_classical": "isobutyl quinoline birch tar",
    "leather_floral": "rose jasmine leather",
    "leather_smoky": "birch tar guaiacol smoke",
    "leather_suede": "suede cashmeran violet",
    "leather_oriental": "leather amber benzoin",
    "marine_ozonic": "calone ozonic floralozone",
    "marine_floral": "marine rose muguet",
    "marine_woody": "driftwood cedar marine",
    "marine_aromatic": "marine lavender rosemary",
    "gourmand_vanilla": "vanillin vanilla",
    "gourmand_chocolate": "cocoa patchouli chocolate",
    "gourmand_fruity": "fruity caramel lactone",
    "gourmand_coffee": "coffee tonka",
    "gourmand_nutty": "almond heliotropin coumarin",
    "musk_clean": "galaxolide habanolide",
    "musk_skin": "exaltolide ethylene brassylate",
    "musk_animalic": "civet castoreum animalic",
    "musk_floral": "musk rose jasmine",
    "musk_woody": "musk iso e super sandalore",
    "green_fresh": "hexenol galbanum green",
    "green_floral": "green floral galbanum",
    "green_aromatic": "galbanum clary sage",
    "aldehydic_classical": "aldehyde chanel no 5",
    "aldehydic_floral": "aldehyde white floral",
    "aldehydic_woody": "aldehyde woody musk",
    "aromatic_herbal": "lavender sage rosemary",
    "aromatic_spicy": "cardamom ginger pepper",
    "aromatic_green": "galbanum clary sage petitgrain",
}

ARCHETYPE_TERMS: dict[str, list[str]] = {
    "aromatic_fougere.classic_reference": ["fougere", "perfume"],
    "aromatic_fougere.modern_mineral": ["fougere", "mineral", "perfume"],
    "aromatic_fougere.modern_tonka_mass": ["tonka", "fougere", "perfume"],
    "layton_dna.fresh_thai": ["layton", "parfums de marly"],
    "layton_dna.indoor_amber": ["layton", "amber"],
    "layton_dna.night_intense": ["layton", "intense"],
    "woody.vetiver_classical": ["vetiver", "perfume"],
    "floral_aldehydic_amber.classic": ["chanel no 5", "aldehydic"],
    "iris_amber_woody.classic": ["iris", "perfume", "ionone"],
    "iris_amber_woody.prada_lhomme_reference": ["prada", "iris", "perfume"],
    "iris_coumarin_amber.dhi2011": ["dior homme", "iris"],
    "iris_ambrox_amber.dhi2025": ["dior homme", "ambrox"],
    "iris_sandalwood.dhp2025": ["dior homme", "sandalwood"],
    "leather_iris_amber.dhp2014": ["dior homme parfum", "leather"],
    "woody_floral_musk.classic": ["woody floral musk", "perfume"],
    "gourmand_floral.classic_reference": ["gourmand", "floral", "perfume"],
    "prada_clean_iris": ["prada", "iris"],
}


def _epmc(query: str, *, page_size: int, result_type: str = "core", retries: int = 3) -> list[dict]:
    params = urllib.parse.urlencode(
        {"query": query, "format": "json", "pageSize": str(page_size), "resultType": result_type}
    )
    url = f"{EPMC}?{params}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return payload.get("resultList", {}).get("result", [])
        except Exception:
            if attempt == retries - 1:
                return []
            time.sleep(1.5 * (attempt + 1))
    return []


def _build_query(must: list[str], context: list[str], *, terms_per_group: int = 4) -> str:
    m = " OR ".join(f'TITLE:"{t}" OR ABSTRACT:"{t}"' for t in must[:terms_per_group])
    c = " OR ".join(f'TITLE:"{t}" OR ABSTRACT:"{t}"' for t in context[:terms_per_group])
    return f"({m}) AND ({c})"


def _text_of(item: dict) -> str:
    parts = [str(item.get("title") or "")]
    abstract = item.get("abstractText")
    if abstract:
        parts.append(str(abstract))
    return re.sub(r"<[^>]+>", " ", " ".join(parts)).lower()


def _title_of(item: dict) -> str:
    return re.sub(r"<[^>]+>", " ", str(item.get("title") or "")).lower()


def _relevant(item: dict, must: list[str], context: list[str], all_must: bool = False) -> bool:
    title = _title_of(item)
    text = _text_of(item)
    must_l = [t.lower() for t in must]
    context_l = [t.lower() for t in context]
    if not any(c in text for c in context_l):
        return False
    if all_must:
        return all(t in text for t in must_l)
    # Precision-first: the defining term must appear in the title.
    return any(t in title for t in must_l)


def _to_ref(item: dict, *, category: str, used_for: str) -> dict | None:
    doi = str(item.get("doi") or "").strip().lower()
    info = item.get("journalInfo") or {}
    year = str(item.get("pubYear") or info.get("yearOfPublication") or "").strip()
    if not year:
        date = str(item.get("firstPublicationDate") or "")
        year = date[:4]
    if not doi or not year.isdigit():
        return None
    journal = str(
        item.get("journalTitle")
        or (info.get("journal") or {}).get("title")
        or ""
    ).strip()
    if not journal:
        return None
    return {
        "key": "doi:" + doi,
        "title": re.sub(r"<[^>]+>", "", str(item.get("title") or "")).strip(),
        "authors": str(item.get("authorString") or "").strip(),
        "journal": journal,
        "year": int(year),
        "doi": doi,
        "url": "https://doi.org/" + doi,
        "category": category,
        "used_for": used_for,
        "citations": int(item.get("citedByCount") or 0),
        "tier": "A_peer_reviewed",
    }


def _dedupe(refs: list[dict], limit: int) -> list[dict]:
    seen: dict[str, dict] = {}
    for ref in refs:
        seen.setdefault(ref["key"], ref)
    return sorted(seen.values(), key=lambda r: -r["citations"])[:limit]


def _crossref_ok(doi: str, retries: int = 2) -> bool:
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
        time.sleep(1.0)
    return False


def _context_clause(context: list[str], n: int = 6) -> str:
    parts = [f'TITLE:"{c}"' for c in context[:n]]
    parts += [f'ABSTRACT:"{c}"' for c in context[:n]]
    return "(" + " OR ".join(parts) + ")"


def _collect(specs: dict[str, dict], *, group: str, limit: int, page_size: int) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for key, spec in specs.items():
        must, context = spec["must"], spec["context"]
        require = spec.get("require")
        all_must = bool(spec.get("all_must"))
        refs: list[dict] = []
        if all_must:
            queries = [_build_query(must, context)]
        else:
            ctx = _context_clause(context)
            queries = [f'(TITLE:"{term}") AND {ctx}' for term in must]
        for query in queries:
            for item in _epmc(query, page_size=page_size):
                if not _relevant(item, must, context, all_must=all_must):
                    continue
                if require:
                    text = _text_of(item)
                    if not any(t.lower() in text for t in require):
                        continue
                ref = _to_ref(item, category=group, used_for=f"{key}: {'; '.join((require or must)[:3])}")
                if ref:
                    refs.append(ref)
            time.sleep(0.3)
        kept = _dedupe(refs, limit)
        if kept:
            out[key] = kept
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--page-size", type=int, default=25)
    parser.add_argument("--out", default=str(OUT_PATH))
    args = parser.parse_args(argv)

    dims = dict(DIMENSION_SPECS)
    fams = dict(FAMILY_SPECS)
    subs = {}
    for key, extra in SUBFAMILY_EXTRA.items():
        family = key.split("_")[0]
        base = FAMILY_SPECS.get(family, {"must": [], "context": OLFACTORY_CONTEXT})
        must = (base["must"] or extra.split())[:4]
        subs[key] = {"must": must, "context": OLFACTORY_CONTEXT, "require": extra.split()}
    archs = {
        k: {"must": v, "context": ["perfume", "fragrance", "gc-ms", "analysis", "odor", "odour"],
            "require": ["perfume", "fragrance", "gc-ms", "analysis", "odor", "odour"],
            "all_must": True}
        for k, v in ARCHETYPE_TERMS.items()
    }

    if args.smoke:
        dims = {"texture": DIMENSION_SPECS["texture"]}
        fams = {"musk": FAMILY_SPECS["musk"]}
        subs = {"musk_clean": subs["musk_clean"]}
        archs = {}

    payload = {
        "schema_version": "deep_architecture_evidence_v1",
        "evidence_class": "PEER_REVIEWED_LITERATURE",
        "sources": ["Europe PMC REST (discovery, field-restricted)", "Crossref (DOI)"],
        "note": "Google Scholar blocks automation; Europe PMC/Crossref index the same peer-reviewed journals.",
        "dimensions": _collect(dims, group="dimension", limit=args.limit, page_size=args.page_size),
        "families": _collect(fams, group="family", limit=args.limit, page_size=args.page_size),
        "subfamilies": _collect(subs, group="subfamily", limit=max(5, args.limit // 3), page_size=args.page_size),
        "archetypes": _collect(archs, group="archetype_reference", limit=5, page_size=args.page_size) if archs else {},
    }

    coverage = {g: {k: len(v) for k, v in payload[g].items()} for g in ("dimensions", "families", "subfamilies", "archetypes")}
    payload["coverage"] = coverage
    payload["gaps"] = {
        g: sorted(set(specs) - set(payload[g]))
        for g, specs in (("dimensions", dims), ("families", fams), ("subfamilies", subs), ("archetypes", archs))
    }

    verified: dict[str, bool] = {}
    if args.verify:
        all_refs = {r["key"]: r for g in ("dimensions", "families", "subfamilies", "archetypes") for refs in payload[g].values() for r in refs}
        for i, (key, ref) in enumerate(all_refs.items(), 1):
            verified[key] = _crossref_ok(ref["doi"])
            if i % 25 == 0:
                print(f"  verified {i}/{len(all_refs)}")
            time.sleep(0.12)
        payload["doi_verified"] = verified

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    total = sum(len(v) for g in ("dimensions", "families", "subfamilies", "archetypes") for v in payload[g].values())
    print(f"wrote {out} ({total} refs)")
    for g in ("dimensions", "families", "subfamilies", "archetypes"):
        print(f"  {g}: {len(payload[g])} keys, refs={sum(len(v) for v in payload[g].values())}, gaps={payload['gaps'][g]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
