"""
producthunter2/core/scoring.py
--------------------------------
Rule-based product opportunity scoring. NO AI, NO external calls — pure,
deterministic formulas. This is deliberate:
  - It always works (no Ollama/network dependency).
  - It's 100% explainable in the viva — you can point at the exact formula.
  - It's fast — scores hundreds of products instantly.

THE THREE SUB-SCORES (each 0-100, higher = better opportunity):

1. DEMAND  — are people actually buying / wanting this?
   Signals: best-seller rank (lower rank number = more demand),
   sales volume text ("500+ bought"), and star rating.

2. COMPETITION — how crowded is the market? We INVERT this so higher = better:
   a product with very few reviews but selling well = low competition = HIGH
   score (good). A product with 100k reviews = saturated = LOW score (bad).

3. PROFIT — rough margin potential based on selling price. Mid-priced items
   ($15-$60) tend to have the best margin-vs-shippability balance for a
   reseller; very cheap items have thin margins, very expensive ones sell
   slowly and tie up capital.

OPPORTUNITY = weighted blend of the three (weights explained below).
"""
from typing import List

from producthunter2.models import Product

# How much each sub-score contributes to the final opportunity score.
# Demand weighted highest because "will it sell" matters most; competition
# next; profit last (a great-selling low-competition item is worth chasing
# even at a modest margin). These sum to 1.0.
WEIGHTS = {
    "demand": 0.45,
    "competition": 0.35,
    "profit": 0.20,
}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _demand_score(p: Product) -> float:
    """
    Best-seller rank is the strongest demand signal. Rank 1 is the hottest;
    by ~rank 100 demand has dropped a lot. We map rank -> score on a curve
    so the top ranks are rewarded strongly.
    """
    if p.rank and p.rank > 0:
        # rank 1 -> ~100, rank 50 -> ~50, rank 100 -> ~0 (linear, clamped)
        rank_component = _clamp(100 - (p.rank - 1) * 1.0)
    else:
        rank_component = 40  # unknown rank -> neutral-ish

    # Sales volume text bonus: "500+ bought in past month" etc.
    volume_bonus = 0
    vol = p.sales_volume.lower()
    if "bought" in vol or "sold" in vol:
        digits = "".join(c for c in vol if c.isdigit())
        if digits:
            n = int(digits)
            if n >= 1000:
                volume_bonus = 15
            elif n >= 500:
                volume_bonus = 10
            elif n >= 100:
                volume_bonus = 5

    # Rating nudge: 4.0+ stars adds a little, under 3.0 subtracts.
    rating_adj = 0
    if p.rating >= 4.5:
        rating_adj = 8
    elif p.rating >= 4.0:
        rating_adj = 4
    elif 0 < p.rating < 3.0:
        rating_adj = -8

    return _clamp(rank_component + volume_bonus + rating_adj)


def _competition_score(p: Product) -> float:
    """
    Fewer reviews = less established competition = better opportunity.
    We invert review count into a 0-100 score. Thresholds are rough
    industry rules of thumb for reseller product research.
    """
    r = p.num_reviews
    if r <= 0:
        return 60  # unknown -> mildly favorable (benefit of the doubt)
    if r < 100:
        base = 95      # barely any competition
    elif r < 500:
        base = 85
    elif r < 2000:
        base = 70
    elif r < 10000:
        base = 45
    elif r < 50000:
        base = 25
    else:
        base = 10      # extremely saturated

    return _clamp(base)


def _profit_score(p: Product) -> float:
    """
    Sweet-spot pricing for a reseller: mid-priced items score highest.
    Too cheap = thin margins after fees/shipping; too expensive = slow
    to sell and ties up capital.
    """
    price = p.price
    if price <= 0:
        return 50  # unknown price -> neutral

    if 15 <= price <= 60:
        return 90      # ideal margin/shippability band
    if 8 <= price < 15:
        return 65
    if 60 < price <= 120:
        return 60
    if price < 8:
        return 35      # margins too thin
    # price > 120
    return 40          # high capital tie-up, slower sales


def _reason(p: Product) -> str:
    """One-line human-readable justification for the top-line score."""
    bits = []
    if p.rank and p.rank <= 20:
        bits.append(f"top-{p.rank} best seller")
    if p.num_reviews and p.num_reviews < 500:
        bits.append("low competition")
    elif p.num_reviews and p.num_reviews > 20000:
        bits.append("saturated market")
    if 15 <= p.price <= 60:
        bits.append("good price band")
    if p.rating >= 4.5:
        bits.append("highly rated")
    if not bits:
        bits.append("moderate opportunity")
    return ", ".join(bits)


def score_product(p: Product) -> Product:
    """Fills in all four score fields + reason on a single Product, in place."""
    p.demand_score = _demand_score(p)
    p.competition_score = _competition_score(p)
    p.profit_score = _profit_score(p)
    p.opportunity_score = _clamp(
        p.demand_score * WEIGHTS["demand"]
        + p.competition_score * WEIGHTS["competition"]
        + p.profit_score * WEIGHTS["profit"]
    )
    p.score_reason = _reason(p)
    return p


def score_all(products: List[Product]) -> List[Product]:
    """Scores every product, then returns them sorted best-opportunity-first."""
    for p in products:
        score_product(p)
    return sorted(products, key=lambda x: x.opportunity_score, reverse=True)
