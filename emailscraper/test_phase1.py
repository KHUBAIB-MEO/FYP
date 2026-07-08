"""
emailscraper/test_phase1.py
------------------------------
Proves the Phase 1 scraping engine works — completely on its own, with NO
GUI involved yet. Run this from your FYP project's ROOT folder (the same
folder that has app.py, requirements.txt, venv/).

HOW TO RUN (see chat for full step-by-step setup):
    python -m emailscraper.test_phase1 "software house" "Karachi"

If you don't pass any arguments, it defaults to "software house" / "Karachi".
"""
import sys

from emailscraper.core.lead_finder import find_leads


def main():
    keyword = sys.argv[1] if len(sys.argv) > 1 else "software house"
    city = sys.argv[2] if len(sys.argv) > 2 else "Karachi"

    print(f"Searching Google Maps for '{keyword}' in '{city}'...")
    print("(A Chrome window will open — headless=False so you can watch it work.)\n")

    def maps_progress(current, total):
        print(f"  [Maps]  scraped listing {current}/{total}")

    def email_progress(current, total):
        print(f"  [Email] checked website {current}/{total}")

    leads = find_leads(
        keyword,
        city,
        max_results=10,          # keep small for testing — raise later
        headless=False,          # watch it work for your first runs
        min_delay=1.5,
        max_delay=3.0,
        on_maps_progress=maps_progress,
        on_email_progress=email_progress,
    )

    print(f"\n{'=' * 50}")
    print(f"Found {len(leads)} leads:\n")

    with_email = 0
    for lead in leads:
        has_email = bool(lead.emails)
        with_email += has_email
        print(f"- {lead.business_name}")
        print(f"  Website : {lead.website or 'N/A'}")
        print(f"  Phone   : {lead.phone or 'N/A'}")
        print(f"  Emails  : {', '.join(lead.emails) if lead.emails else 'none found'}")
        print()

    print(f"{'=' * 50}")
    print(f"Summary: {with_email}/{len(leads)} leads had at least one email found.")


if __name__ == "__main__":
    main()
