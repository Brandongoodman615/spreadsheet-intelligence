import duckdb
import pandas as pd
from app.services.schema_profiler import normalize_table_name

# In-memory registry: workbook_id → DuckDB connection
# Future: for large files, move to file-backed DuckDB connections or async processing
_registry: dict[int, duckdb.DuckDBPyConnection] = {}


def register_workbook(workbook_id: int, frames: dict[str, pd.DataFrame]) -> None:
    """Register all sheets as DuckDB tables for a given workbook."""
    conn = duckdb.connect()
    for sheet_name, df in frames.items():
        table_name = normalize_table_name(sheet_name)
        conn.register(table_name, df)
    _registry[workbook_id] = conn


def get_connection(workbook_id: int) -> duckdb.DuckDBPyConnection:
    if workbook_id not in _registry:
        raise KeyError(f"Workbook {workbook_id} not registered in DuckDB.")
    return _registry[workbook_id]


def is_registered(workbook_id: int) -> bool:
    return workbook_id in _registry


def unregister_workbook(workbook_id: int) -> None:
    """Free DuckDB connection when workbook is deleted."""
    if workbook_id in _registry:
        _registry[workbook_id].close()
        del _registry[workbook_id]
