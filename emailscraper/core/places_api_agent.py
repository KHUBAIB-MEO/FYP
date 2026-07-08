"""
emailscraper/core/places_api_agent.py
----------------------------------------
OPTIONAL paid alternative to maps_agent.py (Playwright).

If the user pastes a Google Places API key into the GUI, this is used
instead of browser-scraping Google Maps. Trade-offs vs. the free path:

    Free (maps_agent.py, Playwright)     Paid (this file, Places API)
    ------------------------------       ------------------------------
    $0 cost                              Free tier + billing account
                                          required on Google Cloud
    Needs delay/cooldown tuning          No anti-ban tuning needed —
    to avoid IP flags                    it's an official API call
    Slower (real browser)                Faster (plain HTTP requests)
    Selectors can break if Google        Stable — official, versioned API
    changes their HTML

Leave the API key field blank in the GUI and NONE of this file's code
runs — lead_finder.py falls back to maps_agent.py automatically.

Docs:
  Text Search: https://developers.google.com/maps/documentation/places/web-service/search-text
  Place Details: https://developers.google.com/maps/documentation/places/web-service/details
"""
import time
from typing import Callable, List, Optional

import requests

TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


class PlacesApiAgent:
    """
    Usage:
        agent = PlacesApiAgent(api_key="AIza...")
        places = agent.search("software house", "Karachi", max_results=15)
    """

    def __init__(self, api_key: str, timeout: int = 15):
        self.api_key = api_key
        self.timeout = timeout

    def search(
        self,
        keyword: str,
        city: str,
        max_results: int = 15,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> List[dict]:
        query = f"{keyword} in {city}"
        places: List[dict] = []
        params = {"query": query, "key": self.api_key}

        # Google returns up to 20 results per page, with a token for the
        # next page (max 60 results total across 3 pages).
        while len(places) < max_results:
            resp = requests.get(TEXT_SEARCH_URL, params=params, timeout=self.timeout)
            data = resp.json()

            status = data.get("status")
            if status not in ("OK", "ZERO_RESULTS"):
                # Common statuses: REQUEST_DENIED (bad/unbilled key),
                # OVER_QUERY_LIMIT (quota used up), INVALID_REQUEST
                raise RuntimeError(
                    f"Google Places API error: {status} — "
                    f"{data.get('error_message', 'check your API key / billing')}"
                )

            for result in data.get("results", []):
                if len(places) >= max_results:
                    break

                details = self._get_details(result.get("place_id"))
                places.append(
                    details
                    or {
                        "name": result.get("name", "Unknown"),
                        "website": "",
                        "phone": "",
                        "address": result.get("formatted_address", ""),
                    }
                )
                if progress_cb:
                    progress_cb(len(places), max_results)

            next_page_token = data.get("next_page_token")
            if not next_page_token or len(places) >= max_results:
                break

            # Google requires a short delay before a next_page_token becomes
            # usable — this is Google's own API rule, not an anti-ban trick.
            time.sleep(2)
            params = {"pagetoken": next_page_token, "key": self.api_key}

        return places[:max_results]

    def _get_details(self, place_id: Optional[str]) -> Optional[dict]:
        """Fetch website/phone/address for one place_id (Text Search alone doesn't include these)."""
        if not place_id:
            return None
        params = {
            "place_id": place_id,
            "fields": "name,website,formatted_phone_number,formatted_address",
            "key": self.api_key,
        }
        try:
            resp = requests.get(DETAILS_URL, params=params, timeout=self.timeout)
            data = resp.json()
            if data.get("status") != "OK":
                return None
            r = data.get("result", {})
            return {
                "name": r.get("name", "Unknown"),
                "website": r.get("website", ""),
                "phone": r.get("formatted_phone_number", ""),
                "address": r.get("formatted_address", ""),
            }
        except requests.RequestException:
            return None
