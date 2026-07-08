"""
emailscraper/models.py
------------------------
Simple data container for one scraped lead (a business + whatever
email(s) we managed to find for it).

We use a dataclass instead of a plain dict because:
  1. Autocomplete works in VS Code (lead.business_name instead of lead["business_name"])
  2. It's harder to make a typo in a field name
  3. to_dict() below makes it trivial to turn a list of Leads into
     an Excel sheet in Phase 4 (pandas.DataFrame(list_of_dicts))
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class Lead:
    """One business found while scraping, plus the emails we found for it."""

    business_name: str
    keyword: str                            # search term used, e.g. "software house"
    city: str                               # e.g. "Karachi"
    website: str = ""                       # blank if Google Maps had no website listed
    phone: str = ""
    address: str = ""
    emails: List[str] = field(default_factory=list)
    source: str = "Google Maps"
    include: bool = True                    # Phase 3 checkbox state (keep/discard) lives here

    def to_dict(self) -> dict:
        """Flatten this Lead into a dict — one row of the Excel export (Phase 4)."""
        return {
            "Include": self.include,
            "Business Name": self.business_name,
            "Email": ", ".join(self.emails) if self.emails else "",
            "Website": self.website,
            "Phone": self.phone,
            "Address": self.address,
            "Keyword": self.keyword,
            "City": self.city,
            "Source": self.source,
        }
