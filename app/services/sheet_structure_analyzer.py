import json
import logging
from pathlib import Path

import pandas as pd
from openai import OpenAI
from pydantic import BaseModel, field_validator

from app.config import settings
from app.services.workbook_scanner import SheetScan

logger = logging.getLogger(__name__)

_client = OpenAI(api_key=settings.openai_api_key)
_prompt_template = (Path(__file__).parent.parent / "prompts" / "sheet_structure.txt").read_text()


class SheetStructure(BaseModel):
    header_row: int
    data_start_row: int
    skip_rows: list[int] = []
    column_renames: dict[str, str] = {}
    notes: str = ""

    @field_validator("header_row", "data_start_row")
    @classmethod
    def must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("row index must be non-negative")
        return v


def analyze_sheet_structure(
    df: pd.DataFrame,
    sheet_name: str,
    sheet_scan: SheetScan | None = None,
) -> SheetStructure:
    """
    Use the LLM to identify the structural layout of a raw sheet.

    Detects title rows, the true header row, the first data row, and any
    embedded subtotal/grand-total/metadata rows that should be excluded.

    If sheet_scan is provided, rich openpyxl metadata (bold rows, merged
    regions, named ranges, print area) is injected into the prompt as explicit
    structural signals. Without it the LLM falls back to guessing from cell
    values alone.

    Falls back to a simple heuristic if the LLM call fails or returns
    an invalid response — so upload never breaks due to this step.
    """
    sample_size = min(35, len(df))
    sample = df.iloc[:sample_size]

    # Pre-detect which columns have blank/NA values in the first non-empty candidate
    # rows so we can explicitly annotate them in the prompt.  We don't know
    # header_row yet, so we pass None here and annotate after the first call.
    rows_text = _format_sample(sample)
    scan_block = _format_scan_metadata(sheet_scan)
    prompt = (
        _prompt_template
        .replace("{scan_metadata}", scan_block)
        .replace("{sheet_name}", sheet_name)
        .replace("{rows}", rows_text)
    )

    try:
        response = _client.chat.completions.create(
            model=settings.structure_model,
            max_tokens=256,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        structure = SheetStructure(**data)
        _validate_structure(structure, len(df))

        # Check whether any blank header positions were missed.  If the LLM
        # identified the header row but left column_renames empty (or incomplete)
        # for columns that are actually blank in that row, retry once with an
        # explicit annotation listing the missed positions.
        missed = _find_blank_header_cols(df, structure.header_row, structure.column_renames)
        if missed:
            logger.info(
                "Sheet '%s': retrying rename for blank cols %s",
                sheet_name, missed,
            )
            rows_text2 = _format_sample(sample, blank_col_indices=missed)
            prompt2 = (
                _prompt_template
                .replace("{scan_metadata}", scan_block)
                .replace("{sheet_name}", sheet_name)
                .replace("{rows}", rows_text2)
            )
            resp2 = _client.chat.completions.create(
                model=settings.structure_model,
                max_tokens=256,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt2}],
            )
            raw2 = resp2.choices[0].message.content.strip()
            data2 = json.loads(raw2)
            structure2 = SheetStructure(**data2)
            _validate_structure(structure2, len(df))
            structure = structure2

        logger.info(
            "Sheet '%s' structure: header=%d, data_start=%d, skip=%s, renames=%s — %s",
            sheet_name, structure.header_row, structure.data_start_row,
            structure.skip_rows, structure.column_renames, structure.notes,
        )
        return structure

    except Exception as exc:
        logger.warning(
            "Sheet structure analysis failed for '%s' (%s) — using heuristic fallback",
            sheet_name, exc,
        )
        return _heuristic_structure(df)


