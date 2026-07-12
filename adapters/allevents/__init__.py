"""AllEvents collector.

Acquisition and source normalization only. Downstream intelligence remains source-agnostic.
"""

from adapters.allevents.parser import parse_pages

__all__ = ["parse_pages"]
