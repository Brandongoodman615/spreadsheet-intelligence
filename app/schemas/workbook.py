from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel


class SheetRelationship(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    relationship_type: Literal["foreign_key", "lookup", "reference"]
    match_type: Literal["exact_name", "semantic"]
    join_hint: str   # ready-to-use SQL ON clause, e.g. pipeline."Owner" = organization."Employee"
    confidence: float
    notes: str = ""


class WorkbookRelationships(BaseModel):
    detected_at: datetime
    relationships: list[SheetRelationship] = []


class ColumnSchema(BaseModel):
    name: str
    dtype: str
    sample_values: list[Any]
    null_count: int
    hints: list[str] = []  # e.g. ["percent_strings", "currency_strings", "date_strings"]


class SheetSchema(BaseModel):
    name: str
    table_name: str          # normalized: "Sales Data" → "sales_data"
    row_count: int
    column_count: int
    columns: list[ColumnSchema]
    has_formulas: bool = False


class WorkbookSchema(BaseModel):
    original_name: str
    sheet_count: int
    sheets: list[SheetSchema]
    has_formulas: bool = False
