"""Hierarchical odor ontology for semantic fragrance search.

Implements Perplexity recommendation: "Build a high-quality odor-label ontology
aligned to existing industry wheels and sentiment vocabularies."

Provides:
  - Hierarchical odor taxonomy: family → subfamily → descriptors
  - Material → odor mapping from knowledge graph data
  - Semantic search: "find materials similar to X"
  - Odor distance: how far apart are two materials in odor space?

Based on Michael Edwards fragrance wheel + Arctander classifications.
"""

from engine.optimizer.models import get_materials_db

# ── Odor Taxonomy ──
# family → subfamilies → descriptors (keywords that map to this node)
ODOR_TREE: dict[str, dict[str, list[str]]] = {
    "citrus": {
        "lemon": ["lemon", "citral", "lemongrass", "lemon peel"],
        "orange": ["orange", "neroli", "petitgrain", "bitter orange"],
        "bergamot": ["bergamot", "earl grey"],
        "grapefruit": ["grapefruit", "nootkatone"],
        "lime": ["lime", "yuzu"],
        "mandarin": ["mandarin", "tangerine", "clementine"],
    },
    "floral": {
        "rose": ["rose", "geraniol", "citronellol", "phenyl ethyl alcohol"],
        "jasmine": ["jasmine", "indole", "benzyl acetate", "hedione"],
        "lily": ["lily", "muguet", "hydroxycitronellal", "lyral"],
        "violet": ["violet", "ionone", "orris", "iris"],
        "tuberose": ["tuberose", "methyl benzoate"],
        "ylang": ["ylang", "ylang-ylang", "cananga"],
        "orange_blossom": ["orange blossom", "neroli", "methyl anthranilate"],
        "lavender": ["lavender", "linalool", "linalyl acetate"],
    },
    "woody": {
        "cedar": ["cedar", "cedarwood", "cedrol", "virginiamyl"],
        "sandalwood": ["sandalwood", "santalol", "javanol"],
        "vetiver": ["vetiver", "vetiveryl", "khusimol"],
        "patchouli": ["patchouli", "patchoulol", "norpatchoulenol"],
        "guaiac": ["guaiacwood", "guaiacol", "guaiac"],
        "oud": ["oud", "agarwood", "cypriol"],
        "birch": ["birch", "birch tar", "rectified birch"],
    },
    "amber": {
        "vanilla": ["vanilla", "vanillin", "ethyl vanillin"],
        "benzoin": ["benzoin", "styrax", "benzyl benzoate"],
        "labdanum": ["labdanum", "cistus", "amber"],
        "coumarin": ["coumarin", "tonka", "tonka bean"],
        "incense": ["incense", "frankincense", "olibanum", "elemi"],
    },
    "musk": {
        "white_musk": ["white musk", "galaxolide", "habanolide",
                       "ethylene brassylate"],
        "animalic_musk": ["musk", "civet", "castoreum", "muscone",
                          "exaltone"],
        "clean_musk": ["iso e super", "ambroxan", "cashmeran"],
        "powdery_musk": ["musk ketone", "helvetolide", "exaltolide"],
    },
    "spicy": {
        "warm_spice": ["cinnamon", "cinnamaldehyde", "clove", "eugenol",
                       "nutmeg"],
        "cool_spice": ["cardamom", "ginger", "elemi", "pink pepper"],
        "anise": ["anise", "anethole", "star anise", "fennel"],
    },
    "green": {
        "leafy": ["green", "cis-3-hexenol", "galbanum", "violet leaf"],
        "herbal": ["basil", "thyme", "rosemary", "sage", "artemisia"],
        "tea": ["tea", "green tea", "mate"],
    },
    "fruity": {
        "berry": ["raspberry", "frambinone", "blackberry", "strawberry"],
        "tropical": ["coconut", "mango", "pineapple", "passion fruit"],
        "stone_fruit": ["peach", "apricot", "plum", "aldehyde c-14"],
        "apple_pear": ["apple", "pear", "damascone"],
    },
    "aquatic": {
        "marine": ["marine", "calone", "ozonic", "dihydromyrcenol"],
        "watery": ["watery", "melon", "cucumber"],
    },
    "gourmand": {
        "chocolate": ["chocolate", "cocoa", "cacao"],
        "caramel": ["caramel", "ethyl maltol", "furaneol"],
        "coffee": ["coffee", "furfuryl"],
        "honey": ["honey", "phenylacetic acid", "beeswax"],
    },
    "leather": {
        "smoky_leather": ["leather", "birch tar", "isobutyl quinoline",
                          "suederal"],
        "tobacco": ["tobacco", "coumarin", "tonka"],
    },
}


