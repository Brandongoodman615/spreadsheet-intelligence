from pydantic import BaseModel
from typing import Any


class QueryPlan(BaseModel):
    relevant_sheets: list[str]
    sql: str
    explanation: str


class Attribution(BaseModel):
    sheets: list[str]
    columns: list[str]
    rows_matched: int


class QueryResult(BaseModel):
    question: str
    answer: Any
    sql: str
    explanation: str
    attribution: Attribution
    preview_rows: list[dict] = []
