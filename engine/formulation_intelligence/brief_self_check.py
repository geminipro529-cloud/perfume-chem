"""Brief self-check: does a solved formula carry the notes its own brief names?

The composer's critic for choosing among its candidate solves (Phase 3 step 5 of the
composer plan). A note's lead should be that note: a pepper brief's spice lead a pepper,
not cardamom; a vanilla brief's balsam lead the vanilla molecule, not tonka. When the
check finds a lead that misses its note and an owned, design-ready stock is named for
it, the composer solves again with that role asking for such a stock, and keeps
whichever candidate the check scores higher (the first one on a tie).

It reads only the semantic brief the composer compiled from the request and the stocks'
own names and descriptors. No OAV, intensity, pleasantness or liking (AGENTS.md Rule 1),
and no benchmark note lists: the duel's yardstick stays an outside measure.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from engine.formulation_intelligence.family_structure import family_role_words
from engine.formulation_intelligence.formula_solver import (
    FormulaSolveResult,
    _chemical_identity,
    _family_bucket,
)
from engine.formulation_intelligence.material_capability_index import (
    MaterialCapability,
    MaterialCapabilityIndex,
)
from engine.formulation_intelligence.semantic_brief_adapter import (
    ACCORD_SUPPORT_PROVENANCE,
    SemanticBrief,
    SemanticRole,
    _key,
    _phrase_present,
    role_identity_requirement,
)
from engine.research.composition_planner import (
    NOTE_STOCK_WORDS,
    NoteAnchor,
    _avoid_candidate,
    names_note_stock,
)

SCHEMA_VERSION = "brief-self-check-v1"

# Words that name an odor class rather than one note. A lead answers them with any stock
# whose own descriptors carry the word; only a specific note (pepper, vanilla, cedar)
# asks for a stock named for it.
GENERIC_WORDS = frozenset({
    "amber", "ambery", "wood", "woody", "woods", "woody amber", "fruit", "fruity", "floral",
    "flower", "flowers", "musk", "musky", "spice", "spicy", "green", "citrus", "creamy",
    "powder", "powdery", "fresh", "sweet", "warm", "resin", "resinous", "balsam", "balsamic",
    "smoke", "smoky", "aromatic", "herbal", "earthy", "aquatic", "marine", "gourmand",
    "animalic", "mineral", "leather", "suede", "root", "leaf", "petal", "petals", "dry",
})

# A brief word and the stock-name words that carry it: stocks are named "Cedarwood
# Virginia" and "Guaiacwood EO" (family_structure.py); vanilla's molecule is vanillin;
# an orris or irone stock is the iris (the solver's own iris rule); oud is agarwood.
WORD_EQUIVALENTS: Mapping[str, tuple[str, ...]] = {
    "cedar": ("cedarwood",),
    "sandal": ("sandalwood",),
    "guaiac": ("guaiacwood",),
    "vanilla": ("vanillin",),
    "iris": ("orris", "irone"),
    "orris": ("iris", "irone"),
    "oud": ("agarwood",),
}

# Weights of the check's parts: each lead carries its note, every note the brief names
# is carried by some stock, the family's own materials found a place.
WEIGHTS = {"lead_fidelity": .55, "word_coverage": .35, "family_coverage": .10}
# Owned stocks named for an uncovered note that are not design ready, listed per word.
_HELD_LISTED = 3
# Owned stocks offered to a capsule role for a note it left out, best first.
_NOTE_STOCKS_LISTED = 6


def _specific(word: str) -> bool:
    return _key(word) not in GENERIC_WORDS


def carries(capability: MaterialCapability, word: str) -> str | None:
    """``identity`` when the stock's own name carries the word, ``descriptor`` when only
    its own odor descriptors do, else None."""
    tokens = set(_key(word).split())
    if not tokens:
        return None
    identity = set(capability.identity_vocabulary)
    equivalents = set(WORD_EQUIVALENTS.get(_key(word), ()))
    if tokens <= identity or equivalents & identity:
        return "identity"
    if tokens <= set(capability.descriptor_vocabulary):
        return "descriptor"
    return None


def brief_words(role: SemanticRole, request_key: str) -> tuple[str, ...]:
    """The role's query words the request itself uses."""
    return tuple(term for term in role.query_terms if _phrase_present(request_key, term))


