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
from typing import Callable, List, Optional

from emailscraper.core.email_crawler import crawl_emails
from emailscraper.core.maps_agent import MapsAgent
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
    on_maps_progress: Optional[Callable[[int, int], None]] = None,
    on_email_progress: Optional[Callable[[int, int], None]] = None,
) -> List[Lead]:
    """
    Returns a list of Lead objects. See models.py for the Lead fields.

    The min_delay/max_delay/cooldown_* args are passed straight through to
    MapsAgent — see maps_agent.py's __init__ docstring for what each one
    does. Widen them if you're scraping a lot in one session.
    """
    maps_agent = MapsAgent(
        headless=headless,
        min_delay=min_delay,
        max_delay=max_delay,
        cooldown_every=cooldown_every,
        cooldown_seconds=cooldown_seconds,
    )

    # --- Step 1: Google Maps -------------------------------------------------
    places = maps_agent.search(keyword, city, max_results=max_results, progress_cb=on_maps_progress)

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
            )
        )

    done = 0
    total = len(places_with_site)
    if total:
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
                    )
                )
                done += 1
                if on_email_progress:
                    on_email_progress(done, total)

    return leads
