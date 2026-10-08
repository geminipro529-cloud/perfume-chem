"""Deterministic, authority-safe interpretation of perfume change requests.

The interpreter protects explicit facts (materials, quantities, units,
direction, timing, preserve/avoid clauses, execution strategy, and reference
intent).  It is intentionally not a generative model and never commits a
physical action.  Soft descriptor interpretation remains advisory and may be
challenged by a separately governed semantic capability later.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Literal, Sequence

from .contracts import FALSE_ACTION_AUTHORITY, stable_payload_hash

ExecutionStrategy = Literal["NEW_FORMULA", "EVOLVING_BOTTLE"]
AppealMode = Literal["IDENTITY_FIRST", "GLOBAL_CROWD_PLEASING"]
ComparisonEvidence = Literal[
    "DOCUMENT_ONLY",
    "QUICK_BLIND",
    "CONTROLLED_PERSONAL",
    "TARGET_POPULATION",
]

_EXECUTION_STRATEGIES = {"NEW_FORMULA", "EVOLVING_BOTTLE"}
_APPEAL_MODES = {"IDENTITY_FIRST", "GLOBAL_CROWD_PLEASING"}
_COMPARISON_EVIDENCE = {
    "DOCUMENT_ONLY",
    "QUICK_BLIND",
    "CONTROLLED_PERSONAL",
    "TARGET_POPULATION",
}
_UNITS = {"uL", "mL", "mg", "g"}
_COUNT_WORDS = {
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
}
_COUNT_TOKEN = r"\d+|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty"

_EVOLVING_RE = re.compile(
    r"\b(?:current|existing|same|this)\s+bottle\b|\badd\s+(?:it|this|that)\s+to\b",
    re.I,
)
_NEW_FORMULA_RE = re.compile(r"\b(?:new|separate|fresh)\s+(?:formula|bottle|batch)\b", re.I)
_GLOBAL_RE = re.compile(
    r"\b(?:global\s+crowd[- ]?pleasing|crowd[- ]?pleasing|"
    r"global\s+(?:mass[- ]?market|market|appeal)|mass[- ]?market|bestseller|"
    r"successful\s+(?:prestige\s+)?perfumes?|"
    r"commercial\s+(?:reference|comparison|appeal))\b",
    re.I,
)
_IDENTITY_RE = re.compile(r"\bidentity[- ]?first\b|\bpreserve\s+(?:the\s+)?identity\b", re.I)
_DIRECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("DECREASE", re.compile(r"\b(?:less|reduce|decrease|weaken|soften|mute|remove|cut)\b", re.I)),
    ("INCREASE", re.compile(r"\b(?:more|increase|boost|stronger|raise|add|clearer|brighter)\b", re.I)),
)
_NEGATED_INCREASE_RE = re.compile(
    r"\b(?:do\s+not|don't|not\s+to|avoid)\s+(?:make\s+(?:it\s+)?|become\s+)?"
    r"(?:more|increase|boost|raise|strengthen|add)\b|\bnot\s+more\b",
    re.I,
)
_NEGATED_DECREASE_RE = re.compile(
    r"\b(?:do\s+not|don't|not\s+to|avoid)\s+(?:make\s+(?:it\s+)?|become\s+)?"
    r"(?:less|reduce|decrease|weaken|mute|remove|cut)\b|\bnot\s+less\b",
    re.I,
)
_WINDOWS: tuple[tuple[str, int | None, re.Pattern[str]], ...] = (
    ("OPENING", 0, re.compile(r"\b(?:opening|first\s+blast|initial)\b", re.I)),
    ("FIVE_MINUTES", 300, re.compile(r"\b(?:5|five)[-\s]*(?:m|min|mins|minute|minutes)\b", re.I)),
    ("THIRTY_MINUTES", 1800, re.compile(r"\b(?:30|thirty)[-\s]*(?:m|min|mins|minute|minutes)\b", re.I)),
    ("TWO_HOURS", 7200, re.compile(r"\b(?:2|two)[-\s]*(?:h|hr|hrs|hour|hours)\b", re.I)),
    ("FOUR_HOURS", 14400, re.compile(r"\b(?:4|four)[-\s]*(?:h|hr|hrs|hour|hours)\b", re.I)),
    ("HEART", None, re.compile(r"\b(?:heart|mid|middle)\b", re.I)),
    ("DRYDOWN", None, re.compile(r"\b(?:drydown|dry-down|dry\s+down|late\s+stage)\b", re.I)),
)
_QUANTITY_RE = re.compile(
    r"(?<![\w.])(?P<amount>\d+(?:\.\d+)?)\s*"
    # NFKC turns the MICRO SIGN (U+00B5) into GREEK SMALL LETTER MU
    # (U+03BC).  Accept both spellings so callers may normalize prose before
    # request interpretation without making an exact quantity disappear.
    r"(?P<unit>uL|µL|μL|mL|mg|g|microlitres?|microliters?|millilitres?|"
    r"milliliters?|milligrams?|grams?)\b",
    re.I,
)
_PRESERVE_RE = re.compile(
    r"\b(?:preserve|keep|do\s+not\s+change)\s+(?P<value>[^,.;]+?)(?=\s+(?:while|but|and\s+avoid|without)\b|[,.;]|$)",
    re.I,
)
_AVOID_RE = re.compile(
    r"\b(?:avoid|without|do\s+not\s+(?:add|use)|must\s+not\s+contain|"
    r"must\s+contain\s+no|containing\s+no|use\s+no)\s+"
    r"(?P<value>[^.;]+?)(?=\s+(?:while|but|and\s+preserve|and\s+must)\b|[.;]|$)",
    re.I,
)
_SHORT_NO_RE = re.compile(
    r"(?:^|[.;]\s*)no\s+(?P<value>[^.;]+?)(?=[.;]|$)",
    re.I,
)
_INLINE_NO_RE = re.compile(
    r"\bno\s+(?P<value>[^.;]+?)(?=[.;]|$)",
    re.I,
)
_MANDATORY_RE = re.compile(
    r"\b(?:mandatory|required|must\s+(?:use|contain|include)|using\s+(?:exactly|all)|"
    r"use\s+exactly)\b",
    re.I,
)
_SIMULTANEOUS_RE = re.compile(
    r"\b(?:at\s+the\s+same\s+time|while\s+also|simultaneously|one\s+uniform)\b",
    re.I,
)
_OPPOSED_REQUIREMENTS: tuple[tuple[re.Pattern[str], re.Pattern[str]], ...] = (
    (
        re.compile(r"\b(?:intensely\s+hot|very\s+hot|strongly\s+warm)\b", re.I),
        re.compile(r"\b(?:completely\s+cold|intensely\s+cold|very\s+cold)\b", re.I),
    ),
    (
        re.compile(r"\b(?:very\s+sweet|intensely\s+sweet|intensely\s+sugary|caramel[- ]heavy|edible)\b", re.I),
        re.compile(r"\b(?:completely\s+unsweetened|unsweetened|non[- ]gourmand|no\s+sweet[- ]smelling)\b", re.I),
    ),
)
_MATERIAL_ALIASES = {
    "nagarmotha oil": "Nagarmortha Oil",
    "crystal ambrox": "Ambrox Super Crystals",
    "ambrox crystals": "Ambrox Super Crystals",
    "lavender": "Lavender EO (BONTAUX SAS)",
    "grapefruit": "Grapefruit FCF Oil Sicilian",
    "cedar": "Cedarwood Virginia",
    "vetiver": "Vetiver EO (Haiti)",
    "patchouli": "Patchouli EO",
    "frankincense": "Olibanum Resinoid",
    "coffee": "Coffee Absolute Grasse",
    "cocoa": "Cocoa Absolute",
    "cardamom": "Cardamom EO",
}


def _text(value: object, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field} must be non-empty text")
    return text


def _dedupe(values: Iterable[object]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        key = " ".join(text.casefold().split())
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return tuple(result)


def _enum(value: str, allowed: set[str], field: str) -> str:
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    if normalized not in allowed:
        raise ValueError(f"unsupported {field}: {value}")
    return normalized


def _direction(text: str) -> str:
    negated_increase = bool(_NEGATED_INCREASE_RE.search(text))
    negated_decrease = bool(_NEGATED_DECREASE_RE.search(text))
    scrubbed = _NEGATED_INCREASE_RE.sub(" ", text)
    scrubbed = _NEGATED_DECREASE_RE.sub(" ", scrubbed)
    # In an evolving-bottle request, "add one nonnegative delta to make it
    # less X" describes the physical operation, not an increase in X.
    scrubbed = re.sub(
        r"\badd\s+(?:one\s+)?(?:small\s+)?(?:nonnegative\s+)?delta\b",
        " ",
        scrubbed,
        flags=re.I,
    )
    matches = {
        direction
        for direction, pattern in _DIRECTION_PATTERNS
        if pattern.search(scrubbed)
    }
    if negated_increase and negated_decrease:
        return "CONTRADICTORY"
    if negated_increase and not matches:
        return "PRESERVE_OR_DECREASE"
    if negated_decrease and not matches:
        return "PRESERVE_OR_INCREASE"
    if len(matches) > 1:
        return "CONTRADICTORY"
    return next(iter(matches), "UNSPECIFIED")


def positive_reference_text(text: str) -> str:
    """Exclude explicitly avoided clauses from documentary reference matching."""
    _values, spans = _avoid_values_and_spans(text)
    return _masked_text(text, spans)


def _matched_names(text: str, names: Sequence[str]) -> tuple[str, ...]:
    # Longest-first span claiming prevents a short identity (for example
    # ``Ambrox Super``) from duplicating an exact product/form mention (for
    # example ``Ambrox Super Crystals``) at the same text position.
    claimed: list[tuple[int, int]] = []
    matched: list[str] = []
    for name in sorted(names, key=lambda item: (-len(item), item.casefold())):
        hits = tuple(re.finditer(rf"(?<!\w){re.escape(name)}(?!\w)", text, re.I))
        accepted = False
        for hit in hits:
            span = hit.span()
            if any(span[0] < end and start < span[1] for start, end in claimed):
                continue
            claimed.append(span)
            accepted = True
        if accepted:
            matched.append(name)
    known_by_key = {name.casefold(): name for name in names}
    for alias, canonical in _MATERIAL_ALIASES.items():
        if not re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text, re.I):
            continue
        actual = known_by_key.get(canonical.casefold())
        if actual is not None:
            matched.append(actual)
    return _dedupe(matched)


def _split_constraint_values(value: str) -> tuple[str, ...]:
    """Split an avoid list without destroying a single descriptive phrase."""

    clean = re.sub(r"\s+", " ", value).strip(" ,")
    if not clean:
        return ()
    if "," not in clean and not re.search(r"\s+(?:or|nor)\s+", clean, re.I):
        return (clean,)
    return _dedupe(
        re.sub(r"^(?:and|or|nor|any)\s+", "", part.strip(), flags=re.I)
        for part in re.split(r"\s*,\s*|\s+(?:or|nor)\s+", clean, flags=re.I)
    )


def _avoid_values_and_spans(text: str) -> tuple[tuple[str, ...], tuple[tuple[int, int], ...]]:
    values: list[str] = []
    spans: list[tuple[int, int]] = []
    for pattern in (_AVOID_RE, _SHORT_NO_RE, _INLINE_NO_RE):
        for match in pattern.finditer(text):
            if re.match(
                r"\s*(?:more\s+than|less\s+than|fewer\s+than|longer\b|later\b)",
                match.group("value"),
                re.I,
            ):
                continue
            values.extend(_split_constraint_values(match.group("value")))
            spans.append(match.span())
    # Common prose negation that is not naturally introduced by "avoid".
    for match in re.finditer(
        r"\bnot\s+(?P<value>sweet|sporty|edible|perfumey|detergent(?:-like)?|"
        r"sugary|romantic(?:ally)?\s+sweet)\b",
        text,
        re.I,
    ):
        values.append(match.group("value"))
        spans.append(match.span())
    return _dedupe(values), tuple(spans)


def _masked_text(text: str, spans: Sequence[tuple[int, int]]) -> str:
    chars = list(text)
    for start, end in spans:
        chars[start:end] = " " * (end - start)
    return "".join(chars)


def _material_key(value: str) -> str:
    return re.sub(
        r"\b(?:material|stock|solution|crystals?|neat|owned|the|any)\b",
        " ",
        re.sub(r"[^a-z0-9]+", " ", value.casefold()),
    ).strip()


def _constraints_overlap(required: Sequence[str], prohibited: Sequence[str]) -> bool:
    prohibited_rows = [(value, _material_key(value)) for value in prohibited]
    for value in required:
        required_key = _material_key(value)
        if not required_key:
            continue
        for prohibited_value, prohibited_key in prohibited_rows:
            if not prohibited_key:
                continue
            required_is_solid = any(word in value.casefold() for word in ("crystal", "solid", "powder"))
            prohibited_is_solution = "solution" in prohibited_value.casefold()
            required_is_solution = "solution" in value.casefold()
            prohibited_is_solid = any(
                word in prohibited_value.casefold()
                for word in ("crystal", "solid", "powder")
            )
            prohibited_has_form = any(
                word in prohibited_value.casefold()
                for word in ("neat", "solution", "crystal", "solid", "powder", "dilution")
            )
            required_has_form = any(
                word in value.casefold()
                for word in ("neat", "solution", "crystal", "solid", "powder", "dilution")
            )
            if prohibited_has_form and not required_has_form:
                continue
            if (required_is_solid and prohibited_is_solution) or (
                required_is_solution and prohibited_is_solid
            ):
                continue
            # A broader identity ban (``Ambrox material`` -> ``ambrox``) may
            # conflict with a specific product (``Ambrox Super``).  A longer
            # sensory phrase containing the name (``sweet coumarin cloud``)
            # does not prohibit the chemical itself.
            if required_key == prohibited_key or prohibited_key in required_key:
                return True
    return False


def _exact_prohibited_names(
    values: Sequence[str], names: Sequence[str]
) -> tuple[str, ...]:
    """Return identity bans, excluding requests that only constrain a facet."""

    allowed_extra = {
        "any",
        "material",
        "stock",
        "solution",
        "neat",
        "crystal",
        "crystals",
        "solid",
        "powder",
        "the",
    }
    result: list[str] = []
    for value in values:
        value_tokens = set(_material_key(value).split())
        for name in _matched_names(value, names):
            name_tokens = set(_material_key(name).split())
            if name_tokens and value_tokens - name_tokens <= allowed_extra:
                result.append(name)
    return _dedupe(result)


def _mandatory_materials(text: str, materials: Sequence[str]) -> tuple[str, ...]:
    required: list[str] = []
    for marker in _MANDATORY_RE.finditer(text):
        sentence_start = max(
            text.rfind(".", 0, marker.start()),
            text.rfind(";", 0, marker.start()),
            0,
        )
        sentence_end_candidates = [
            position
            for position in (text.find(".", marker.end()), text.find(";", marker.end()))
            if position >= 0
        ]
        sentence_end = min(sentence_end_candidates, default=len(text))
        required.extend(_matched_names(text[sentence_start:sentence_end], materials))
    lowered = text.casefold()
    for alias, canonical in _MATERIAL_ALIASES.items():
        start = lowered.find(alias)
        if start >= 0 and _MANDATORY_RE.search(text[max(0, start - 80) : start + len(alias) + 40]):
            required.append(canonical)
    return _dedupe(required)


def _quantities(text: str, materials: Sequence[str]) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for match in _QUANTITY_RE.finditer(text):
        try:
            amount = Decimal(match.group("amount"))
        except InvalidOperation as exc:  # pragma: no cover - regex already constrains syntax
            raise ValueError("quantity must be a finite decimal") from exc
        if not amount.is_finite() or amount <= 0:
            raise ValueError("quantity must be finite and greater than zero")
        unit_raw = match.group("unit")
        unit = {
            "ul": "uL",
            "µl": "uL",
            "μl": "uL",
            "microlitre": "uL",
            "microlitres": "uL",
            "microliter": "uL",
            "microliters": "uL",
            "ml": "mL",
            "millilitre": "mL",
            "millilitres": "mL",
            "milliliter": "mL",
            "milliliters": "mL",
            "mg": "mg",
            "milligram": "mg",
            "milligrams": "mg",
            "g": "g",
            "gram": "g",
            "grams": "g",
        }[unit_raw.casefold()]
        if unit not in _UNITS:
            raise ValueError(f"unsupported quantity unit: {unit}")
        context_start = max(0, match.start() - 120)
        context_end = min(len(text), match.end() + 120)
        nearby = text[context_start:context_end]
        matched = _matched_names(nearby, materials)
        material: str | None = None
        if matched:
            def distance(name: str) -> tuple[int, int, str]:
                positions = [
                    hit.start()
                    for hit in re.finditer(re.escape(name), nearby, re.I)
                ]
                closest = min(
                    (abs((context_start + position) - match.start()) for position in positions),
                    default=10_000,
                )
                return (closest, -len(name), name.casefold())

            material = min(matched, key=distance)
        immediate_before = text[max(0, match.start() - 64) : match.start()]
        immediate_after = text[match.end() : min(len(text), match.end() + 40)]
        total_scope = bool(
            re.search(
                r"(?:keep\s+(?:the\s+)?|total\s+)?(?:liquid\s+concentrate|"
                r"concentrate\s+total|liquid\s+total)\s+(?:at\s+|exactly\s+)?$",
                immediate_before,
                re.I,
            )
            or re.match(
                r"\s*(?:of\s+)?(?:total\s+)?(?:liquid\s+concentrate|"
                r"concentrate\s+total|liquid\s+total)\b",
                immediate_after,
                re.I,
            )
        )
        rows.append(
            {
                "amount_decimal": format(amount, "f").rstrip("0").rstrip(".")
                if "." in format(amount, "f")
                else format(amount, "f"),
                "unit": unit,
                "material": None if total_scope else material,
                "source_text": match.group(0),
                "scope": "LIQUID_TOTAL" if total_scope else "MATERIAL_DOSE",
            }
        )
    return tuple(rows)


def _material_count_constraints(text: str) -> tuple[dict[str, Any], ...]:
    """Extract exact/minimum/maximum row-count constraints from the brief."""

    range_patterns = (
        re.compile(
            rf"\b(?P<minimum>{_COUNT_TOKEN})\s*(?:-|–|—|to|through)\s*"
            rf"(?P<maximum>{_COUNT_TOKEN})\s+materials?\b",
            re.I,
        ),
        re.compile(
            rf"\bbetween\s+(?P<minimum>{_COUNT_TOKEN})\s+and\s+"
            rf"(?P<maximum>{_COUNT_TOKEN})\s+materials?\b",
            re.I,
        ),
    )
    patterns = (
        (
            "EXACT",
            re.compile(
                rf"\b(?:exactly\s+)?(?P<count>{_COUNT_TOKEN})[-\s]+materials?\b",
                re.I,
            ),
        ),
        (
            "EXACT",
            re.compile(
                rf"\bin\s+(?P<count>{_COUNT_TOKEN})\s+materials?\b",
                re.I,
            ),
        ),
        (
            "MINIMUM",
            re.compile(
                rf"\b(?:at\s+least|minimum(?:\s+of)?)\s+(?P<count>{_COUNT_TOKEN})\s+materials?\b",
                re.I,
            ),
        ),
        (
            "MAXIMUM",
            re.compile(
                rf"\b(?:at\s+most|maximum(?:\s+of)?|up\s+to|no\s+more\s+than)\s+"
                rf"(?P<count>{_COUNT_TOKEN})\s+materials?\b",
                re.I,
            ),
        ),
        (
            "MAXIMUM",
            re.compile(
                rf"\bunder\s+(?:a\s+)?(?P<count>{_COUNT_TOKEN})[-\s]+material\s+ceiling\b",
                re.I,
            ),
        ),
    )
    rows: list[dict[str, Any]] = []
    claimed: list[tuple[int, int]] = []
    for pattern in range_patterns:
        for match in pattern.finditer(text):
            if any(match.start() < end and start < match.end() for start, end in claimed):
                continue
            minimum_token = match.group("minimum").casefold()
            maximum_token = match.group("maximum").casefold()
            minimum = (
                int(minimum_token)
                if minimum_token.isdigit()
                else _COUNT_WORDS[minimum_token]
            )
            maximum = (
                int(maximum_token)
                if maximum_token.isdigit()
                else _COUNT_WORDS[maximum_token]
            )
            source_text = match.group(0)
            rows.extend(
                (
                    {
                        "kind": "MINIMUM",
                        "count": minimum,
                        "source_text": source_text,
                    },
                    {
                        "kind": "MAXIMUM",
                        "count": maximum,
                        "source_text": source_text,
                    },
                )
            )
            claimed.append(match.span())
    # More explicit minimum/maximum patterns claim their spans before the
    # general ``N-material`` expression can classify them as exact.
    for kind, pattern in (*patterns[2:], *patterns[:2]):
        for match in pattern.finditer(text):
            if any(match.start() < end and start < match.end() for start, end in claimed):
                continue
            token = match.group("count").casefold()
            count = int(token) if token.isdigit() else _COUNT_WORDS[token]
            rows.append(
                {
                    "kind": kind,
                    "count": count,
                    "source_text": match.group(0),
                }
            )
            claimed.append(match.span())
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class RequestInterpretationInputV1:
    original_request: str
    known_materials: tuple[str, ...] = ()
    known_references: tuple[str, ...] = ()
    desired_changes: tuple[str, ...] = ()
    must_preserve: tuple[str, ...] = ()
    must_avoid: tuple[str, ...] = ()
    evaluation_windows: tuple[str, ...] = ()
    execution_strategy: str | None = None
    appeal_mode: str | None = None
    comparison_evidence: str = "DOCUMENT_ONLY"
    reference_panel_id: str | None = None
    target_population: str | None = None
    application_context: str | None = None
    active_bottle_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "original_request", _text(self.original_request, "original_request"))
        for field in (
            "known_materials",
            "known_references",
            "desired_changes",
            "must_preserve",
            "must_avoid",
            "evaluation_windows",
        ):
            object.__setattr__(self, field, _dedupe(getattr(self, field)))
        if self.execution_strategy is not None:
            object.__setattr__(
                self,
                "execution_strategy",
                _enum(self.execution_strategy, _EXECUTION_STRATEGIES, "execution_strategy"),
            )
        if self.appeal_mode is not None:
            object.__setattr__(self, "appeal_mode", _enum(self.appeal_mode, _APPEAL_MODES, "appeal_mode"))
        object.__setattr__(
            self,
            "comparison_evidence",
            _enum(self.comparison_evidence, _COMPARISON_EVIDENCE, "comparison_evidence"),
        )
        for field in ("reference_panel_id", "target_population", "application_context", "active_bottle_id"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _text(value, field))


def interpret_request(request: RequestInterpretationInputV1) -> dict[str, Any]:
    """Return a reviewable interpretation card without taking an action."""

    text = request.original_request
    ambiguities: list[str] = []

    inferred_evolving = bool(_EVOLVING_RE.search(text) or request.active_bottle_id)
    inferred_new = bool(
        _NEW_FORMULA_RE.search(text)
        and not re.search(r"\bnot\s+(?:a\s+)?new\s+(?:formula|bottle|batch)\b", text, re.I)
    )
    if inferred_evolving and inferred_new:
        ambiguities.append("CONTRADICTORY_EXECUTION_STRATEGY")
    execution_strategy = request.execution_strategy or (
        "EVOLVING_BOTTLE" if inferred_evolving else "NEW_FORMULA"
    )
    if request.execution_strategy is not None:
        if inferred_evolving and execution_strategy == "NEW_FORMULA":
            ambiguities.append("EXPLICIT_STRATEGY_CONFLICTS_WITH_CURRENT_BOTTLE_LANGUAGE")
        if inferred_new and execution_strategy == "EVOLVING_BOTTLE":
            ambiguities.append("EXPLICIT_STRATEGY_CONFLICTS_WITH_NEW_FORMULA_LANGUAGE")

    inferred_global = bool(_GLOBAL_RE.search(text))
    inferred_identity = bool(_IDENTITY_RE.search(text))
    if inferred_global and inferred_identity and request.appeal_mode is None:
        # Identity preservation is compatible with crowd-pleasing mode, but a
        # bare request containing both mode labels needs the user to choose the
        # optimization framing.
        ambiguities.append("MULTIPLE_APPEAL_MODES_NAMED")
    appeal_mode = request.appeal_mode or (
        "GLOBAL_CROWD_PLEASING" if inferred_global else "IDENTITY_FIRST"
    )

    preserve = list(request.must_preserve)
    avoid = list(request.must_avoid)
    preserve.extend(match.group("value").strip() for match in _PRESERVE_RE.finditer(text))
    parsed_avoid, avoid_spans = _avoid_values_and_spans(text)
    avoid.extend(parsed_avoid)
    preserve_values = _dedupe(preserve)
    avoid_values = _dedupe(avoid)
    overlap = {value.casefold() for value in preserve_values} & {
        value.casefold() for value in avoid_values
    }
    if overlap:
        ambiguities.append("SAME_CONSTRAINT_PRESERVED_AND_AVOIDED")

    windows: list[dict[str, Any]] = [
        {"label": value, "time_seconds": None, "source": "STRUCTURED_REQUEST"}
        for value in request.evaluation_windows
    ]
    window_keys = {(row["label"], row["time_seconds"]) for row in windows}
    for label, seconds, pattern in _WINDOWS:
        if pattern.search(text) and (label, seconds) not in window_keys:
            windows.append({"label": label, "time_seconds": seconds, "source": "FREE_TEXT"})
            window_keys.add((label, seconds))

    positive_text = _masked_text(text, avoid_spans)
    materials = _matched_names(positive_text, request.known_materials)
    prohibited_materials = _exact_prohibited_names(avoid_values, request.known_materials)
    prohibited_identity_phrases = tuple(
        value
        for value in avoid_values
        if _constraints_overlap(request.known_materials, (value,))
    )
    mandatory_materials = _mandatory_materials(positive_text, request.known_materials)
    references = _matched_names(positive_text, request.known_references)
    quantities = _quantities(text, request.known_materials)
    material_count_constraints = _material_count_constraints(text)
    quantity_materials = tuple(
        row["material"]
        for row in quantities
        if row["scope"] == "MATERIAL_DOSE" and row["material"] is not None
    )
    mandatory_materials = _dedupe((*mandatory_materials, *quantity_materials))
    if any(
        row["scope"] == "MATERIAL_DOSE" and row["material"] is None
        for row in quantities
    ):
        ambiguities.append("QUANTITY_WITHOUT_EXACT_MATERIAL_BINDING")
    if _constraints_overlap(mandatory_materials, avoid_values):
        ambiguities.append("REQUIRED_MATERIAL_IS_ALSO_PROHIBITED")
    if _constraints_overlap(materials, avoid_values):
        ambiguities.append("EXPLICIT_MATERIAL_IS_ALSO_PROHIBITED")

    exact_counts = {
        row["count"]
        for row in material_count_constraints
        if row["kind"] == "EXACT"
    }
    minimums = [
        row["count"]
        for row in material_count_constraints
        if row["kind"] == "MINIMUM"
    ]
    maximums = [
        row["count"]
        for row in material_count_constraints
        if row["kind"] == "MAXIMUM"
    ]
    if len(exact_counts) > 1:
        ambiguities.append("CONTRADICTORY_EXACT_MATERIAL_COUNTS")
    if minimums and maximums and max(minimums) > min(maximums):
        ambiguities.append("CONTRADICTORY_MATERIAL_COUNT_RANGE")
    if exact_counts:
        exact = next(iter(exact_counts))
        if (minimums and exact < max(minimums)) or (
            maximums and exact > min(maximums)
        ):
            ambiguities.append("EXACT_MATERIAL_COUNT_OUTSIDE_REQUESTED_RANGE")

    opposed_requirements = any(
        left.search(text) and right.search(text)
        for left, right in _OPPOSED_REQUIREMENTS
    )
    if opposed_requirements and (_SIMULTANEOUS_RE.search(text) or not windows):
        ambiguities.append("MUTUALLY_EXCLUSIVE_SENSORY_REQUIREMENTS")

    desired = request.desired_changes or (text,)
    desired_rows: list[dict[str, Any]] = [
        {
            "text": change,
            "direction": _direction(change),
            "materials": list(_matched_names(change, request.known_materials)),
        }
        for change in desired
    ]
    if any(row["direction"] == "CONTRADICTORY" for row in desired_rows):
        ambiguities.append("CONTRADICTORY_CHANGE_DIRECTION")

    direct_decrease = any(row["direction"] == "DECREASE" for row in desired_rows)
    additive_feasibility = "ADDITIVE_FEASIBLE"
    if execution_strategy == "EVOLVING_BOTTLE" and direct_decrease:
        additive_feasibility = "ADDITIVE_REPAIR_NOT_FEASIBLE"

    confirmation_required = bool(ambiguities)
    status = "WITHHELD_REQUEST_AMBIGUOUS" if confirmation_required else "REQUEST_INTERPRETATION_READY"
    normalized_goal = "; ".join(change.strip() for change in desired)
    card = {
        "schema_version": "request-interpretation-v1",
        "original_request": text,
        "normalized_goal": normalized_goal,
        "desired_changes": desired_rows,
        "desired_directions": sorted({row["direction"] for row in desired_rows}),
        "explicit_materials": list(materials),
        "mandatory_materials": list(mandatory_materials),
        "prohibited_materials": list(prohibited_materials),
        "prohibited_identity_phrases": list(prohibited_identity_phrases),
        "explicit_quantities": list(quantities),
        "material_count_constraints": list(material_count_constraints),
        "must_preserve": list(preserve_values),
        "must_avoid": list(avoid_values),
        "evaluation_windows": windows,
        "execution_strategy": execution_strategy,
        "appeal_mode": appeal_mode,
        "comparison_evidence": request.comparison_evidence,
        "reference_scope": {
            "reference_panel_id": request.reference_panel_id,
            "named_references": list(references),
            "target_population": request.target_population,
        },
        "application_context": request.application_context,
        "active_bottle_id": request.active_bottle_id,
        "additive_feasibility": additive_feasibility,
        "assumptions": [
            "No proprietary commercial formula composition is inferred.",
            "Read-only interpretation does not authorize a bottle addition.",
        ],
        "ambiguities": sorted(set(ambiguities)),
        "confirmation_required": confirmation_required,
        "field_confidence": {
            "materials": "EXACT_STRING_MATCH" if materials else "NOT_STATED",
            "quantities": "EXACT_SYNTAX" if quantities else "NOT_STATED",
            "execution_strategy": "EXPLICIT" if request.execution_strategy else "RULE_INFERRED_OR_DEFAULTED",
            "appeal_mode": "EXPLICIT" if request.appeal_mode else "RULE_INFERRED_OR_DEFAULTED",
            "soft_descriptors": "RULE_BASED_ADVISORY",
        },
        "status": status,
        "action_generated": False,
        **FALSE_ACTION_AUTHORITY,
    }
    payload = asdict(request)
    return {
        **card,
        "request_sha256": stable_payload_hash(payload),
        "interpretation_sha256": stable_payload_hash(card),
    }


__all__ = [
    "AppealMode",
    "ComparisonEvidence",
    "ExecutionStrategy",
    "RequestInterpretationInputV1",
    "interpret_request",
]
