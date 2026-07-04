"""Visit Tri-Cities Algolia configuration.

These values are shipped publicly by the Visit Tri-Cities website.
Environment overrides allow rotation without source edits.
"""

from __future__ import annotations

import os

SOURCE_NAME = "VisitTriCities"
BASE_URL = "https://www.visittri-cities.com"
ALGOLIA_APP_ID = os.getenv("VTC_ALGOLIA_APP_ID", "EYQHJ2IY2M")
ALGOLIA_API_KEY = os.getenv("VTC_ALGOLIA_API_KEY", "c6d5977cb5cd80c09abfd2a7e5d9e88b")
ALGOLIA_INDEX_NAME = os.getenv("VTC_ALGOLIA_INDEX_NAME", "prod-visit-tri-cities-2024-listings")
ALGOLIA_MULTI_QUERY_URL = os.getenv(
    "VTC_ALGOLIA_MULTI_QUERY_URL",
    "https://eyqhj2iy2m-dsn.algolia.net/1/indexes/*/queries",
)

# Captured from the public site request payload.
ALGOLIA_EVENT_FILTERS = (
    'sectionName:"Events" '
    'AND (NOT isPrimaryEvent:false) '
    'AND ('
    'eventCategories:"Annual Events" OR '
    'eventCategories:"Arts & Theater" OR '
    'eventCategories:"Community Events" OR '
    'eventCategories:"Fairs & Festivals" OR '
    'eventCategories:"Food & Drink" OR '
    'eventCategories:"History & Heritage" OR '
    'eventCategories:"Holiday & Seasonal" OR '
    'eventCategories:"Kids & Family" OR '
    'eventCategories:"Music & Concerts" OR '
    'eventCategories:"Sports & Recreation" OR '
    'eventCategories:"Winery Events" OR '
    'eventCategories:"WW2"'
    ') '
    'AND ('
    'partnerRegions:"Benton City" OR '
    'partnerRegions:"Burbank" OR '
    'partnerRegions:"Connell" OR '
    'partnerRegions:"Grandview" OR '
    'partnerRegions:"Kennewick" OR '
    'partnerRegions:"Nearby" OR '
    'partnerRegions:"Outside Area" OR '
    'partnerRegions:"Pasco" OR '
    'partnerRegions:"Paterson" OR '
    'partnerRegions:"Prosser" OR '
    'partnerRegions:"Richland" OR '
    'partnerRegions:"Sunnyside" OR '
    'partnerRegions:"West Richland" OR '
    'partnerRegions:"Yakima"'
    ')'
)
