"""Eventbrite discovery adapter configuration.

Attempt_24_Eventbrite
"""

SOURCE_NAME = "Eventbrite"
BASE_URL = "https://www.eventbrite.com"
SEARCH_URLS = {
    "Richland": f"{BASE_URL}/d/wa--richland/events/",
    "Kennewick": f"{BASE_URL}/d/wa--kennewick/events/",
    "Pasco": f"{BASE_URL}/d/wa--pasco/events/",
}

LOCAL_CITIES = {
    "Richland",
    "West Richland",
    "Kennewick",
    "Pasco",
    "Benton City",
    "Finley",
    "Burbank",
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0 Safari/537.36"
)