class OdorOntology:
    """Hierarchical odor classification and semantic search."""

    def __init__(self):
        # Build reverse index: keyword → (family, subfamily)
        self._keyword_index: dict[str, tuple[str, str]] = {}
        for family, subs in ODOR_TREE.items():
            for sub, keywords in subs.items():
                for kw in keywords:
                    self._keyword_index[kw.lower()] = (family, sub)

    def classify_material(self, name: str) -> dict:
        """Classify a material into the odor ontology.

        Returns {family, subfamily, confidence} or None fields if unknown.
        """
        mat = get_materials_db().get(name.lower().strip())
        candidates = []

        if mat:
            # Check odor_family field
            of = (mat.get("odor_family") or "").lower()
            if of:
                for kw, (fam, sub) in self._keyword_index.items():
                    if kw in of or of in kw:
                        candidates.append((fam, sub, "odor_family"))

            # Check odor_profile field
            op = (mat.get("odor_profile") or "").lower()
            if op:
                for kw, (fam, sub) in self._keyword_index.items():
                    if kw in op:
                        candidates.append((fam, sub, "odor_profile"))

            # Check sar_class
            sc = (mat.get("sar_class") or "").lower()
            if sc:
                for kw, (fam, sub) in self._keyword_index.items():
                    if kw in sc:
                        candidates.append((fam, sub, "sar_class"))

        # Check the material name itself
        nl = name.lower()
        for kw, (fam, sub) in self._keyword_index.items():
            if kw in nl or nl in kw:
                candidates.append((fam, sub, "name_match"))

        if not candidates:
            return {"family": None, "subfamily": None, "confidence": 0}

        # Most frequently matched family/subfamily wins
        from collections import Counter
        fam_counts = Counter((f, s) for f, s, _ in candidates)
        (best_fam, best_sub), count = fam_counts.most_common(1)[0]
        conf = min(count / 3, 1.0)  # 3+ matches = full confidence

        return {
            "family": best_fam,
            "subfamily": best_sub,
            "confidence": round(conf, 2),
        }

    def odor_distance(self, name_a: str, name_b: str) -> float:
        """Compute odor distance between two materials. 0=identical, 3=max.

        Distance levels:
          0 — same subfamily
          1 — same family, different subfamily
          2 — different family
          3 — one or both unknown
        """
        ca = self.classify_material(name_a)
        cb = self.classify_material(name_b)

        if ca["family"] is None or cb["family"] is None:
            return 3.0

        if ca["family"] == cb["family"]:
            if ca["subfamily"] == cb["subfamily"]:
                return 0.0
            return 1.0
        return 2.0

    def find_similar(self, name: str, max_results: int = 10) -> list[dict]:
        """Find materials with similar odor profiles.

        Returns list of {name, family, subfamily, distance}.
        """
        db = get_materials_db()
        results = []
        seen = set()

        for key, mat in db.items():
            mat_name = mat.get("name", key)
            if mat_name.lower().strip() == name.lower().strip():
                continue
            if mat_name in seen:
                continue
            seen.add(mat_name)
            dist = self.odor_distance(name, mat_name)
            cls = self.classify_material(mat_name)
            results.append({
                "name": mat_name,
                "family": cls["family"],
                "subfamily": cls["subfamily"],
                "distance": dist,
            })

        results.sort(key=lambda x: x["distance"])
        return results[:max_results]

    def family_members(self, family: str,
                       subfamily: str | None = None) -> list[str]:
        """List all materials belonging to an odor family/subfamily."""
        db = get_materials_db()
        members = []
        seen = set()

        for key, mat in db.items():
            mat_name = mat.get("name", key)
            if mat_name in seen:
                continue
            cls = self.classify_material(mat_name)
            if cls["family"] == family:
                if subfamily is None or cls["subfamily"] == subfamily:
                    members.append(mat_name)
                    seen.add(mat_name)

        return members

    def get_taxonomy(self) -> dict:
        """Return the full odor taxonomy tree for display."""
        return {
            fam: list(subs.keys())
            for fam, subs in ODOR_TREE.items()
        }
