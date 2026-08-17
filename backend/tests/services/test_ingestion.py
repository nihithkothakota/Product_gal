"""
Tests for the ingestion service — URL normalization, hashing, and extraction.
"""

import pytest

from app.services.ingestion import (
    detect_source,
    detect_store,
    hash_url,
    normalize_url,
)


def test_normalize_url_strips_tracking_params():
    url = "https://www.amazon.in/dp/B09V3KXJPB?ref=abc&utm_source=google&tag=xyz"
    normalized = normalize_url(url)
    assert "utm_source" not in normalized
    assert "ref=" not in normalized
    assert "tag=" not in normalized
    assert "amazon.in/dp/b09v3kxjpb" in normalized


def test_normalize_url_lowercases():
    assert normalize_url("https://Amazon.in/Product") == normalize_url("https://amazon.in/product")


def test_hash_url_consistent():
    url1 = "https://www.amazon.in/dp/B09V3KXJPB?ref=abc"
    url2 = "https://www.amazon.in/dp/B09V3KXJPB?utm_source=google"
    assert hash_url(url1) == hash_url(url2)


def test_hash_url_different_products():
    url1 = "https://www.amazon.in/dp/B09V3KXJPB"
    url2 = "https://www.amazon.in/dp/B09DIFFERENT"
    assert hash_url(url1) != hash_url(url2)


def test_detect_store():
    assert detect_store("https://www.amazon.in/dp/B09V3KXJPB") == "Amazon"
    assert detect_store("https://www.flipkart.com/item/p/123") == "Flipkart"
    assert detect_store("https://www.myntra.com/shoes/nike/123") == "Myntra"
    assert detect_store("https://unknown-shop.com/product") is None


def test_detect_source():
    assert detect_source("https://www.instagram.com/p/abc123") == "instagram"
    assert detect_source("https://www.reddit.com/r/deals/post") == "reddit"
    assert detect_source("https://www.youtube.com/watch?v=abc") == "youtube"
    assert detect_source("https://www.amazon.in/dp/B09V") == "web"
