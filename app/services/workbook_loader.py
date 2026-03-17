from pathlib import Path
import pandas as pd
import openpyxl


def load_workbook(path: Path) -> dict[str, pd.DataFrame]:
    """
    Load all sheets from an .xlsx file into a dict of DataFrames.

    Uses data_only=True so formula cells return their last cached value.
    Does NOT recalculate formulas — see README known limitations.

    # Future: detect and handle multi-table sheets, named ranges,
    # merged headers, and non-rectangular data layouts.
    """
    frames: dict[str, pd.DataFrame] = {}

    raw = pd.read_excel(path, sheet_name=None, engine="openpyxl", header=None)

    for sheet_name, df in raw.items():
        cleaned = _extract_table(df, sheet_name)
        if cleaned is not None:
            frames[sheet_name] = cleaned

    return frames


def _extract_table(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame | None:
    """
    Find the best header row and return clean tabular data.

    Handles: leading title rows, empty rows, merged header cells, fully empty sheets.

    Strategy: use the row with the highest non-null cell count as the header.
    Title rows (e.g. "Acme Corporation", "Sales Report - H1 2024") typically
    have only one populated cell, while real header rows span all columns.
    """
    if df.empty:
        return None

    # Drop fully empty rows and columns
    df = df.dropna(how="all").dropna(axis=1, how="all")

    if df.empty:
        return None

    # Find the header row: first row with non-null count >= 50% of the max.
    # Title rows (e.g. "Acme Corporation") have 1 populated cell; header rows
    # have most cells populated. Using a threshold instead of strict max handles
    # cases where a header row has one blank cell (e.g. a formula column with no label).
    non_null_counts = df.notna().sum(axis=1)
    threshold = max(1, non_null_counts.max() * 0.5)
    header_idx = non_null_counts[non_null_counts >= threshold].index[0]

    df.columns = [
        str(df.loc[header_idx, c]).strip() if pd.notna(df.loc[header_idx, c]) else f"col_{i}"
        for i, c in enumerate(df.columns)
    ]
    df = df.loc[header_idx + 1:].reset_index(drop=True)

    # Drop rows that are entirely empty after header extraction
    df = df.dropna(how="all")

    if df.empty:
        return None

    # Coerce types: try numeric conversion on object columns.
    # Only apply if conversion introduces no new NaN values (mirrors old errors="ignore" behavior).
    for col in df.select_dtypes(include="object").columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.isna().sum() == df[col].isna().sum():
            df[col] = converted

    return df


def has_formula_cells(path: Path) -> bool:
    """Check if any cell in the workbook contains a formula."""
    wb = openpyxl.load_workbook(path, data_only=False)
    for sheet in wb.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    return True
    return False
