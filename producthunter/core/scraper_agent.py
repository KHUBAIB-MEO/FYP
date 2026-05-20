"""
Scraper Agent — Phase 2
========================
Scrapes trending products from Reddit (free JSON API),
Google Shopping, Amazon, and AliExpress using requests + BeautifulSoup.
No paid API keys needed.
"""
import requests
import time
import random
from bs4 import BeautifulSoup
from typing import List, Callable, Optional
from producthunter.models.product import Product


# Rotate user-agents to avoid getting blocked
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) "
    "Gecko/20100101 Firefox/121.0",
]


def _headers() -> dict:
    """Return randomised headers to mimic a real browser."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


class ScraperAgent:
    """
    Scrapes product data from multiple free sources.

    Usage:
        agent = ScraperAgent()
        products = agent.scrape("reddit", keyword="trending gadgets", max_pages=2)
    """

    SUPPORTED_SOURCES = ["reddit", "amazon", "aliexpress"]

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    # ------------------------------------------------------------------ #
    # Public entry point                                                   #
    # ------------------------------------------------------------------ #
    def scrape(self, source: str, keyword: str = "",
               max_pages: int = 2,
               progress_cb: Optional[Callable] = None) -> List[Product]:
        """
        Unified scrape entry point.

        Args:
            source:      'reddit' | 'amazon' | 'aliexpress'
            keyword:     search term e.g. 'wireless earbuds'
            max_pages:   result pages to scrape
            progress_cb: optional callback(current_page, total_pages)
        """
        source = source.lower()
        try:
            if source == "reddit":
                return self.scrape_reddit(keyword, max_pages, progress_cb)
            elif source == "amazon":
                return self.scrape_amazon(keyword, max_pages, progress_cb)
            elif source == "aliexpress":
                return self.scrape_aliexpress(keyword, max_pages, progress_cb)
            else:
                raise ValueError(f"Unknown source '{source}'.")
        except Exception as e:
            print(f"[ScraperAgent] Error scraping {source}: {e}")
            return []

    # ------------------------------------------------------------------ #
    # Reddit — uses public JSON API, no auth needed                       #
    # ------------------------------------------------------------------ #
    def scrape_reddit(self, keyword: str = "",
                      max_pages: int = 2,
                      progress_cb=None) -> List[Product]:
        """
        Scrapes Reddit subreddits for trending product mentions.
        Uses Reddit's free .json endpoint — no API key required.
        """
        subreddits = ["deals", "BuyItForLife", "shutupandtakemymoney",
                      "ProductPorn", "gadgets"]
        products = []
        seen_titles = set()

        for i, sub in enumerate(subreddits[:max_pages * 2]):
            if progress_cb:
                progress_cb(i + 1, len(subreddits[:max_pages * 2]))

            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=25"
            if keyword:
                url = (f"https://www.reddit.com/r/{sub}/search.json"
                       f"?q={keyword}&sort=hot&limit=25&restrict_sr=1")
            try:
                resp = requests.get(url, headers=_headers(), timeout=self.timeout)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                posts = data.get("data", {}).get("children", [])

                for post in posts:
                    d = post.get("data", {})
                    title = d.get("title", "").strip()
                    score = d.get("score", 0)
                    num_comments = d.get("num_comments", 0)

                    # Skip non-product posts
                    if not title or len(title) < 10:
                        continue
                    if title.lower() in seen_titles:
                        continue
                    seen_titles.add(title.lower())

                    # Estimate sold_count from upvotes + comments
                    engagement = score + (num_comments * 5)

                    p = Product(
                        title=title[:200],
                        category=sub,
                        price=0.0,
                        currency="PKR",
                        rating=min(5.0, score / 1000),
                        reviews=num_comments,
                        sold_count=engagement,
                        source="reddit",
                        url=f"https://reddit.com{d.get('permalink', '')}",
                    )
                    products.append(p)

                time.sleep(1.5)  # Be polite to Reddit
            except Exception as e:
                print(f"[ScraperAgent] Reddit r/{sub} error: {e}")
                continue

        return self._deduplicate(products)

    # ------------------------------------------------------------------ #
    # Amazon — BeautifulSoup scraper                                      #
    # ------------------------------------------------------------------ #
    def scrape_amazon(self, keyword: str,
                      max_pages: int = 2,
                      progress_cb=None) -> List[Product]:
        """
        Scrapes Amazon search results.
        Note: Amazon may block scrapers — retry or rotate agents if needed.
        """
        products = []
        seen = set()

        for page in range(1, max_pages + 1):
            if progress_cb:
                progress_cb(page, max_pages)

            url = (f"https://www.amazon.com/s?k={keyword.replace(' ', '+')}"
                   f"&page={page}")
            try:
                resp = requests.get(url, headers=_headers(), timeout=self.timeout)
                soup = BeautifulSoup(resp.text, "html.parser")

                # Each product card on Amazon search
                items = soup.select("div[data-component-type='s-search-result']")

                for item in items:
                    title_el = item.select_one("h2 a span")
                    price_el = item.select_one(".a-price .a-offscreen")
                    rating_el = item.select_one(".a-icon-alt")
                    reviews_el = item.select_one(".a-size-base.s-underline-text")
                    link_el = item.select_one("h2 a")

                    title = title_el.text.strip() if title_el else ""
                    if not title or title in seen:
                        continue
                    seen.add(title)

                    # Parse price (remove currency symbols)
                    raw_price = price_el.text.strip() if price_el else "0"
                    price = self._parse_price(raw_price)

                    # Parse rating e.g. "4.5 out of 5 stars"
                    raw_rating = rating_el.text if rating_el else "0"
                    rating = float(raw_rating.split()[0]) if raw_rating else 0.0

                    # Parse review count
                    raw_reviews = reviews_el.text.replace(",", "") if reviews_el else "0"
                    reviews = int(raw_reviews) if raw_reviews.isdigit() else 0

                    link = ("https://amazon.com" + link_el["href"]
                            if link_el else "")

                    p = Product(
                        title=title[:200],
                        category=keyword,
                        price=price * 280,   # Approx USD → PKR conversion
                        currency="PKR",
                        rating=rating,
                        reviews=reviews,
                        sold_count=reviews * 3,  # Estimate
                        source="amazon",
                        url=link,
                    )
                    products.append(p)

                time.sleep(2)
            except Exception as e:
                print(f"[ScraperAgent] Amazon page {page} error: {e}")
                continue

        return self._deduplicate(products)

    # ------------------------------------------------------------------ #
    # AliExpress — BeautifulSoup scraper                                  #
    # ------------------------------------------------------------------ #
    def scrape_aliexpress(self, keyword: str,
                          max_pages: int = 2,
                          progress_cb=None) -> List[Product]:
        """
        Scrapes AliExpress search results.
        AliExpress is JS-heavy — this gets basic data from meta tags.
        Full JS rendering requires Selenium (Phase 3 upgrade).
        """
        products = []
        seen = set()

        for page in range(1, max_pages + 1):
            if progress_cb:
                progress_cb(page, max_pages)

            url = (f"https://www.aliexpress.com/wholesale"
                   f"?SearchText={keyword.replace(' ', '+')}&page={page}")
            try:
                resp = requests.get(url, headers=_headers(), timeout=self.timeout)
                soup = BeautifulSoup(resp.text, "html.parser")

                # AliExpress renders items in script tags as JSON
                # We extract whatever product titles we can from meta/links
                items = soup.select("a[href*='/item/']")

                for item in items:
                    title = item.get("title", "") or item.text.strip()
                    href = item.get("href", "")

                    if not title or len(title) < 8 or title in seen:
                        continue
                    seen.add(title)

                    p = Product(
                        title=title[:200],
                        category=keyword,
                        price=0.0,
                        currency="PKR",
                        rating=0.0,
                        reviews=0,
                        sold_count=0,
                        source="aliexpress",
                        url=href if href.startswith("http") else f"https:{href}",
                    )
                    products.append(p)

                time.sleep(2)
            except Exception as e:
                print(f"[ScraperAgent] AliExpress page {page} error: {e}")
                continue

        return self._deduplicate(products)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #
    def _parse_price(self, raw: str) -> float:
        """Convert '$12.99' or 'Rs. 1,200' → float."""
        import re
        cleaned = re.sub(r"[^\d.]", "", raw)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _deduplicate(self, products: List[Product]) -> List[Product]:
        """Remove products with duplicate titles (case-insensitive)."""
        seen = set()
        unique = []
        for p in products:
            key = p.title.lower().strip()
            if key not in seen and len(key) > 5:
                seen.add(key)
                unique.append(p)
        return unique