def _find_blank_header_cols(df: pd.DataFrame, header_row: int, existing_renames: dict) -> list[int]:
    """
    Return col indices that are blank in header_row and not already in existing_renames.

    A position is considered blank if its value is NA, empty string, or whitespace-only.
    These are the positions the LLM missed and need a retry annotation.
    """
    if header_row >= len(df):
        return []
    row = df.iloc[header_row]
    missing = []
    for i, val in enumerate(row):
        is_blank = pd.isna(val) or str(val).strip() == ""
        if is_blank and f"col_{i}" not in existing_renames:
            missing.append(i)
    return missing


def _validate_structure(structure: SheetStructure, row_count: int) -> None:
    """Raise if the LLM returned out-of-bounds or logically inconsistent indices."""
    if structure.header_row >= row_count:
        raise ValueError(f"header_row {structure.header_row} >= row_count {row_count}")
    if structure.data_start_row > row_count:
        raise ValueError(f"data_start_row {structure.data_start_row} > row_count {row_count}")
    if structure.data_start_row <= structure.header_row:
        raise ValueError(
            f"data_start_row {structure.data_start_row} must be > header_row {structure.header_row}"
        )
    for r in structure.skip_rows:
        if r < structure.data_start_row or r >= row_count:
            raise ValueError(f"skip_row {r} is out of the valid data range")


def _heuristic_structure(df: pd.DataFrame) -> SheetStructure:
    """
    Fallback: pick the first row whose non-null count is ≥50% of the maximum.
    This is the same logic the loader used before AI-assisted detection.
    """
    non_null_counts = df.notna().sum(axis=1)
    threshold = max(1, non_null_counts.max() * 0.5)
    candidates = non_null_counts[non_null_counts >= threshold]
    header_row = int(candidates.index[0]) if not candidates.empty else 0
    return SheetStructure(header_row=header_row, data_start_row=header_row + 1)


def _format_scan_metadata(sheet_scan: SheetScan | None) -> str:
    """
    Format openpyxl pre-scan metadata into a compact text block for the prompt.
    Returns an empty string if no scan data is available.
    """
    if sheet_scan is None:
        return ""

    lines = ["Formatting metadata (from openpyxl pre-scan):"]
    has_content = False

    if sheet_scan.bold_rows:
        lines.append(f"- Bold rows (0-indexed): {', '.join(str(r) for r in sheet_scan.bold_rows)}")
        has_content = True

    if sheet_scan.merged_regions:
        parts = []
        for r in sheet_scan.merged_regions:
            val = f' (value: "{r.top_left_value}")' if r.top_left_value else ""
            parts.append(f"{r.range_str}{val}")
        lines.append(f"- Merged cell regions: {', '.join(parts)}")
        has_content = True

    if sheet_scan.named_ranges:
        lines.append(f"- Named ranges covering this sheet: {', '.join(sheet_scan.named_ranges)}")
        has_content = True

    if sheet_scan.print_area:
        lines.append(f"- Print area: {sheet_scan.print_area}")
        has_content = True

    if not has_content:
        return ""

    return "\n".join(lines) + "\n"


def _format_sample(df: pd.DataFrame, blank_col_indices: list[int] | None = None) -> str:
    """
    Format raw DataFrame rows as numbered text for the LLM prompt.
    Empty cells are shown as <empty> so the LLM can see the sparsity pattern.
    A column-index header line is prepended so the LLM can map blank header
    positions to the correct col_N placeholder name.

    If blank_col_indices is provided, an explicit annotation line is appended
    after the data listing the col_N positions that must be renamed.
    """
    col_header = "Cols: " + " | ".join(f"col_{i}" for i in range(len(df.columns)))
    lines = [col_header]
    for idx in df.index:
        vals = [
            str(v).strip() if pd.notna(v) and str(v).strip() != "" else "<empty>"
            for v in df.loc[idx]
        ]
        lines.append(f"Row {idx}: {' | '.join(vals)}")
    if blank_col_indices:
        names = ", ".join(f"col_{i}" for i in blank_col_indices)
        lines.append(f"\n⚠ Blank header positions that MUST be renamed: {names}")
    return "\n".join(lines)
