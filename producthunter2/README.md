# Product Hunter Agent (v2)

Part of **AI TASKFORCE**. Finds trending best-seller products, scores each
for opportunity (demand vs competition vs profit) with a transparent
rule-based formula, and lets you shortlist, export, or send the winners
straight to the Content Scripting agent for ad copy.

## What it does

1. Fetches best-seller products for a chosen category + marketplace.
2. Scores each product 0–100 on **demand**, **competition**, and **profit**,
   then blends them into one **opportunity** score and sorts best-first.
3. Shows them in a review table — keep/discard checkboxes, color-coded
   scores (green/amber/grey).
4. Exports the kept products to a formatted Excel report, or sends the top
   pick to the Content agent to auto-write marketing copy.

## Folder structure

```
producthunter2/
├── __init__.py
├── models.py                  Product dataclass (data + computed scores)
├── producthunter2_page.py     PyQt6 GUI page (the dashboard tile)
├── test_phase1.py             Terminal-only engine test, no GUI
└── core/
    ├── product_fetcher.py     Data source: RapidAPI + offline demo fallback
    ├── scoring.py             Rule-based opportunity scoring
    ├── hunter.py              Orchestrates fetch + score
    └── excel_exporter.py      Writes the shortlist to a formatted .xlsx
```

## Setup

```
pip install requests pandas openpyxl
```
(All likely already installed for the rest of the project.)

## Data sources — free but reliable

| Source | When used | Cost |
|---|---|---|
| **RapidAPI 'Real-Time Amazon Data'** | when a key is pasted in the GUI | free tier ~100 req/month, no card |
| **Bundled demo data** | when no key / API fails / quota hit | always free, works offline |

The demo-data fallback is deliberate: the app **never hard-fails** in a
viva, even with no internet or an exhausted quota. The source label in the
table always shows which one produced the results, so it's never misleading.

**Why not keyless Amazon scraping** (like the email scraper does for Maps)?
Amazon's anti-bot protection is far more aggressive than Google Maps — a raw
keyless scraper breaks constantly. A free RapidAPI key is the honest
"free but reliable" answer.

## Scoring formula (rule-based, fully explainable)

Each product gets three 0–100 sub-scores (all in `scoring.py`):

- **Demand (weight 0.45)** — best-seller rank (lower rank = more demand),
  sales-volume text ("500+ bought"), and star rating.
- **Competition (weight 0.35)** — *inverted* review count: fewer reviews =
  less established competition = higher score. A 45k-review product is
  saturated and scores low even at a great rank.
- **Profit (weight 0.20)** — price sweet-spot: $15–60 scores highest (best
  margin-vs-shippability for a reseller); too cheap = thin margins, too
  expensive = slow-moving and ties up capital.

`opportunity = 0.45·demand + 0.35·competition + 0.20·profit`

No AI, no network — deterministic, instant, and you can point at the exact
formula in the viva.

## Extending with new data sources later

`product_fetcher.fetch_products()` uses a `provider` dispatch. To add
Amazon's official Product Advertising API (PA-API) in future:
1. Write `_fetch_from_amazon_paapi(...)` returning `List[Product]`.
2. Add its credentials as params + one `elif` branch in the dispatch.
Nothing else (scoring, GUI, export) changes, because every source returns
the same `Product` objects. The slot is already marked in the code.

## Integration points

- **Excel export** — `excel_exporter.py`, kept products only, formatted sheet.
- **Send to Content agent** — emits `sendToContentAgent` with a ready-made
  `{topic, keywords}` prompt built from the top kept product; MainWindow
  hands it to `ContentPage`, which pre-fills its fields. One click from
  "found a winner" to "writing its ad copy".

## Threading model

Fetching runs on a `QThread` via a `HuntWorker` (QObject), same pattern as
the other agents, so the GUI never freezes. Progress/results/errors come
back through Qt signals.

## Known limitations

- Free RapidAPI tier is ~100 requests/month — heavy use needs a paid plan
  or falls back to demo data.
- Scoring thresholds are reasonable rules-of-thumb, not guarantees — they
  rank *relative* opportunity, they don't predict actual sales.
- Profit scoring is price-band based; it doesn't know real sourcing cost
  (that needs a supplier-side data source, a possible future addition).
