"""Mid-Columbia Libraries adapter configuration."""

SOURCE_NAME = "MidColumbiaLibraries"
DEFAULT_VENUE_PREFIX = "Mid-Columbia Library"
BASE_URL = "https://midcolumbialibraries.org"
EVENTS_URL = f"{BASE_URL}/events"

BRANCH_CITY_MAP = {
    "Basin City": "Basin City",
    "Benton City": "Benton City",
    "Connell": "Connell",
    "Kahlotus": "Kahlotus",
    "Keewaydin Park": "Kennewick",
    "Kennewick": "Kennewick",
    "Merrill's Corner": "Pasco",
    "Othello": "Othello",
    "Pasco": "Pasco",
    "Prosser": "Prosser",
    "Rural Services": "Kennewick",
    "West Pasco": "Pasco",
    "West Richland": "West Richland",
}

EVENT_TYPES = {
    "Adult Program",
    "Author Visit",
    "Book Club",
    "Branch Closure",
    "Community Program",
    "Elementary Program",
    "Friends Event",
    "Special Event",
    "Storytime",
    "Lecture",
    "Library Tour",
    "Preschool Program",
    "Teen Program",
    "School Visit",
}

AUDIENCES = {
    "Adults",
    "All Ages",
    "0-5",
    "6-8",
    "9-12",
    "Teens",
    "13+",
    "6-12",
}
