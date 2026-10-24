"""Read French perfume-note words in a formula name or brief as their English notes.

Formula names are often French ("Baie Rose Homme", "Lavande Ambre Profond").
The brief compiler matches English note words, so "Baie Rose" (pink pepper)
read as a rose and "Lavande" read as nothing. This module rewrites only whole
note phrases, for reading; the user's own text is kept wherever it is shown.
A French word that is also an English word with another meaning (citron, the
cedrat fruit) is left alone.
"""

from __future__ import annotations

import re

# Longer phrases first: "bois de rose" must win over "rose"-free "bois", and
# "baie rose" must be read before anything could see its "rose".
_PHRASES: tuple[tuple[str, str], ...] = (
    (r"baies?\s+roses?", "pink pepper"),
    (r"poivre\s+rose", "pink pepper"),
    (r"poivre\s+noir", "black pepper"),
    (r"fleurs?\s+d['’]\s*oranger", "orange blossom"),
    (r"bois\s+de\s+santal", "sandalwood"),
    (r"bois\s+de\s+c[eèé]dre", "cedarwood"),
    (r"bois\s+de\s+rose", "rosewood"),
    (r"mousse\s+de\s+ch[eê]ne", "oakmoss"),
    (r"f[eè]ve\s+tonka", "tonka bean"),
    (r"noix\s+de\s+coco", "coconut"),
    (r"santal", "sandalwood"),
    (r"c[eè]dre", "cedar"),
    (r"lavande", "lavender"),
    (r"violettes?", "violet"),
    (r"ambr[eé]e?s?", "amber"),
    (r"cuirs?", "leather"),
    (r"vanille", "vanilla"),
    (r"tub[eé]reuses?", "tuberose"),
    (r"encens", "incense"),
    (r"tabac", "tobacco"),
    (r"figues?", "fig"),
    (r"poires?", "pear"),
    (r"pommes?", "apple"),
    (r"abricots?", "apricot"),
    (r"p[eê]ches?", "peach"),
    (r"framboises?", "raspberry"),
    (r"cerises?", "cherry"),
    # Family and citrus words: the reading drops accented letters, so
    # "fougère" read as no family at all.
    (r"foug[eè]res?", "fougere"),
    (r"agrumes?", "citrus"),
    (r"hesp[eé]rid[eé]e?s?", "citrus"),
    (r"c[eé]drats?", "cedrat"),
    (r"cl[eé]mentines?", "clementine"),
    (r"pom[eé]los?", "pomelo"),
    (r"zestes?", "zest"),
    (r"bergamote", "bergamot"),
    (r"pamplemousse", "grapefruit"),
    (r"mandarine", "mandarin"),
    (r"n[eé]roli", "neroli"),
    (r"muguet", "lily of the valley"),
)
_COMPILED = tuple(
    (re.compile(rf"(?<!\w){pattern}(?!\w)", re.I), english) for pattern, english in _PHRASES
)


def translate_note_phrases(text: str) -> str:
    """Return ``text`` with French note phrases replaced by their English notes."""
    out = str(text or "")
    for pattern, english in _COMPILED:
        out = pattern.sub(english, out)
    return out
