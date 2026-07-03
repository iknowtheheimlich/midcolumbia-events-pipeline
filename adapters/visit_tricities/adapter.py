"""Visit Tri-Cities source adapter.

Milestone: Attempt_15_Visit_Tri-Cities

This module is intentionally scaffolded before implementation.
It should parse saved Visit Tri-Cities HTML and emit canonical event schema objects.
"""

SOURCE_NAME = "VisitTriCities"


def parse_visit_tricities_html(html: str) -> list[dict]:
    """Parse Visit Tri-Cities saved HTML into canonical event objects.

    Implementation target:
    - Accept saved HTML from fixtures/visit_tricities/saved_page.html
    - Return canonical event objects compatible with docs/EventSchema.md
    - Preserve raw venue strings for resolver processing

    This placeholder deliberately returns an empty list until fixture HTML and
    expected_events.json are populated.
    """
    if not isinstance(html, str):
        raise TypeError("html must be a string")

    return []
