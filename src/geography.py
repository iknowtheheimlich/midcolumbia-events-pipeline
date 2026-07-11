"""Deterministic geographic enrichment for canonical events.

Attempt_27_GeographicIntelligence

No network geocoding is performed. Classification uses normalized event city/state
and, when present, latitude/longitude supplied by upstream data.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any


_SPACE_RE = re.compile(r"\s+")
_ADDRESS_CITY_STATE_RE = re.compile(
    r",\s*([^,]+?),\s*(WA|Washington|OR|Oregon|ID|Idaho|BC|British Columbia)"
    r"(?:\s+\d{5}(?:-\d{4})?)?(?:,\s*(?:USA|United States|Canada))?\s*$",
    re.IGNORECASE,
)
_STREET_LOCATION_RE = re.compile(r"^\s*\d+[A-Za-z]?\s+\S+")


TRI_CITIES = {
    "kennewick",
    "richland",
    "pasco",
    "west richland",
    "benton city",
    "burbank",
    "finley",
}
LOWER_VALLEY = {"prosser", "grandview", "sunnyside", "mabton", "zillah", "toppenish"}
WALLA_WALLA = {"walla walla", "college place", "waitsburg", "dayton", "prescott"}
YAKIMA = {"yakima", "selah", "naches", "union gap", "ellensburg", "cle elum"}
MOSES_LAKE = {"moses lake", "othello", "quincy", "ephrata", "soap lake"}
COLUMBIA_GORGE = {"the dalles", "dufur", "hood river", "boardman"}
PENDLETON = {"pendleton", "hermiston", "umatilla", "stanfield", "echo", "sumpter"}
SPOKANE = {"spokane", "spokane valley", "cheney", "liberty lake"}

REGION_BY_CITY = {
    **{city: "TRI_CITIES" for city in TRI_CITIES},
    **{city: "LOWER_VALLEY" for city in LOWER_VALLEY},
    **{city: "WALLA_WALLA" for city in WALLA_WALLA},
    **{city: "YAKIMA" for city in YAKIMA},
    **{city: "MOSES_LAKE" for city in MOSES_LAKE},
    **{city: "COLUMBIA_GORGE" for city in COLUMBIA_GORGE},
    **{city: "PENDLETON" for city in PENDLETON},
    **{city: "SPOKANE" for city in SPOKANE},
}

SCOPE_BY_REGION = {
    "TRI_CITIES": "LOCAL",
    "LOWER_VALLEY": "REGIONAL_REVIEW",
    "WALLA_WALLA": "REGIONAL_REVIEW",
    "YAKIMA": "OUT_OF_AREA",
    "MOSES_LAKE": "OUT_OF_AREA",
    "COLUMBIA_GORGE": "OUT_OF_AREA",
    "PENDLETON": "OUT_OF_AREA",
    "SPOKANE": "OUT_OF_AREA",
    "OTHER": "OUT_OF_AREA",
    "UNKNOWN": "REVIEW",
}

CITY_CENTERS = {
    "kennewick": (46.2112, -119.1372),
    "richland": (46.2857, -119.2845),
    "pasco": (46.2396, -119.1006),
}


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class GeographicResult:
    city: str | None
    state: str | None
    region: str
    scope: str
    location_type: str
    point: GeoPoint | None = None
    distance_to_kennewick_miles: float | None = None
    distance_to_richland_miles: float | None = None
    distance_to_pasco_miles: float | None = None


def normalize_city(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = _SPACE_RE.sub(" ", value.strip()).strip(" ,")
    if not cleaned or cleaned.casefold() == "unknown":
        return None
    replacements = {
        "hermiston": "Hermiston",
        "herminston": "Hermiston",
        "west richland": "West Richland",
        "walla walla": "Walla Walla",
        "the dalles": "The Dalles",
        "moses lake": "Moses Lake",
        "tri cities": "Tri-Cities",
        "tri-cities": "Tri-Cities",
    }
    key = cleaned.casefold()
    return replacements.get(key, cleaned.title())


def normalize_state(value: str | None) -> str | None:
    if not value:
        return None
    key = value.strip().casefold()
    aliases = {
        "wa": "WA",
        "washington": "WA",
        "or": "OR",
        "oregon": "OR",
        "id": "ID",
        "idaho": "ID",
        "bc": "BC",
        "british columbia": "BC",
    }
    return aliases.get(key, value.strip().upper())


def looks_like_street_location(value: str | None) -> bool:
    """Return True when a value begins like a numbered street location."""
    return bool(value and _STREET_LOCATION_RE.match(value))


def city_state_from_address(address: str | None) -> tuple[str | None, str | None]:
    if not address:
        return None, None
    match = _ADDRESS_CITY_STATE_RE.search(address.strip())
    if not match:
        return None, None
    return normalize_city(match.group(1)), normalize_state(match.group(2))


def classify_region(city: str | None, state: str | None = None) -> str:
    normalized_city = normalize_city(city)
    normalized_state = normalize_state(state)
    if not normalized_city:
        return "UNKNOWN"
    key = normalized_city.casefold()
    if key == "tri-cities":
        return "TRI_CITIES"
    region = REGION_BY_CITY.get(key)
    if region:
        return region
    if normalized_state in {"WA", "OR", "ID", "BC"}:
        return "OTHER"
    return "UNKNOWN"


def haversine_miles(a: GeoPoint, b: GeoPoint) -> float:
    radius_miles = 3958.7613
    lat1 = math.radians(a.latitude)
    lat2 = math.radians(b.latitude)
    delta_lat = math.radians(b.latitude - a.latitude)
    delta_lon = math.radians(b.longitude - a.longitude)
    h = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return radius_miles * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def _event_point(event: dict[str, Any]) -> GeoPoint | None:
    latitude = event.get("latitude")
    longitude = event.get("longitude")
    if latitude is None or longitude is None:
        return None
    try:
        return GeoPoint(float(latitude), float(longitude))
    except (TypeError, ValueError):
        return None


def _location_type(event: dict[str, Any]) -> str:
    venue = str(event.get("venue") or "").strip()
    if looks_like_street_location(venue) and not event.get("venue_id"):
        return "PRIVATE_ADDRESS"
    return "VENUE"


def classify_event(event: dict[str, Any]) -> GeographicResult:
    raw_city = str(event.get("city") or "").strip()
    city = normalize_city(raw_city)
    state = normalize_state(str(event.get("state") or ""))

    address_city, address_state = city_state_from_address(str(event.get("address") or ""))

    # Some marketplace sources put a truncated street fragment in the city field.
    # Prefer a city parsed from the full address; otherwise leave it unresolved.
    if looks_like_street_location(raw_city):
        city = address_city
    else:
        city = city or address_city
    state = state or address_state

    region = classify_region(city, state)
    scope = SCOPE_BY_REGION[region]
    point = _event_point(event)

    distances: dict[str, float | None] = {name: None for name in CITY_CENTERS}
    if point is not None:
        for name, (latitude, longitude) in CITY_CENTERS.items():
            distances[name] = round(haversine_miles(point, GeoPoint(latitude, longitude)), 1)

    return GeographicResult(
        city=city,
        state=state,
        region=region,
        scope=scope,
        location_type=_location_type(event),
        point=point,
        distance_to_kennewick_miles=distances["kennewick"],
        distance_to_richland_miles=distances["richland"],
        distance_to_pasco_miles=distances["pasco"],
    )


def enrich_event_geography(event: dict[str, Any]) -> dict[str, Any]:
    copied = dict(event)
    result = classify_event(copied)
    if result.city:
        copied["city"] = result.city
    elif looks_like_street_location(str(copied.get("city") or "")):
        copied.pop("city", None)
    if result.state:
        copied["state"] = result.state
    copied["geo_region"] = result.region
    copied["geo_scope"] = result.scope
    copied["location_type"] = result.location_type
    if result.distance_to_kennewick_miles is not None:
        copied["distance_to_kennewick_miles"] = result.distance_to_kennewick_miles
        copied["distance_to_richland_miles"] = result.distance_to_richland_miles
        copied["distance_to_pasco_miles"] = result.distance_to_pasco_miles
    return copied