def _required_words(words: Sequence[str]) -> tuple[str, ...]:
    """Words a repaired role's stock name should carry: each note's head word (the
    "pepper" of "pink pepper") and its stock-name equivalents."""
    result: list[str] = []
    for word in words:
        key = _key(word)
        if key:
            result.extend((key.split()[-1], *WORD_EQUIVALENTS.get(key, ())))
    return tuple(dict.fromkeys(result))


@dataclass(frozen=True, slots=True)
class LeadDefect:
    role_id: str
    words: tuple[str, ...]
    stock: str


@dataclass(frozen=True, slots=True)
class BriefSelfCheck:
    score: float
    lead_fidelity: float
    word_coverage: float
    family_coverage: float
    lead_defects: tuple[LeadDefect, ...]
    uncovered_words: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "lead_fidelity": round(self.lead_fidelity, 4),
            "word_coverage": round(self.word_coverage, 4),
            "family_coverage": round(self.family_coverage, 4),
            "lead_defects": [
                {"role_id": d.role_id, "words": list(d.words), "stock": d.stock}
                for d in self.lead_defects
            ],
            "uncovered_words": list(self.uncovered_words),
        }


def _lead_score(role: SemanticRole, capability: MaterialCapability, request: str,
                words: Sequence[str]) -> float:
    required = role_identity_requirement(role.role_id, request)
    if required and set(required) & set(capability.identity_vocabulary):
        return 1.0
    specific = [word for word in words if _specific(word)]
    kinds = [carries(capability, word) for word in words]
    if specific:
        if any(carries(capability, word) == "identity" for word in specific):
            return 1.0
    elif any(kinds):
        return 1.0
    return .5 if any(kinds) else 0.0


def check_solve(brief: SemanticBrief, solve: FormulaSolveResult) -> BriefSelfCheck | None:
    """Score a solved formula against its brief; None for a withheld solve."""
    if solve.status != "SOLVED":
        return None
    request_key = f" {_key(brief.normalized_request)} "
    leads: list[float] = []
    defects: list[LeadDefect] = []
    named: dict[str, None] = {}
    for assignment in solve.assignments:
        role = assignment.role
        if role.provenance != "PROMPT_DERIVED_FACET" or role.exact_material is not None:
            continue
        words = brief_words(role, request_key)
        if not words:
            continue
        named.update(dict.fromkeys(word for word in words if _specific(word)))
        score = _lead_score(role, assignment.capability, brief.normalized_request, words)
        leads.append(score)
        if score < 1:
            defects.append(LeadDefect(role.role_id, words, assignment.capability.identity_name))
    named.update(dict.fromkeys((*brief.requested_fruits, *brief.unmapped_requested_notes)))
    capabilities = [assignment.capability for assignment in solve.assignments]
    uncovered = tuple(word for word in named if not any(carries(c, word) for c in capabilities))
    family_roles = [role.role_id for role in brief.roles if family_role_words(role.role_id)]
    placed = {assignment.role.role_id for assignment in solve.assignments}
    parts = {
        "lead_fidelity": sum(leads) / len(leads) if leads else 1.0,
        "word_coverage": 1 - len(uncovered) / len(named) if named else 1.0,
        "family_coverage": (
            sum(role_id in placed for role_id in family_roles) / len(family_roles)
            if family_roles else 1.0
        ),
    }
    return BriefSelfCheck(
        score=sum(WEIGHTS[name] * value for name, value in parts.items()),
        **parts,
        lead_defects=tuple(defects),
        uncovered_words=uncovered,
    )


