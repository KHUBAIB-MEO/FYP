"""
producthunter2/core/product_fetcher.py
----------------------------------------
Fetches trending/best-selling products.

DATA SOURCES (in priority order):
  1. RapidAPI "Real-Time Amazon Data" — the reliable free path. The free
     tier gives ~100 requests/month, no credit card. User pastes their
     RapidAPI key in the GUI. This returns real, live Amazon best-seller
     data.
  2. Built-in DEMO DATA — if no API key is provided (or the API call
     fails / quota is exhausted), we fall back to a bundled sample set so
     the app ALWAYS produces results. Critical for a viva: the demo can
     never hard-fail just because the internet or a quota is down. The
     source label makes it clear this is sample data, not live.

WHY NOT keyless Amazon scraping like the email scraper does for Maps?
Amazon has far more aggressive anti-bot protection than Google Maps —
a raw keyless scraper breaks constantly and would make the demo unreliable.
The free RapidAPI key is the honest "free but reliable" answer.

EXTENDING WITH NEW SOURCES (e.g. Amazon's official PA-API) LATER:
The dispatch in fetch_products() picks a source based on which credential
is present. To add Amazon's official Product Advertising API in future:
  1. Write a `_fetch_from_amazon_paapi(access_key, secret_key, partner_tag,
     ...)` function here that returns a List[Product] (same shape as
     _fetch_from_rapidapi).
  2. Add its credentials as new optional params to fetch_products().
  3. Add one `elif` branch in fetch_products()'s dispatch below.
Nothing else in the app (scoring, GUI, hunter.py) needs to change, because
every source returns the same Product objects. That's the whole point of
keeping fetching isolated behind this one function.
"""
import time
from typing import Callable, List, Optional

import requests

from producthunter2.models import Product

RAPIDAPI_HOST = "real-time-amazon-data.p.rapidapi.com"
BEST_SELLERS_URL = f"https://{RAPIDAPI_HOST}/best-sellers"

# Amazon category IDs the RapidAPI endpoint understands. Kept in one place
# so it's easy to add more later.
CATEGORY_MAP = {
    "Electronics": "electronics",
    "Home & Kitchen": "home-garden",
    "Toys & Games": "toys-and-games",
    "Beauty": "beauty",
    "Sports & Outdoors": "sports-and-outdoors",
    "Office": "office-products",
}


def _parse_price(raw) -> tuple:
    """Turn '$24.99' (or None) into (24.99, '$24.99'). Returns (0.0, '')."""
    if not raw:
        return 0.0, ""
    display = str(raw)
    digits = display.replace(",", "")
    num = ""
    seen_dot = False
    for c in digits:
        if c.isdigit():
            num += c
        elif c == "." and not seen_dot:
            num += c
            seen_dot = True
    try:
        return (float(num) if num else 0.0), display
    except ValueError:
        return 0.0, display


def fetch_products(
    category: str = "Electronics",
    api_key: str = "",
    max_results: int = 20,
    country: str = "US",
    provider: str = "rapidapi",
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> List[Product]:
    """
    Returns a list of Product objects (UN-scored — scoring.py handles that).

    provider: which data source to use. Currently:
        "rapidapi" -> RapidAPI 'Real-Time Amazon Data' (needs api_key)
        (future)   -> "amazon_paapi" would go here, see module docstring.
    api_key: credential for the chosen provider. Blank -> demo data fallback.

    Any provider failure falls back to demo data rather than crashing, so
    a run never hard-fails.
    """
    # --- Source dispatch: add future providers as new branches here -------
    if provider == "rapidapi" and api_key.strip():
        try:
            return _fetch_from_rapidapi(category, api_key.strip(), max_results, country, progress_cb)
        except Exception as e:
            print(f"[product_fetcher] RapidAPI failed ({e}); using demo data.")
            products = _demo_products(category, max_results)
            for p in products:
                p.source = "Demo data (API call failed)"
            return products

    # elif provider == "amazon_paapi" and access_key and secret_key and partner_tag:
    #     return _fetch_from_amazon_paapi(...)   # future addition

    # No usable credential for the chosen provider -> demo data.
    return _demo_products(category, max_results)


def _fetch_from_rapidapi(category, api_key, max_results, country, progress_cb) -> List[Product]:
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": RAPIDAPI_HOST,
    }
    params = {
        "category": CATEGORY_MAP.get(category, "electronics"),
        "type": "BEST_SELLERS",
        "page": "1",
        "country": country,
    }
    resp = requests.get(BEST_SELLERS_URL, headers=headers, params=params, timeout=20)

    if resp.status_code == 401 or resp.status_code == 403:
        raise RuntimeError("RapidAPI rejected the key — check it's correct and subscribed to the free plan.")
    if resp.status_code == 429:
        raise RuntimeError("RapidAPI free quota reached (100/month). Wait for reset or leave the key blank for demo data.")
    resp.raise_for_status()

    data = resp.json()
    items = data.get("data", {}).get("best_sellers", []) or data.get("data", {}).get("products", [])

    products: List[Product] = []
    for i, item in enumerate(items[:max_results], start=1):
        price, price_display = _parse_price(item.get("product_price"))
        products.append(
            Product(
                title=item.get("product_title", "Unknown product"),
                category=category,
                price=price,
                price_display=price_display,
                rating=float(item.get("product_star_rating") or 0) if item.get("product_star_rating") else 0.0,
                num_reviews=int(item.get("product_num_ratings") or 0),
                rank=int(item.get("rank") or i),
                sales_volume=item.get("sales_volume", "") or "",
                image_url=item.get("product_photo", "") or "",
                product_url=item.get("product_url", "") or "",
                asin=item.get("asin", "") or "",
                source="Amazon Best Sellers (live)",
            )
        )
        if progress_cb:
            progress_cb(i, min(len(items), max_results))

    return products


