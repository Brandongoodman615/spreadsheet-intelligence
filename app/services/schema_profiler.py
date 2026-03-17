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
    sample = series.dropna().head(3).tolist()
    # Serialize samples to JSON-safe types
    sample = [_safe_value(v) for v in sample]

    return ColumnSchema(
        name=name,
        dtype=str(series.dtype),
        sample_values=sample,
        null_count=int(series.isna().sum()),
    )


def normalize_table_name(name: str) -> str:
    """
    Convert sheet name to a valid SQL table name.
    "Sales Data Q1" → "sales_data_q1"
    """
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    # Prefix with t_ if starts with a digit
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
