"""
emailscraper/core/email_crawler.py
------------------------------------
Given a business website URL, visits a few likely pages (home, contact,
about) and pulls out any email addresses it finds.

100% free — just `requests` + `BeautifulSoup`, same libraries producthunter's
scraper_agent.py already uses in this project. No paid API, no browser
needed here (a plain HTML fetch is enough for normal business websites,
unlike Google Maps which needed Playwright).

NOTE ON POLITENESS: each business website is a separate small server, not
Google, so the "get banned" risk is much lower here. Still, we keep a short
delay between the 2-3 pages we check on the SAME site so we don't hammer
someone's small business server with rapid requests.
"""
import random
import re
import time
from typing import List
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Pages most likely to list a real contact email, checked in this order.
CANDIDATE_PATHS = ["", "/contact", "/contact-us", "/about", "/about-us"]

# Standard email regex: local-part @ domain . tld
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# Emails ending in these extensions are false positives from the regex
# matching things like "icon@2x.png" inside a stylesheet/JS file.
JUNK_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js")

# Domains that show up constantly but are never a real business contact —
# tracking pixels, placeholder/example addresses, website-builder plumbing.
JUNK_DOMAINS = (
    "sentry.io", "wixpress.com", "example.com", "yourdomain.com",
    "domain.com", "schema.org", "godaddy.com", "cloudflare.com",
    "w3.org", "gstatic.com", "google.com",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def _is_valid_email(email: str) -> bool:
    email = email.lower()
    if email.endswith(JUNK_EXTENSIONS):
        return False
    if any(junk in email for junk in JUNK_DOMAINS):
        return False
    return True


def _extract_emails_from_html(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")

    found = set()

    # 1. mailto: links — most reliable source, these are deliberately
    #    published by the business ("Email us: <a href='mailto:...'>")
    for tag in soup.select('a[href^="mailto:"]'):
        addr = tag["href"].replace("mailto:", "").split("?")[0].strip()
        if addr:
            found.add(addr)

    # 2. Plain text on the page (footers often just write the email as text)
    for match in EMAIL_REGEX.findall(soup.get_text(" ")):
        found.add(match)

    return [e for e in found if _is_valid_email(e)]


def crawl_emails(website: str, min_delay: float = 1.0, max_delay: float = 2.0) -> List[str]:
    """
    Visits up to len(CANDIDATE_PATHS) pages on `website` and returns a
    deduplicated list of emails found across all of them.
    """
    if not website:
        return []

    if not website.startswith(("http://", "https://")):
        website = "https://" + website

    parsed = urlparse(website)
    base = f"{parsed.scheme}://{parsed.netloc}"

    all_emails = set()

    for i, path in enumerate(CANDIDATE_PATHS):
        url = urljoin(base, path)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=8)
            if resp.status_code == 200:
                emails = _extract_emails_from_html(resp.text)
                all_emails.update(emails)
        except requests.RequestException:
            # Site down, SSL error, DNS failure, etc — just skip this page.
            continue

        # Small delay between pages on the SAME site (skip after last page)
        if i < len(CANDIDATE_PATHS) - 1:
            time.sleep(random.uniform(min_delay, max_delay))

        # Early exit once we've found something on the homepage or contact
        # page — no need to check every remaining path.
        if all_emails and path in ("", "/contact", "/contact-us"):
            break

    return sorted(all_emails)
