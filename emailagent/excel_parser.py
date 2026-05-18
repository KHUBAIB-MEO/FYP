"""
Excel Parser - Reads Excel files and extracts email addresses
Auto-detects email columns and supports preview
"""
import pandas as pd
import re

class ExcelParser:
    """
    Parses Excel files to extract email addresses.
    Auto-detects the email column by header name or content pattern.
    """

    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None
        self.email_column = None
        self.name_column = None
        self.preview_data = []

    def read(self):
        """
        Read the Excel file and detect columns

        Returns:
            bool: True if successful
        """
        try:
            # Try reading with pandas
            self.df = pd.read_excel(self.file_path, engine='openpyxl')
            self._detect_columns()
            self.preview_data = self.df.head(20).to_dict('records')
            return True
        except Exception as e:
            print(f"Error reading Excel: {e}")
            return False

    def _detect_columns(self):
        """Auto-detect email and name columns"""
        if self.df is None:
            return

        # Possible email column names
        email_patterns = ['email', 'e-mail', 'mail', 'email address', 'e_mail', 
                         'Email', 'E-mail', 'Mail', 'EMAIL', 'E-MAIL']

        # Check headers first
        for col in self.df.columns:
            col_str = str(col).strip()
            if col_str in email_patterns:
                self.email_column = col_str
                break

        # If not found by header, check content for @ symbols
        if not self.email_column:
            for col in self.df.columns:
                sample = self.df[col].dropna().astype(str).head(10)
                if any(sample.str.contains('@', na=False)):
                    self.email_column = col
                    break

        # Detect name column for personalization
        name_patterns = ['name', 'first name', 'full name', 'customer name', 
                        'Name', 'NAME', 'First Name', 'Full Name']
        for col in self.df.columns:
            col_str = str(col).strip()
            if col_str in name_patterns and col_str != self.email_column:
                self.name_column = col_str
                break

    def get_emails(self):
        """
        Extract valid email addresses from the detected column

        Returns:
            list: List of dicts with 'email' and 'name' keys
        """
        if self.email_column is None or self.df is None:
            return []

        results = []
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

        for idx, row in self.df.iterrows():
            email = str(row.get(self.email_column, '')).strip()

            # Basic validation
            if email and '@' in email and '.' in email.split('@')[1]:
                # Additional regex check
                if email_pattern.match(email):
                    name = ""
                    if self.name_column:
                        name = str(row.get(self.name_column, '')).strip()

                    results.append({
                        "email": email,
                        "name": name,
                        "row_data": row.to_dict()
                    })

        return results

    def get_preview(self):
        """Get first 20 rows for preview"""
        return self.preview_data

    def get_column_names(self):
        """Get all column names from the file"""
        if self.df is not None:
            return list(self.df.columns)
        return []

    def get_stats(self):
        """Get file statistics"""
        if self.df is not None:
            emails = self.get_emails()
            return {
                "total_rows": len(self.df),
                "valid_emails": len(emails),
                "columns": len(self.df.columns),
                "email_column": self.email_column,
                "name_column": self.name_column
            }
        return {}
