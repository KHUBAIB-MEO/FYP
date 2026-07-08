"""
emailscraper/core/excel_exporter.py
--------------------------------------
Exports the reviewed leads (Phase 3's checkbox table) to a real .xlsx file.

COMPATIBILITY NOTE (why this looks the way it does):
Your existing emailagent/excel_parser.py auto-detects a "Name" column and
an "Email" column by their EXACT header text, and its regex only accepts a
cell containing a SINGLE valid email address — a cell like
"a@x.com, b@x.com" fails that regex and the whole row gets silently
skipped on import.

So this export:
  - uses "Name" / "Email" as headers (not "Business Name") so your Email
    Agent's auto-detect finds them immediately, no manual column picking.
  - writes ONE ROW PER EMAIL ADDRESS — a lead with 2 emails becomes 2 rows.
    This is the only way every email actually survives the round trip into
    your Email Agent.

Leads with NO email (kept only for phone/address as a follow-up list)
still get one row with a blank Email cell — harmless, the Email Agent's
importer just skips rows with no valid email.
"""
from typing import List

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from emailscraper.models import Lead

COLUMNS = ["Name", "Email", "Website", "Phone", "Address", "Keyword", "City", "Source"]


def export_leads_to_excel(leads: List[Lead], filepath: str, only_included: bool = True) -> int:
    """
    Writes `leads` to an .xlsx file at `filepath`. Returns the number of
    rows written.

    only_included=True (default): skips any lead whose Phase 3 checkbox
    was unchecked (lead.include == False) — this is the "discard" action
    actually taking effect.
    """
    rows = []
    for lead in leads:
        if only_included and not lead.include:
            continue

        if lead.emails:
            for email in lead.emails:
                rows.append(_row(lead, email))
        else:
            rows.append(_row(lead, ""))

    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_excel(filepath, index=False, engine="openpyxl")

    _apply_formatting(filepath, len(COLUMNS))

    return len(rows)


def _row(lead: Lead, email: str) -> dict:
    return {
        "Name": lead.business_name,
        "Email": email,
        "Website": lead.website,
        "Phone": lead.phone,
        "Address": lead.address,
        "Keyword": lead.keyword,
        "City": lead.city,
        "Source": lead.source,
    }


def _apply_formatting(filepath: str, num_columns: int) -> None:
    """
    Small polish so the file looks like a finished deliverable, not a raw
    data dump: bold white-on-purple header, auto-fit column widths, and the
    header row frozen so it stays visible while scrolling.
    """
    wb = load_workbook(filepath)
    ws = wb.active

    header_fill = PatternFill(start_color="6366F1", end_color="6366F1", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    for col_idx in range(1, num_columns + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font

    for col_idx in range(1, num_columns + 1):
        letter = get_column_letter(col_idx)
        max_len = max(
            (len(str(ws.cell(row=r, column=col_idx).value or "")) for r in range(1, ws.max_row + 1)),
            default=10,
        )
        ws.column_dimensions[letter].width = min(max(max_len + 2, 12), 50)

    ws.freeze_panes = "A2"
    wb.save(filepath)
