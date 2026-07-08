"""
producthunter2/core/hunter.py
-------------------------------
The orchestrator — the ONE function the GUI and terminal test both call.
Fetches products from the chosen source, scores them all, returns them
sorted best-opportunity-first.
"""
from typing import Callable, List, Optional

from producthunter2.core.product_fetcher import fetch_products
from producthunter2.core.scoring import score_all
from producthunter2.models import Product


def hunt_products(
    category: str = "Electronics",
    api_key: str = "",
    max_results: int = 20,
    country: str = "US",
    provider: str = "rapidapi",
    on_fetch_progress: Optional[Callable[[int, int], None]] = None,
) -> List[Product]:
    """
    Returns scored, ranked Product objects.

    api_key: RapidAPI key. Blank -> bundled demo data (app still works).
    provider: data source id (see product_fetcher.fetch_products). Kept as a
        param now so future sources (e.g. Amazon's official PA-API) need no
        signature change here.
    """
    products = fetch_products(
        category=category,
        api_key=api_key,
        max_results=max_results,
        country=country,
        provider=provider,
        progress_cb=on_fetch_progress,
    )
    return score_all(products)
