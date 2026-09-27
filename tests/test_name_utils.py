"""Material identity must survive the normalization performance change."""

import re
import sys

import pytest

from engine import name_utils


def test_all_unicode_whitespace_preserves_legacy_normalization():
    # Cover the actual Unicode predicate, including control separators and
    # non-breaking spaces encountered in copied supplier labels.
    whitespace = [chr(code) for code in range(sys.maxunicode + 1) if chr(code).isspace()]
    labels = [*name_utils._ALIASES, *name_utils._ALIASES.values(), "Unknown Material"]
    for separator in whitespace:
        for label in labels:
            source = separator + label.upper().replace(" ", separator * 2) + separator
            legacy = re.sub(r"\s+", " ", source.strip()).lower()
            assert name_utils.normalize_name(source) == name_utils._ALIASES.get(legacy, legacy)


@pytest.mark.parametrize("source", ["", " \t\n", "Alpha Irone", "Alpha Ionone", "İris", "A\u200bB"])
def test_empty_and_non_whitespace_characters_keep_existing_identity(source):
    legacy = re.sub(r"\s+", " ", source.strip()).lower()
    assert name_utils.normalize_name(source) == name_utils._ALIASES.get(legacy, legacy)


def test_alias_changes_are_visible_without_cache_invalidation(monkeypatch):
    source = "  Performance\tAlias  "
    assert name_utils.normalize_name(source) == "performance alias"
    monkeypatch.setitem(name_utils._ALIASES, "performance alias", "first identity")
    assert name_utils.normalize_name(source) == "first identity"
    monkeypatch.setitem(name_utils._ALIASES, "performance alias", "second identity")
    assert name_utils.normalize_name(source) == "second identity"
    monkeypatch.delitem(name_utils._ALIASES, "performance alias")
    assert name_utils.normalize_name(source) == "performance alias"


@pytest.mark.parametrize(
    ("stock_label", "canonical"),
    [
        ("Anisaldehyde 10% v/v in ethanol", "anisaldehyde"),
        ("Ethyl Maltol 1% v/v in ethanol", "ethyl maltol"),
        ("Helional 10% v/v in ethanol", "helional"),
        ("Hexyl Acetate 1% v/v in DPG", "hexyl acetate"),
        ("Cinnamyl Alcohol 50% w/w in DPG", "cinnamyl alcohol"),
    ],
)
def test_exact_current_stock_labels_resolve_to_existing_identity(stock_label, canonical):
    assert name_utils.normalize_name(stock_label) == canonical