def repair_targets(
    brief: SemanticBrief,
    solve: FormulaSolveResult,
    check: BriefSelfCheck,
    index: MaterialCapabilityIndex,
    avoid: Sequence[str],
) -> dict[str, tuple[str, ...]]:
    """Roles worth solving again, each with the words its stock's name should carry.

    A lead that misses its specific note, and an accord support of the same note when
    the brief's word is carried by no stock at all, but only when an owned design-ready
    stock named for the word could take the place: not avoided, not already in the
    formula, not a second stock of a wood or flower family another role holds.
    """
    request_key = f" {_key(brief.normalized_request)} "
    placed = {_chemical_identity(a.capability) for a in solve.assignments}

    def fixable(role_id: str, words: Sequence[str]) -> bool:
        held = {
            _family_bucket(a.capability) for a in solve.assignments if a.role.role_id != role_id
        } - {None, "citrus", "musk"}
        return any(
            capability.design_ready
            and not _avoid_candidate(capability.candidate, avoid)
            and _chemical_identity(capability) not in placed
            and _family_bucket(capability) not in held
            and any(carries(capability, word) == "identity" for word in words)
            for capability in index.capabilities
        )

    targets: dict[str, tuple[str, ...]] = {}
    for defect in check.lead_defects:
        words = tuple(word for word in defect.words if _specific(word))
        if words and fixable(defect.role_id, words):
            targets[defect.role_id] = _required_words(words)
    for word in check.uncovered_words:
        if not _specific(word):
            continue
        for assignment in solve.assignments:
            role = assignment.role
            if (
                role.provenance != ACCORD_SUPPORT_PROVENANCE
                or role.role_id in targets
                or _key(word) not in {_key(term) for term in role.query_terms}
                or any(
                    carries(assignment.capability, other)
                    for other in brief_words(role, request_key) if _specific(other)
                )
            ):
                continue
            if fixable(role.role_id, (word,)):
                targets[role.role_id] = _required_words((word,))
                break
    return targets


def held_carriers(index: MaterialCapabilityIndex, words: Sequence[str]) -> dict[str, list[str]]:
    """For each uncovered word, owned stocks named for it that are not design ready
    (their details are completed on the Lab's Stock page)."""
    result: dict[str, list[str]] = {}
    for word in words:
        names = sorted({
            c.identity_name for c in index.capabilities
            if not c.design_ready and carries(c, word) == "identity"
        })
        if names:
            result[word] = names[:_HELD_LISTED]
    return result


def _note_words(role: SemanticRole, request_key: str) -> tuple[str, ...]:
    """The request's words for a facet role's note; "mossy", "musky" and "resinous"
    say the note with a suffix, so a query term may start a request word (both the
    term and the word are kept: a stock may describe itself either way)."""
    words = brief_words(role, request_key)
    if words:
        return words
    found: list[str] = []
    for term in role.query_terms:
        key = _key(term)
        match = re.search(rf"(?:^| )({re.escape(key)}[a-z]*)(?= |$)", request_key) if key else None
        if match:
            found.extend((key, match.group(1)))
    return tuple(dict.fromkeys(found))


def _carries_note(capability: MaterialCapability, role: SemanticRole, request: str,
                  words: Sequence[str]) -> str | None:
    """``identity`` or ``descriptor`` when the stock carries the note; a note with an
    identity requirement (oud is agarwood, iris is orris or irone) only by name."""
    required = role_identity_requirement(role.role_id, request)
    if required:
        return "identity" if set(required) & set(capability.identity_vocabulary) else None
    if any(names_note_stock(capability.candidate, word) for word in words):
        return "identity"
    kinds = {carries(capability, word) for word in words}
    return "identity" if "identity" in kinds else "descriptor" if "descriptor" in kinds else None


def _note_stock_rank(capability: MaterialCapability, words: Sequence[str]) -> int:
    """Position of the first of the note's stock words the stock is named for: an
    incense is olibanum before myrrh (NOTE_STOCK_WORDS lists them in that order)."""
    probe = f" {_key(capability.identity_name)}"
    for word in words:
        for rank, stock_word in enumerate(NOTE_STOCK_WORDS.get(_key(word), ())):
            if f" {stock_word}" in probe:
                return rank
    return len(NOTE_STOCK_WORDS)


