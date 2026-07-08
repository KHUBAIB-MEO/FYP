"""
producthunter2/test_phase1.py
-------------------------------
Proves the Phase 1 engine works with NO GUI. Run from the project ROOT
(same folder as app.py):

    python -m producthunter2.test_phase1
    python -m producthunter2.test_phase1 "Home & Kitchen"
    python -m producthunter2.test_phase1 "Electronics" YOUR_RAPIDAPI_KEY

With no API key it uses bundled demo data, so it always runs.
"""
import sys

from producthunter2.core.hunter import hunt_products


def main():
    category = sys.argv[1] if len(sys.argv) > 1 else "Electronics"
    api_key = sys.argv[2] if len(sys.argv) > 2 else ""

    print(f"Hunting products in '{category}'"
          f"{' via RapidAPI' if api_key else ' (demo data — no API key)'}...\n")

    def progress(cur, total):
        print(f"  fetched {cur}/{total}")

    products = hunt_products(category, api_key=api_key, max_results=15, on_fetch_progress=progress)

    print(f"\n{'=' * 70}")
    print(f"Top opportunities (sorted best-first):\n")
    for i, p in enumerate(products, start=1):
        print(f"{i:2}. [{p.opportunity_score:5.1f}] {p.title[:50]}")
        print(f"     price {p.price_display or 'N/A':>8} | {p.num_reviews:>6} reviews | rank {p.rank}")
        print(f"     demand {p.demand_score:.0f}  competition {p.competition_score:.0f}  profit {p.profit_score:.0f}")
        print(f"     why: {p.score_reason}")
        print(f"     source: {p.source}")
        print()


if __name__ == "__main__":
    main()
