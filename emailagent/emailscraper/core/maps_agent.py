"""
emailscraper/core/maps_agent.py
---------------------------------
Scrapes business listings (name, website, phone, address) from Google Maps
for a given keyword + city, e.g. keyword="software house", city="Karachi".

WHY PLAYWRIGHT (not requests + BeautifulSoup like producthunter's scraper_agent.py):
Google Maps is a JavaScript-heavy single-page app — the HTML you'd get from a
plain `requests.get()` is basically empty. We need a real browser to render the
page and scroll through results, which is exactly what Playwright gives us.

HOW IT WORKS (high level):
    1. Open https://www.google.com/maps/search/<keyword in city>
    2. Scroll the results panel until we have enough listings (Maps lazy-loads
       more cards as you scroll, like Instagram's infinite feed).
    3. Collect the URL of each listing.
    4. Visit each listing's page directly and read its name/website/phone/address
       from Google's info panel.

NOTE FOR VIVA: Google occasionally changes its internal HTML attribute names.
Every selector Google Maps depends on lives in ONE place — the SELECTORS dict
below — so if scraping breaks in the future, this is the only place to fix.
"""
import random
import time
from typing import Callable, List, Optional

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

# Small pool of real, current desktop user-agents. Picking one at random each
# run (instead of always sending the same string) makes traffic look less
# like a bot and more like "some person's Chrome browser".
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# The single biggest tell that a browser is automated is the JS property
# `navigator.webdriver === true`. Google (and most sites) check this. We
# inject a tiny script into every page BEFORE any of Google's JS runs, that
# makes this property look normal. This is a standard, legal fingerprint
# tweak — we're not bypassing a login or paywall, just browsing public map
# data without an obvious "I am a bot" flag.
STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
"""

# Everything Google-Maps-HTML-specific is isolated here on purpose (see note above).
SELECTORS = {
    "feed": 'div[role="feed"]',                       # the scrollable results panel
    "listing_link": 'div[role="feed"] a[href*="/maps/place/"]',
    "name": "h1",                                      # business name on the detail panel
    "website": 'a[data-item-id="authority"]',          # the "Website" button
    "phone": 'button[data-item-id^="phone:tel:"]',      # the "Phone" button
    "address": 'button[data-item-id="address"]',        # the "Address" button
}


class MapsAgent:
    """
    Usage:
        agent = MapsAgent(headless=True)
        places = agent.search("software house", "Karachi", max_results=15)
    """

    def __init__(
        self,
        headless: bool = True,
        nav_timeout_ms: int = 20000,
        min_delay: float = 1.5,
        max_delay: float = 3.0,
        cooldown_every: int = 5,
        cooldown_seconds: float = 10.0,
    ):
        """
        headless        : False = you SEE the Chrome window while it scrapes
                           (good for your first few test runs / viva demo).
                           True  = runs invisibly in the background (faster,
                           use once you trust it works).
        nav_timeout_ms  : how long to wait for a page to load before giving up.
        min_delay/max_delay : after each listing, we sleep a random number of
                           seconds in this range. Bigger range = slower but
                           safer. 1.5-3.0s is a reasonable default; if you're
                           scraping a lot in one sitting, widen this (e.g.
                           3.0-6.0) to look more human.
        cooldown_every  : every N listings, take a longer break.
        cooldown_seconds: length of that longer break, in seconds.
        """
        self.headless = headless
        self.nav_timeout_ms = nav_timeout_ms
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.cooldown_every = cooldown_every
        self.cooldown_seconds = cooldown_seconds

    def _human_delay(self) -> None:
        """Short randomized pause — call this between actions."""
        time.sleep(random.uniform(self.min_delay, self.max_delay))

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #
    def search(
        self,
        keyword: str,
        city: str,
        max_results: int = 15,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> List[dict]:
        """
        Returns a list of dicts: {name, website, phone, address}
        (no emails yet — that's core/email_crawler.py's job)
        """
        query = f"{keyword} in {city}"
        results: List[dict] = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=self.headless,
                # This flag removes the specific Chrome automation banner/flag
                # that some sites check for.
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1366, "height": 900},
                locale="en-US",
            )
            # Runs before any page JS — masks navigator.webdriver on every
            # page this context ever opens.
            context.add_init_script(STEALTH_INIT_SCRIPT)

            page = context.new_page()
            page.set_default_timeout(self.nav_timeout_ms)

            try:
                listing_urls = self._collect_listing_urls(page, query, max_results)

                for i, url in enumerate(listing_urls, start=1):
                    place = self._scrape_listing(page, url)
                    if place:
                        results.append(place)
                    if progress_cb:
                        progress_cb(i, len(listing_urls))

                    # Every `cooldown_every` listings, take a longer break —
                    # this breaks up the steady, robotic request pattern that
                    # rate-limiters look for. Otherwise just a normal
                    # human-like pause between listings.
                    if i % self.cooldown_every == 0 and i != len(listing_urls):
                        cooldown = self.cooldown_seconds + random.uniform(0, 4)
                        if progress_cb:
                            print(f"[MapsAgent] Cooling down for {cooldown:.1f}s...")
                        time.sleep(cooldown)
                    else:
                        self._human_delay()

            finally:
                browser.close()

        return results

    # ------------------------------------------------------------------ #
    # Step 1: scroll the results feed and collect listing URLs
    # ------------------------------------------------------------------ #
    def _collect_listing_urls(self, page, query: str, max_results: int) -> List[str]:
        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        page.goto(search_url)

        try:
            page.wait_for_selector(SELECTORS["feed"], timeout=self.nav_timeout_ms)
        except PWTimeoutError:
            # Google sometimes shows a single result directly (no feed panel) —
            # in that case just use the current page's URL as the only listing.
            return [page.url]

        feed = page.query_selector(SELECTORS["feed"])
        collected_urls: List[str] = []
        stale_scrolls = 0  # counts consecutive scrolls that found nothing new

        while len(collected_urls) < max_results and stale_scrolls < 5:
            links = page.query_selector_all(SELECTORS["listing_link"])
            urls = []
            for link in links:
                href = link.get_attribute("href")
                if href and href not in urls:
                    urls.append(href)

            new_count = len(set(urls) - set(collected_urls))
            collected_urls = list(dict.fromkeys(urls))  # dedupe, keep order

            stale_scrolls = 0 if new_count > 0 else stale_scrolls + 1

            # Scroll the feed panel down (NOT the whole page — the feed is its
            # own inner scrollable div)
            feed.hover()
            page.mouse.wheel(0, 2000)
            self._human_delay()

        return collected_urls[:max_results]

    # ------------------------------------------------------------------ #
    # Step 2: open one listing and read its details
    # ------------------------------------------------------------------ #
    def _scrape_listing(self, page, url: str) -> Optional[dict]:
        try:
            page.goto(url)
            page.wait_for_selector(SELECTORS["name"], timeout=self.nav_timeout_ms)

            name_el = page.query_selector(SELECTORS["name"])
            name = name_el.inner_text().strip() if name_el else "Unknown"

            website_el = page.query_selector(SELECTORS["website"])
            website = website_el.get_attribute("href") if website_el else ""

            phone_el = page.query_selector(SELECTORS["phone"])
            phone = ""
            if phone_el:
                # aria-label looks like "Phone: 021 1234 5678" — strip the label
                aria = phone_el.get_attribute("aria-label") or ""
                phone = aria.replace("Phone:", "").strip()

            address_el = page.query_selector(SELECTORS["address"])
            address = ""
            if address_el:
                aria = address_el.get_attribute("aria-label") or ""
                address = aria.replace("Address:", "").strip()

            return {
                "name": name,
                "website": website or "",
                "phone": phone,
                "address": address,
            }

        except PWTimeoutError:
            print(f"[MapsAgent] Timed out loading listing, skipping: {url}")
            return None
        except Exception as e:
            print(f"[MapsAgent] Error scraping listing ({url}): {e}")
            return None
