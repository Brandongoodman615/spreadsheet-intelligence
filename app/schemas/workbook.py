from pydantic import BaseModel
from typing import Any


class ColumnSchema(BaseModel):
    name: str
    dtype: str
    sample_values: list[Any]
    null_count: int


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
