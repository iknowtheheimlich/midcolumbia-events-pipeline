import json
from pathlib import Path

from src.artist_registry import ArtistRegistry


def test_resolves_alias_and_uses_canonical_direct_url(tmp_path: Path) -> None:
    path = tmp_path / "artists.json"
    path.write_text(
        json.dumps(
            {
                "artists": [
                    {
                        "name": "The Band",
                        "website": "https://theband.example/?utm_source=events",
                        "genres": ["Rock"],
                        "aliases": ["Band, The"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    event = ArtistRegistry.from_json(path).enrich({"performer": "Band, The"})

    assert event["artist"] == "The Band"
    assert event["artist_url"] == "https://theband.example/"
    assert event["artist_genres"] == ["Rock"]


def test_unresolved_artist_is_sent_to_review() -> None:
    event = ArtistRegistry().enrich({"artist": "Unknown Artist"})

    assert event["detected_artist"] == "Unknown Artist"
    assert "unresolved_artist" in event["presentation_review_reasons"]


def test_host_is_not_misclassified_as_artist() -> None:
    event = ArtistRegistry().enrich({"host": "Novel Coffee Co."})

    assert "detected_artist" not in event
