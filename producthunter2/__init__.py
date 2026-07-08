"""
producthunter2 package
------------------------
Second-generation Product Hunter agent for AI TASKFORCE. Finds trending /
best-selling products, scores each one for opportunity (demand vs
competition vs profit) using a transparent rule-based formula, and shows
them in a reviewable, exportable table.

Structure mirrors the emailscraper agent:
    producthunter2/
        __init__.py
        models.py                 -> Product dataclass
        core/
            __init__.py
            product_fetcher.py     -> free data source (RapidAPI + demo fallback)
            scoring.py             -> rule-based opportunity scoring
            hunter.py              -> orchestrates fetch + score
        test_phase1.py             -> terminal test, no GUI
        producthunter2_page.py     -> PyQt6 GUI page (Phase 2+)
"""
