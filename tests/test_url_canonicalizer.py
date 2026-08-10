import pytest

from src.url_canonicalizer import (
    canonicalize_url,
    canonicalize_urls,
    is_facebook_share_url,
    validate_public_http_url,
)


def test_strips_tracking_and_fragment_without_shortening_domain() -> None:
    assert canonicalize_url(
        "https://facebook.com/theband/?utm_source=reddit&fbclid=abc#shows"
    ) == "https://www.facebook.com/theband"


def test_normalizes_missing_scheme_and_query_order() -> None:
    assert canonicalize_url("example.com/events?b=2&a=1") == "https://example.com/events?a=1&b=2"


def test_deduplicates_equivalent_urls() -> None:
    assert canonicalize_urls(
        ["https://instagram.com/theband/?utm_medium=social", "https://www.instagram.com/theband"]
    ) == ("https://www.instagram.com/theband",)


def test_rejects_non_http_destinations() -> None:
    assert canonicalize_url("javascript:alert(1)") is None


@pytest.mark.parametrize(
    "value",
    [
        "https://Facebook",
        "https://venue.example/https://tickets.example/event",
        "ftp://venue.example/events",
    ],
)
def test_rejects_malformed_public_destinations(value: str) -> None:
    assert canonicalize_url(value) is None
    with pytest.raises(ValueError):
        validate_public_http_url(value)


@pytest.mark.parametrize(
    "value",
    [
        "https://www.facebook.com/iconicbrewing/",
        "https://venue.example/events?q=music#tonight",
        "http://venue.example/",
    ],
)
def test_accepts_ordinary_public_destinations(value: str) -> None:
    assert validate_public_http_url(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "https://www.facebook.com/share/1EgaqDHA6R/",
        "https://facebook.com/sharer.php?u=https%3A%2F%2Fexample.com",
        "https://m.facebook.com/share.php?u=https%3A%2F%2Fexample.com",
    ],
)
def test_rejects_facebook_share_and_redirect_destinations(value: str) -> None:
    assert is_facebook_share_url(value)
    with pytest.raises(ValueError, match="share/redirect"):
        validate_public_http_url(value)


@pytest.mark.parametrize(
    "value",
    [
        "https://www.facebook.com/events/123456789/",
        "https://www.facebook.com/p/Iconic-Brewing-100063920740478/",
        "https://www.facebook.com/iconicbrewing/",
    ],
)
def test_accepts_direct_facebook_destinations(value: str) -> None:
    assert not is_facebook_share_url(value)
    assert validate_public_http_url(value) == value
