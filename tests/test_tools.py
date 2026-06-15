"""
Pytest tests for the three FitFindr tools in tools.py.

The suggest_outfit and create_fit_card tests only assert that a non-empty
string is returned, so they pass whether the Groq call succeeds or falls back
to the descriptive error string (e.g. when GROQ_API_KEY is unset).

Run from the project root:
    pytest
"""

import os
import sys

# Make the project root importable when running pytest from anywhere.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import (
    load_listings,
    get_example_wardrobe,
    get_empty_wardrobe,
)


# ── search_listings ─────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    results = search_listings("tee", size="M")
    assert all("m" in item["size"].lower() for item in results)


# ── suggest_outfit ──────────────────────────────────────────────────────────

def test_suggest_with_wardrobe():
    new_item = load_listings()[1]
    result = suggest_outfit(new_item, get_example_wardrobe())
    assert isinstance(result, str)
    assert result.strip() != ""


def test_suggest_empty_wardrobe():
    new_item = load_listings()[1]
    result = suggest_outfit(new_item, get_empty_wardrobe())
    assert isinstance(result, str)
    assert result.strip() != ""


# ── create_fit_card ─────────────────────────────────────────────────────────

def test_fit_card_empty_outfit():
    new_item = load_listings()[1]
    result = create_fit_card("", new_item)
    assert isinstance(result, str)
    assert result.strip() != ""


def test_fit_card_real_outfit():
    new_item = load_listings()[1]
    outfit = (
        "Pair the baby tee with baggy dark-wash jeans and chunky white "
        "sneakers, layered under a vintage black denim jacket."
    )
    result = create_fit_card(outfit, new_item)
    assert isinstance(result, str)
    assert result.strip() != ""
