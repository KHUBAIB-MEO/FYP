"""
emailscraper/core/lead_finder.py
------------------------------------
The orchestrator: this is the ONE function the GUI (Phase 2) and the
terminal test script both call. It ties maps_agent.py and
email_crawler.py together and returns a clean list of Lead objects.

Flow:
    1. MapsAgent finds businesses for "<keyword> in <city>" on Google Maps.
    2. For every business that has a website, email_crawler visits it and
       looks for contact emails.
    3. Businesses with NO website still get returned (empty email list) —
       you might still want their name/phone/address, or add an email
       manually later in the review screen (Phase 3).

Step 2 crawls MULTIPLE DIFFERENT websites, so we do it concurrently with a
thread pool — this is safe and doesn't risk any "ban", because each request
goes to a different small business's own server, not to Google.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import Callable, List, Optional

from emailscraper.core.email_crawler import crawl_emails
from emailscraper.core.maps_agent import MapsAgent
from emailscraper.core.places_api_agent import PlacesApiAgent
from emailscraper.models import Lead


def find_leads(
    keyword: str,
    city: str,
    max_results: int = 15,
    headless: bool = True,
    min_delay: float = 1.5,
    max_delay: float = 3.0,
    cooldown_every: int = 5,
    cooldown_seconds: float = 10.0,
    api_key: str = "",
    on_maps_progress: Optional[Callable[[int, int], None]] = None,
    on_email_progress: Optional[Callable[[int, int], None]] = None,
    stop_event: Optional[threading.Event] = None,
) -> List[Lead]:
    """
    Returns a list of Lead objects. See models.py for the Lead fields.

    api_key: leave blank (default) to use the free Playwright Google Maps
        scraper. Paste a Google Places API key to use the official paid
        API instead — faster and no anti-ban tuning needed, but requires
        a billed Google Cloud project. See core/places_api_agent.py.

    The min_delay/max_delay/cooldown_* args are only used on the FREE path
    — see maps_agent.py's __init__ docstring for what each one does.

    stop_event: pass a threading.Event(); if set() while running, we stop
    as soon as practical (after the current listing/website) and return
    whatever leads were collected so far instead of losing everything.
    """
    if api_key.strip():
        source_agent = PlacesApiAgent(api_key=api_key.strip())
        places = source_agent.search(keyword, city, max_results=max_results, progress_cb=on_maps_progress)
        source_label = "Google Places API"
    else:
        maps_agent = MapsAgent(
            headless=headless,
            min_delay=min_delay,
            max_delay=max_delay,
            cooldown_every=cooldown_every,
            cooldown_seconds=cooldown_seconds,
        )
        places = maps_agent.search(
            keyword, city, max_results=max_results, progress_cb=on_maps_progress, stop_event=stop_event
        )
        source_label = "Google Maps (free)"

    # --- Step 2: crawl each business's website for emails (parallel) --------
    leads: List[Lead] = []
    places_with_site = [p for p in places if p.get("website")]
    places_without_site = [p for p in places if not p.get("website")]

    # Businesses with no website: still keep them as leads, just with no
    # emails yet (user can add one manually in Phase 3's review screen).
    for p in places_without_site:
        leads.append(
            Lead(
                business_name=p["name"],
                keyword=keyword,
                city=city,
                website="",
                phone=p.get("phone", ""),
                address=p.get("address", ""),
                emails=[],
                source=source_label,
            )
        )

    done = 0
    total = len(places_with_site)
    already_stopped = stop_event is not None and stop_event.is_set()
    if total and not already_stopped:
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_place = {
                executor.submit(crawl_emails, p["website"]): p for p in places_with_site
            }
            for future in as_completed(future_to_place):
                p = future_to_place[future]
                try:
                    emails = future.result()
                except Exception:
                    emails = []

                leads.append(
                    Lead(
                        business_name=p["name"],
                        keyword=keyword,
                        city=city,
                        website=p["website"],
                        phone=p.get("phone", ""),
                        address=p.get("address", ""),
                        emails=emails,
                        source=source_label,
                    )
                )
                done += 1
                if on_email_progress:
                    on_email_progress(done, total)

                if stop_event is not None and stop_event.is_set():
                    # Cancel whatever hasn't started yet; we already have
                    # results for everything that finished, which is enough
                    # for a clean "stopped early" outcome.
                    for f in future_to_place:
                        f.cancel()
                    break
    elif already_stopped:
        # Stopped before email-crawling even started — still return the
        # businesses Maps found, just without emails (add manually in the
        # review screen if needed) instead of losing them entirely.
        for p in places_with_site:
            leads.append(
                Lead(
                    business_name=p["name"],
                    keyword=keyword,
                    city=city,
                    website=p["website"],
                    phone=p.get("phone", ""),
                    address=p.get("address", ""),
                    emails=[],
                    source=source_label,
                )
            )

    return leads
