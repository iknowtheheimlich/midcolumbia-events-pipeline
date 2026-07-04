"""Visit Tri-Cities Algolia configuration.

These values are shipped publicly by the Visit Tri-Cities website.
"""

SOURCE_NAME = "VisitTriCities"
BASE_URL = "https://www.visittri-cities.com"
ALGOLIA_APP_ID = "EYQHJ2IY2M"
ALGOLIA_INDEX_NAME = "prod-visit-tri-cities-2024-listings"
ALGOLIA_MULTI_QUERY_URL = "https://eyqhj2iy2m-dsn.algolia.net/1/indexes/*/queries"

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
