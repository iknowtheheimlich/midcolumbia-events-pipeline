import json

from adapters.allevents.parser import parse_pages


def _event(event_id: str, title: str) -> dict:
    return {
        "@type": "Event",
        "name": title,
        "startDate": "2026-07-13T10:00:00-07:00",
        "url": f"https://allevents.in/richland/event/{event_id}",
        "location": {
            "@type": "Place",
            "name": "Richland Public Library",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Richland",
                "addressRegion": "WA",
            },
        },
    }


def _page_with_boundary() -> str:
    payload = {
        "@context": "https://schema.org",
        "@graph": [
            _event("200030396981203", "Music Together"),
            _event("200030043282554", "Global Recommendation"),
        ],
    }
    return (
        '<html><head><script type="application/ld+json">'
        + json.dumps(payload)
        + '</script></head><body>'
        + '<li class="event-card" data-eid="200030396981203">Music Together</li>'
        + '<div class="qsp_title"><span>Results for selected filters around the globe</span></div>'
        + '<li class="event-card" data-eid="200030043282554">Global Recommendation</li>'
        + '</body></html>'
    )


def test_global_recommendation_json_ld_is_rejected_after_visible_boundary() -> None:
    events = parse_pages({"Kennewick": _page_with_boundary()})

    assert [event["title"] for event in events] == ["Music Together"]


def test_json_ld_remains_authoritative_when_page_has_no_scope_boundary() -> None:
    payload = {
        "@context": "https://schema.org",
        "@graph": [_event("200030043282554", "Unbounded Event")],
    }
    html = (
        '<html><head><script type="application/ld+json">'
        + json.dumps(payload)
        + '</script></head><body></body></html>'
    )

    events = parse_pages({"Kennewick": html})

    assert [event["title"] for event in events] == ["Unbounded Event"]