def capsule_note_gaps(
    brief: SemanticBrief,
    placed: Sequence[MaterialCapability],
    index: MaterialCapabilityIndex,
    avoid: Sequence[str],
    concept_words: Sequence[str] = (),
) -> tuple[NoteAnchor, ...]:
    """Notes the brief names that no placed stock leads, each with the owned stocks
    that would lead it, best first.

    A curated capsule (composition_planner) fills its own roles and never reads the
    brief's note words, so "an oud and incense skin scent" lost its oud and incense.
    ``concept_words`` are the capsule's own trigger words ("skin scent"): the capsule
    is that note. A stock carries a note by its own name or descriptors; stocks
    named for it come first.
    """
    request = brief.normalized_request
    request_key = f" {_key(request)} "
    concept_tokens = {token for word in concept_words for token in _key(word).split()}
    placed_ids = {_chemical_identity(capability) for capability in placed}
    gaps: list[NoteAnchor] = []
    for role in brief.roles:
        if role.provenance != "PROMPT_DERIVED_FACET" or role.exact_material is not None:
            continue
        words = tuple(
            word for word in _note_words(role, request_key)
            if not set(_key(word).split()) <= concept_tokens
        )
        if not words or any(_carries_note(c, role, request, words) for c in placed):
            continue
        leads = sorted(
            (
                c for c in index.capabilities
                if c.design_ready
                and _chemical_identity(c) not in placed_ids
                and not _avoid_candidate(c.candidate, avoid)
                and _carries_note(c, role, request, words)
            ),
            key=lambda c: (
                _carries_note(c, role, request, words) != "identity",
                _note_stock_rank(c, words),
                -sum(carries(c, term) is not None for term in role.query_terms),
                c.identity_name.casefold(),
                c.stock_id,
            ),
        )
        held = held_carriers(index, words)
        gaps.append(NoteAnchor(
            word=words[0],
            stocks=tuple(dict.fromkeys(c.identity_name for c in leads))[:_NOTE_STOCKS_LISTED],
            note=role.note,
            function=role.function,
            share=role.share,
            max_raw_share=role.max_raw_share,
            held=tuple(dict.fromkeys(name for names in held.values() for name in names)),
        ))
    return tuple(gaps)


def best_of_solves(
    *,
    brief: SemanticBrief,
    index: MaterialCapabilityIndex,
    avoid: Sequence[str],
    solve: Callable[[Mapping[str, tuple[str, ...]] | None], FormulaSolveResult],
) -> FormulaSolveResult:
    """Solve, check, repair, and return the candidate the check scores highest.

    ``solve(identity_words)`` solves the brief with those role identity words (None for
    the composer's own first solve). The returned solve's receipt carries the check
    (``self_check``). A first solve that is withheld is returned unchanged.
    """
    primary = solve(None)
    first = check_solve(brief, primary)
    if first is None:
        return primary
    targets = repair_targets(brief, primary, first, index, avoid)
    candidates: list[tuple[str, Mapping[str, tuple[str, ...]], FormulaSolveResult, BriefSelfCheck]] = [
        ("primary", {}, primary, first),
    ]
    tries = [(f"repair:{role_id}", {role_id: words}) for role_id, words in targets.items()]
    if len(targets) > 1:
        tries.append(("repair:all", dict(targets)))
    for label, words in tries:
        candidate = solve(words)
        check = check_solve(brief, candidate)
        if check is not None:
            candidates.append((label, words, candidate, check))
    best = max(range(len(candidates)), key=lambda i: (candidates[i][3].score, -i))
    label, _words, chosen, check = candidates[best]
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "policy": "BRIEF_WORDS_AND_STOCK_NAMES_ONLY_NO_OAV_V1",
        "candidates": [
            {"label": name, "score": round(c.score, 4),
             "identity_requirements": {k: list(v) for k, v in sorted(w.items())}}
            for name, w, _solve, c in candidates
        ],
        "repairs_withheld": [name for name, _w in tries
                             if name not in {c[0] for c in candidates}],
        "picked": label,
        "check": check.as_dict(),
        "held_carriers": held_carriers(index, check.uncovered_words),
    }
    return replace(chosen, solver_receipt={**chosen.solver_receipt, "self_check": receipt})


__all__ = [
    "BriefSelfCheck",
    "GENERIC_WORDS",
    "LeadDefect",
    "WORD_EQUIVALENTS",
    "best_of_solves",
    "brief_words",
    "capsule_note_gaps",
    "carries",
    "check_solve",
    "held_carriers",
    "repair_targets",
]
