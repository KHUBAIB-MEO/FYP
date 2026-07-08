"""
emailscraper package
----------------------
New agent for the FYP: finds businesses on Google Maps for a keyword+city,
then crawls each business website for contact emails.

Folder layout (matches the style of producthunter/ and emailagent/):
    emailscraper/
        __init__.py
        models.py              -> Lead data class
        core/
            __init__.py
            maps_agent.py       -> Phase 1: Google Maps scraper (Playwright)
            email_crawler.py    -> Phase 1: website email extractor (requests+BS4)
            lead_finder.py      -> Phase 1: orchestrates the two above
        test_phase1.py          -> Phase 1: terminal test, no GUI needed
        emailscraper_page.py    -> Phase 2+: PyQt6 GUI page (added later)
"""