# ---------------------------------------------------------------------- #
# Bundled demo data — a realistic sample so the app works offline / keyless
# ---------------------------------------------------------------------- #
_DEMO = [
    # (title, price, rating, reviews, rank, sales_volume)
    ("Wireless Earbuds Bluetooth 5.3 with Noise Cancelling", 29.99, 4.4, 340, 1, "2000+ bought in past month"),
    ("Smart LED Strip Lights 32.8ft RGB App Control", 18.99, 4.6, 120, 2, "1000+ bought in past month"),
    ("Portable Mini Bluetooth Speaker Waterproof", 24.99, 4.3, 890, 3, "500+ bought in past month"),
    ("USB C Fast Charger 65W GaN 3-Port", 34.99, 4.7, 210, 4, "800+ bought in past month"),
    ("Stainless Steel Insulated Water Bottle 32oz", 21.99, 4.8, 65, 5, "1500+ bought in past month"),
    ("Magnetic Phone Mount for Car Dashboard", 12.99, 4.2, 15400, 6, "300+ bought in past month"),
    ("LED Ring Light 10 inch with Tripod Stand", 27.99, 4.5, 430, 7, "600+ bought in past month"),
    ("Adjustable Laptop Stand Aluminum Foldable", 39.99, 4.6, 80, 8, "400+ bought in past month"),
    ("Electric Handheld Milk Frother Rechargeable", 15.99, 4.4, 2300, 9, "700+ bought in past month"),
    ("Mechanical Gaming Keyboard RGB 87 Keys", 49.99, 4.5, 45000, 10, "200+ bought in past month"),
    ("Silicone Baking Mat Set Non-Stick (3 Pack)", 13.99, 4.7, 190, 11, "900+ bought in past month"),
    ("Digital Kitchen Scale 11lb High Precision", 11.99, 4.6, 55, 12, "1200+ bought in past month"),
    ("Resistance Bands Set 5-Piece with Handles", 22.99, 4.3, 320, 13, "500+ bought in past month"),
    ("Blue Light Blocking Glasses Anti-Eye Strain", 16.99, 4.1, 8900, 14, "150+ bought in past month"),
    ("Cordless Handheld Vacuum Cleaner for Car", 45.99, 4.4, 140, 15, "350+ bought in past month"),
    ("Reusable Food Storage Bags Silicone (6 Pack)", 19.99, 4.5, 75, 16, "600+ bought in past month"),
    ("Wireless Charging Pad 15W Fast Qi", 17.99, 4.2, 12000, 17, "250+ bought in past month"),
    ("Smart Plug WiFi Outlet Works with Alexa (4 Pack)", 26.99, 4.6, 410, 18, "800+ bought in past month"),
    ("Memory Foam Neck Pillow for Travel", 23.99, 4.3, 260, 19, "450+ bought in past month"),
    ("Collapsible Silicone Travel Coffee Cup", 14.99, 4.7, 40, 20, "550+ bought in past month"),
]


def _demo_products(category: str, max_results: int) -> List[Product]:
    products = []
    for i, (title, price, rating, reviews, rank, vol) in enumerate(_DEMO[:max_results], start=1):
        products.append(
            Product(
                title=title,
                category=category,
                price=price,
                price_display=f"${price:.2f}",
                rating=rating,
                num_reviews=reviews,
                rank=rank,
                sales_volume=vol,
                product_url="https://www.amazon.com/",
                source="Demo data (no API key)",
            )
        )
    return products
