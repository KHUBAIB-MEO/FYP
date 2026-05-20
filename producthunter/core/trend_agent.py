"""
Trend Agent — Phase 4
=====================
Fetches Google Trends data for Pakistan (geo='PK') using pytrends.
Assigns trend_score 0–100 to each product.
Works completely offline after initial data fetch.
"""
import time
from typing import List, Dict
from producthunter.models.product import Product


class TrendAgent:
    """
    Wraps pytrends to get search interest from Google Trends.

    Usage:
        agent = TrendAgent()
        scores = agent.get_scores(["wireless earbuds", "phone case"])
    """

    def __init__(self, geo: str = "PK", timeframe: str = "today 3-m"):
        self.geo = geo
        self.timeframe = timeframe
        self._pytrends = None

    def _get_client(self):
        """Lazy-load pytrends so the app starts even if pytrends isn't installed."""
        if self._pytrends is None:
            from pytrends.request import TrendReq
            self._pytrends = TrendReq(hl="en-US", tz=300, timeout=(10, 25),
                                      retries=2, backoff_factor=0.5)
        return self._pytrends

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #
    def get_scores(self, keywords: List[str]) -> Dict[str, float]:
        """
        Return {keyword: trend_score} for up to 5 keywords at a time.
        Google Trends only accepts max 5 keywords per request — we batch.
        """
        if not keywords:
            return {}

        scores = {}
        # Batch into groups of 5 (Google Trends limit)
        batches = [keywords[i:i + 5] for i in range(0, len(keywords), 5)]

        for batch in batches:
            try:
                pt = self._get_client()
                pt.build_payload(batch, geo=self.geo, timeframe=self.timeframe)
                data = pt.interest_over_time()

                if data.empty:
                    for kw in batch:
                        scores[kw] = 0.0
                else:
                    for kw in batch:
                        if kw in data.columns:
                            # Mean of the last 12 weeks, normalised 0–100
                            scores[kw] = float(data[kw].mean())
                        else:
                            scores[kw] = 0.0

                time.sleep(1)  # Avoid rate limiting

            except Exception as e:
                print(f"[TrendAgent] Error fetching trends: {e}")
                for kw in batch:
                    scores[kw] = 0.0

        return scores

    def enrich_products(self, products: List[Product],
                        progress_cb=None) -> List[Product]:
        """
        Attach trend_score to each Product in the list.
        Uses the product title as the search keyword.
        """
        # Use first 5 words of title as keyword (cleaner search)
        keywords = [" ".join(p.title.split()[:5]) for p in products]
        total = len(keywords)

        scores_map = {}
        batches = [keywords[i:i + 5] for i in range(0, total, 5)]

        for idx, batch in enumerate(batches):
            batch_scores = self.get_scores(batch)
            scores_map.update(batch_scores)
            if progress_cb:
                progress_cb(min((idx + 1) * 5, total), total)

        for i, p in enumerate(products):
            kw = keywords[i]
            p.trend_score = scores_map.get(kw, 0.0)

        return products

    def get_related_keywords(self, keyword: str) -> List[str]:
        """Return rising related queries from Google Trends."""
        try:
            pt = self._get_client()
            pt.build_payload([keyword], geo=self.geo, timeframe=self.timeframe)
            related = pt.related_queries()
            rising = related.get(keyword, {}).get("rising")
            if rising is not None and not rising.empty:
                return rising["query"].tolist()[:10]
        except Exception as e:
            print(f"[TrendAgent] Related keywords error: {e}")
        return []