import re
import pandas as pd
from app.schemas.workbook import WorkbookSchema, SheetSchema, ColumnSchema


def profile_workbook(frames: dict[str, pd.DataFrame], original_name: str) -> WorkbookSchema:
    """
    Build a WorkbookSchema from loaded DataFrames.
    This is what gets stored in Postgres and passed to the LLM query planner.
    """
    sheets = [_profile_sheet(name, df) for name, df in frames.items()]
    has_formulas = any(s.has_formulas for s in sheets)

    return WorkbookSchema(
        original_name=original_name,
        sheet_count=len(sheets),
        sheets=sheets,
        has_formulas=has_formulas,
    )


def _profile_sheet(name: str, df: pd.DataFrame) -> SheetSchema:
    columns = [_profile_column(col, df[col]) for col in df.columns]

    return SheetSchema(
        name=name,
        table_name=normalize_table_name(name),
        row_count=len(df),
        column_count=len(df.columns),
        columns=columns,
    )


def _profile_column(name: str, series: pd.Series) -> ColumnSchema:
    non_null = series.dropna()
    # For low-cardinality label columns (e.g. Metric, Stage, Region), show all
    # unique values so the LLM can see the full domain. Fixes cases like the KPIs
    # sheet where "Win Rate" is row 7 and would be cut off by a head(3) sample.
    if series.dtype == object and len(non_null.unique()) <= 20:
        sorted_vals = sorted(non_null.unique(), key=lambda x: str(x))[:15]
        sample = [_safe_value(v) for v in sorted_vals]
    else:
        sample = [_safe_value(v) for v in non_null.head(3).tolist()]
    hints = _detect_hints(series)

    return ColumnSchema(
        name=name,
        dtype=str(series.dtype),
        sample_values=sample,
        null_count=int(series.isna().sum()),
        hints=hints,
    )


def _detect_hints(series: pd.Series) -> list[str]:
    """
    Detect data quality hints for a column that help the LLM write correct SQL.

    Hints tell the LLM how to handle columns that look like one thing but are
    stored as another — e.g. percentages stored as "75%" strings, dates stored
    as text, or numbers with embedded currency symbols.
    """
    hints = []
    if series.dtype != object:
        return hints

    non_null = series.dropna()
    if non_null.empty:
        return hints

    str_vals = non_null.astype(str)

    # Percentage strings: "75%", "2.1%", "0%"
    pct_matches = str_vals.str.match(r'^-?\d+(\.\d+)?%$')
    if pct_matches.sum() / len(str_vals) >= 0.5:
        hints.append("percent_strings")
        return hints  # if it's percents it's not also currency

    # Currency strings: "$1,234", "€88,500", "£1,680,000", "¥525,000,000"
    currency_matches = str_vals.str.match(r'^[€£¥₹₩\$]-?[\d,]+(\.\d+)?$')
    if currency_matches.sum() / len(str_vals) >= 0.3:
        hints.append("currency_strings")

    # Mixed currency: multiple different currency symbols in one column
    symbols_found = set()
    for sym in ['$', '€', '£', '¥', '₹', '₩']:
        if str_vals.str.contains(re.escape(sym), regex=False).any():
            symbols_found.add(sym)
    if len(symbols_found) > 1:
        hints.append("mixed_currency")

    # Date strings: ISO, US slash, day-Mon-Year formats
    date_patterns = [
        r'^\d{4}-\d{2}-\d{2}$',           # 2024-01-15
        r'^\d{2}/\d{2}/\d{4}$',            # 01/15/2024
        r'^\d{1,2}-[A-Za-z]{3}-\d{4}$',   # 15-Jan-2024
        r'^[A-Za-z]{3}\s\d{4}$',           # Jan 2024
    ]
    date_hits = sum(
        str_vals.str.match(pat).sum()
        for pat in date_patterns
    )
    if date_hits / len(str_vals) >= 0.4:
        hints.append("date_strings")

    # Numeric-as-text: looks numeric but stored as object (after cleaning)
    cleaned = str_vals.str.replace(r'^[€£¥₹₩\$]', '', regex=True) \
                          .str.replace(',', '', regex=False) \
                          .str.replace(r'\*+$', '', regex=True)
    numeric_hits = pd.to_numeric(cleaned, errors='coerce').notna().sum()
    if numeric_hits / len(str_vals) >= 0.7 and "currency_strings" not in hints:
        hints.append("numeric_as_text")

    return hints


def normalize_table_name(name: str) -> str:
    """
    Convert sheet name to a valid SQL table name.
    "Sales Data Q1" → "sales_data_q1"
    """
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    if name and name[0].isdigit():
        name = f"t_{name}"
    return name or "sheet"


def _safe_value(v):
    """Convert numpy/pandas types to plain Python for JSON serialization."""
    import numpy as np
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v
