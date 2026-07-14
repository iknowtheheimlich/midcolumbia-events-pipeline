import json
from pathlib import Path

import pytest

from src.event_knowledge_graph import build_event_knowledge_graph, write_event_knowledge_graph


def _event(**overrides):
    event = {
        "title": "Summer Concert",
        "start_date": "2026-07-18",
        "start_time": "19:00",
        "venue": "Howard Amon Park",
        "venue_id": "venue-123",
        "city": "Richland",
        "organization": "City of Richland",
        "source": "AllEvents",
        "source_event_id": "event-456",
        "url": "https://example.com/event-456",
    }
    event.update(overrides)
    return event


def test_builds_event_venue_and_organization_relationships():
    graph = build_event_knowledge_graph([_event()])
    assert {node.node_type for node in graph.nodes} == {"EVENT", "VENUE", "ORGANIZATION"}
    assert {edge.edge_type for edge in graph.edges} == {"HOSTED_AT", "ORGANIZED_BY"}


def test_shared_venue_becomes_one_node():
    graph = build_event_knowledge_graph(
        [
            _event(),
            _event(title="Second Concert", source_event_id="event-789", url="https://example.com/event-789"),
        ]
    )
    venues = [node for node in graph.nodes if node.node_type == "VENUE"]
    hosted_edges = [edge for edge in graph.edges if edge.edge_type == "HOSTED_AT"]
    assert len(venues) == 1
    assert len(hosted_edges) == 2
    assert {edge.to_node for edge in hosted_edges} == {venues[0].node_id}


def test_series_and_eventbrite_relationships_require_explicit_evidence():
    graph = build_event_knowledge_graph(
        [
            _event(
                series_title="Live at Five",
                series_id="series-live-at-five",
                eventbrite_url="https://www.eventbrite.com/e/example-123",
            )
        ]
    )
    assert {node.node_type for node in graph.nodes} >= {"SERIES", "TICKET_PROVIDER"}
    assert {edge.edge_type for edge in graph.edges} >= {"PART_OF_SERIES", "TICKETED_BY"}


def test_does_not_infer_performers_or_sponsors_from_description():
    graph = build_event_knowledge_graph(
        [_event(description="Featuring The Example Band, sponsored by Example Bank.")]
    )
    assert "PERFORMER" not in {node.node_type for node in graph.nodes}
    assert "SPONSOR" not in {node.node_type for node in graph.nodes}


def test_graph_ids_are_deterministic():
    first = build_event_knowledge_graph([_event()]).to_dict()
    second = build_event_knowledge_graph([_event()]).to_dict()
    assert first == second


def test_edge_preserves_source_provenance():
    graph = build_event_knowledge_graph([_event()])
    hosted = next(edge for edge in graph.edges if edge.edge_type == "HOSTED_AT")
    assert hosted.provenance == (
        {
            "source": "AllEvents",
            "source_event_id": "event-456",
            "url": "https://example.com/event-456",
        },
    )


def test_writer_rejects_fixture_directory(tmp_path: Path):
    with pytest.raises(ValueError):
        write_event_knowledge_graph([_event()], tmp_path / "fixtures" / "graph.json")


def test_writer_emits_schema_counts(tmp_path: Path):
    path = tmp_path / "artifacts" / "graph.json"
    write_event_knowledge_graph([_event()], path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["node_count"] == 3
    assert payload["edge_count"] == 2
