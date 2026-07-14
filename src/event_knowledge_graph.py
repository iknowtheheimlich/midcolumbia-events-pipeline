"""Build a deterministic relationship index from enriched event records.

Attempt_58_EventKnowledgeGraph

This is an additive artifact, not a replacement data model. Relationships are created
only from explicit canonical fields and retain source provenance.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable
from urllib.parse import urlparse

DEFAULT_EVENT_GRAPH_PATH = Path("artifacts") / "intelligence" / "Event_Knowledge_Graph.json"
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    node_type: str
    label: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    edge_id: str
    edge_type: str
    from_node: str
    to_node: str
    provenance: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class EventKnowledgeGraph:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "nodes": [asdict(node) for node in self.nodes],
            "edges": [
                {**asdict(edge), "provenance": list(edge.provenance)}
                for edge in self.edges
            ],
        }


def build_event_knowledge_graph(events: Iterable[dict[str, Any]]) -> EventKnowledgeGraph:
    nodes: dict[str, GraphNode] = {}
    edge_provenance: dict[tuple[str, str, str], list[dict[str, Any]]] = {}

    for event in events:
        event_node = _event_node(event)
        nodes[event_node.node_id] = event_node
        provenance = _provenance(event)

        venue_node = _venue_node(event)
        if venue_node:
            nodes.setdefault(venue_node.node_id, venue_node)
            _add_edge(edge_provenance, "HOSTED_AT", event_node.node_id, venue_node.node_id, provenance)

        organization_node = _organization_node(event)
        if organization_node:
            nodes.setdefault(organization_node.node_id, organization_node)
            _add_edge(edge_provenance, "ORGANIZED_BY", event_node.node_id, organization_node.node_id, provenance)

        series_node = _series_node(event)
        if series_node:
            nodes.setdefault(series_node.node_id, series_node)
            _add_edge(edge_provenance, "PART_OF_SERIES", event_node.node_id, series_node.node_id, provenance)

        ticket_node = _ticket_provider_node(event)
        if ticket_node:
            nodes.setdefault(ticket_node.node_id, ticket_node)
            _add_edge(edge_provenance, "TICKETED_BY", event_node.node_id, ticket_node.node_id, provenance)

    edges = [
        GraphEdge(
            edge_id=_stable_id("edge", edge_type, from_node, to_node),
            edge_type=edge_type,
            from_node=from_node,
            to_node=to_node,
            provenance=tuple(_dedupe_provenance(items)),
        )
        for (edge_type, from_node, to_node), items in edge_provenance.items()
    ]
    return EventKnowledgeGraph(
        nodes=tuple(sorted(nodes.values(), key=lambda node: (node.node_type, node.label.casefold(), node.node_id))),
        edges=tuple(sorted(edges, key=lambda edge: (edge.edge_type, edge.from_node, edge.to_node))),
    )


def write_event_knowledge_graph(
    events: Iterable[dict[str, Any]],
    output_path: Path = DEFAULT_EVENT_GRAPH_PATH,
) -> Path:
    if "fixtures" in {part.casefold() for part in output_path.parts}:
        raise ValueError("generated event graph must remain separate from fixtures")
    graph = build_event_knowledge_graph(events)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(graph.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def _event_node(event: dict[str, Any]) -> GraphNode:
    title = _clean(event.get("title")) or "Untitled event"
    identity = event.get("source_event_id") or event.get("url") or "|".join(
        [_clean(event.get("source")), title, _clean(event.get("start_date")), _clean(event.get("start_time"))]
    )
    return GraphNode(
        node_id=_stable_id("event", identity),
        node_type="EVENT",
        label=title,
        attributes={
            key: value
            for key, value in {
                "start_date": event.get("start_date"),
                "start_time": event.get("start_time"),
                "end_date": event.get("end_date"),
                "end_time": event.get("end_time"),
                "category": event.get("category"),
                "url": event.get("external_url") or event.get("url"),
            }.items()
            if value not in (None, "", [], {})
        },
    )


def _venue_node(event: dict[str, Any]) -> GraphNode | None:
    label = _clean(event.get("venue_registry_name") or event.get("venue"))
    if not label:
        return None
    identity = event.get("venue_id") or f"{label}|{_clean(event.get('city'))}"
    return GraphNode(
        node_id=_stable_id("venue", identity),
        node_type="VENUE",
        label=label,
        attributes={
            key: value
            for key, value in {
                "venue_id": event.get("venue_id"),
                "city": event.get("city"),
                "state": event.get("state"),
                "address": event.get("address"),
                "venue_type": event.get("venue_type") or event.get("registry_venue_type"),
            }.items()
            if value not in (None, "", [], {})
        },
    )


def _organization_node(event: dict[str, Any]) -> GraphNode | None:
    label = _clean(event.get("organization") or event.get("organizer") or event.get("host"))
    if not label:
        return None
    return GraphNode(_stable_id("organization", label), "ORGANIZATION", label)


def _series_node(event: dict[str, Any]) -> GraphNode | None:
    label = _clean(event.get("series_title") or event.get("program_title") or event.get("series_name"))
    identity = event.get("series_id") or event.get("program_id") or label
    if not label or not identity:
        return None
    return GraphNode(_stable_id("series", identity), "SERIES", label)


def _ticket_provider_node(event: dict[str, Any]) -> GraphNode | None:
    provider = _clean(event.get("ticket_provider"))
    url = _clean(event.get("eventbrite_url") or event.get("registration_url") or event.get("ticket_url"))
    if not provider and url:
        host = urlparse(url).netloc.casefold()
        if "eventbrite" in host:
            provider = "Eventbrite"
    if not provider:
        return None
    return GraphNode(_stable_id("ticket_provider", provider), "TICKET_PROVIDER", provider)


def _provenance(event: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "source": event.get("source"),
            "source_event_id": event.get("source_event_id"),
            "url": event.get("url"),
        }.items()
        if value not in (None, "")
    }


def _add_edge(
    edges: dict[tuple[str, str, str], list[dict[str, Any]]],
    edge_type: str,
    from_node: str,
    to_node: str,
    provenance: dict[str, Any],
) -> None:
    edges.setdefault((edge_type, from_node, to_node), []).append(provenance)


def _dedupe_provenance(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for item in items:
        identity = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if identity in seen:
            continue
        seen.add(identity)
        output.append(item)
    return output


def _stable_id(namespace: str, *parts: Any) -> str:
    normalized = "|".join(_clean(part).casefold() for part in parts)
    digest = hashlib.sha256(f"{namespace}|{normalized}".encode("utf-8")).hexdigest()[:16]
    return f"{namespace}:{digest}"


def _clean(value: Any) -> str:
    return _SPACE_RE.sub(" ", str(value or "")).strip()
