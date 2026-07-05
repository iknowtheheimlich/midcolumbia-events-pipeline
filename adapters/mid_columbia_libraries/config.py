"""Mid-Columbia Libraries adapter configuration."""

SOURCE_NAME = "MidColumbiaLibraries"
DEFAULT_VENUE_PREFIX = "Mid-Columbia Library"
BASE_URL = "https://midcolumbialibraries.org"
EVENTS_URL = f"{BASE_URL}/events"
CALENDAR_URL = f"{BASE_URL}/calendar"

BRANCH_CITY_MAP = {
    "Basin City": "Basin City",
    "Benton City": "Benton City",
    "Connell": "Connell",
    "Kahlotus": "Kahlotus",
    "Keewaydin Park": "Kennewick",
    "Kennewick": "Kennewick",
    "Merrill's Corner": "Pasco",
    "Multiple Branches": "Multiple Branches",
    "Offsite": "Offsite",
    "Online": "Online",
    "Othello": "Othello",
    "Pasco": "Pasco",
    "Prosser": "Prosser",
    "Rural Services": "Rural Services",
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
    "Lecture",
    "Library Tour",
    "Preschool Program",
    "School Visit",
    "Special Event",
    "Storytime",
    "Teen Program",
}

AUDIENCES = {
    "Adults",
    "All Ages",
    "0-5",
    "6-8",
    "9-12",
    "Teens",
    "Teens 13+",
    "6-12",
}
