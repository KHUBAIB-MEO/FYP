"""
producthunter2/models.py
--------------------------
Data container for one product found while hunting, plus the scores we
compute for it.

Dataclass (not a dict) so VS Code autocomplete works and field typos are
caught early. to_dict() flattens it into one Excel/table row later.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class Product:
    """One trending product + its computed opportunity scores."""

    title: str
    category: str = ""
    price: float = 0.0                 # numeric price for math (0.0 if unknown)
    price_display: str = ""            # original string e.g. "$24.99"
    currency: str = "USD"
    rating: float = 0.0                # star rating 0-5
    num_reviews: int = 0
    rank: int = 0                      # best-seller rank position (1 = top)
    rank_change: str = ""              # e.g. "+12" if it jumped up the charts
    sales_volume: str = ""             # e.g. "500+ bought in past month"
    image_url: str = ""
    product_url: str = ""
    asin: str = ""
    source: str = "Amazon Best Sellers"

    # --- computed by scoring.py (filled in after fetching) ---
    demand_score: float = 0.0          # 0-100
    competition_score: float = 0.0     # 0-100 (higher = LESS competition = better)
    profit_score: float = 0.0          # 0-100
    opportunity_score: float = 0.0     # 0-100 weighted blend of the three
    score_reason: str = ""             # short human-readable explanation

    def to_dict(self) -> dict:
        """Flatten into one row for the results table / Excel export."""
        return {
            "Opportunity": round(self.opportunity_score, 1),
            "Title": self.title,
            "Category": self.category,
            "Price": self.price_display or (f"${self.price:.2f}" if self.price else ""),
            "Rating": self.rating,
            "Reviews": self.num_reviews,
            "Rank": self.rank,
            "Demand": round(self.demand_score, 1),
            "Competition": round(self.competition_score, 1),
            "Profit": round(self.profit_score, 1),
            "Why": self.score_reason,
            "URL": self.product_url,
            "Source": self.source,
        }
