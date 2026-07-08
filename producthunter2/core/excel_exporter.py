"""
producthunter2/core/excel_exporter.py
----------------------------------------
Exports the reviewed product shortlist (checkbox table) to a formatted
.xlsx file — a clean deliverable for market-research reports.

Same style as the emailscraper's exporter: bold header, auto-fit columns,
frozen header row. Only exports products the user kept (checkbox checked).
"""
from typing import List

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from producthunter2.models import Product

COLUMNS = [
    "Opportunity", "Title", "Category", "Price", "Rating", "Reviews",
    "Rank", "Demand", "Competition", "Profit", "Why", "URL", "Source",
]


def export_products_to_excel(products: List[Product], filepath: str, only_included=None) -> int:
    """
    Writes products to an .xlsx. Returns the number of rows written.

    only_included: optional list[bool] parallel to products (True = keep).
    If None, all products are exported.
    """
    rows = []
    for i, p in enumerate(products):
        if only_included is not None and i < len(only_included) and not only_included[i]:
            continue
        rows.append(p.to_dict())

    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_excel(filepath, index=False, engine="openpyxl")
    _apply_formatting(filepath, len(COLUMNS))
    return len(rows)


def _apply_formatting(filepath: str, num_columns: int) -> None:
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
        ws.column_dimensions[letter].width = min(max(max_len + 2, 12), 55)

    ws.freeze_panes = "A2"
    wb.save(filepath)
