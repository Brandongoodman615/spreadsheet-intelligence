import duckdb
from app.schemas.query import QueryPlan, QueryResult, Attribution


def execute_plan(plan: QueryPlan, conn: duckdb.DuckDBPyConnection, question: str = "") -> QueryResult:
    """
    Execute the SQL from a QueryPlan against the DuckDB connection.
    Returns exact results — all arithmetic happens here, never in the LLM.
    """
    try:
        result_df = conn.execute(plan.sql).fetchdf()
    except Exception as e:
        raise ValueError(f"SQL execution failed: {e}\nSQL: {plan.sql}")

    if result_df.empty:
        answer = None
        rows_matched = 0
        preview = []
    else:
        rows_matched = len(result_df)
        preview = result_df.head(5).to_dict(orient="records")
        preview = [{k: _safe_value(v) for k, v in row.items()} for row in preview]

        # Single-value result (aggregation): unwrap it
        if result_df.shape == (1, 1):
            answer = _safe_value(result_df.iloc[0, 0])
        else:
            answer = preview

    attribution = Attribution(
        sheets=plan.relevant_sheets,
        columns=_extract_columns(plan.sql),
        rows_matched=rows_matched,
    )

    return QueryResult(
        question=question,
        answer=answer,
        sql=plan.sql,
        explanation=plan.explanation,
        attribution=attribution,
        preview_rows=preview,
    )


def _extract_columns(sql: str) -> list[str]:
    """
    Best-effort column extraction from SQL for attribution display.
    Captures both quoted identifiers ("My Column") and unquoted column references.
    # Future: use a proper SQL parser (sqlglot) for accurate column lineage.
    """
    import re

    columns = []

    # Quoted identifiers: "Column Name"
    columns += re.findall(r'"([^"]+)"', sql)

    # Unquoted columns after SELECT, WHERE, GROUP BY, ORDER BY, ON
    # Strip keywords, aliases, functions, table prefixes, and SQL keywords
    keywords = {
        "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "GROUP", "BY", "ORDER",
        "HAVING", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "ON", "AS",
        "COUNT", "SUM", "AVG", "MIN", "MAX", "DISTINCT", "LIMIT", "OFFSET",
        "ASC", "DESC", "NULL", "IS", "IN", "BETWEEN", "LIKE", "CASE", "WHEN",
        "THEN", "ELSE", "END", "CAST", "COALESCE",
    }
    tokens = re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', sql)
    for token in tokens:
        if token.upper() not in keywords and token not in columns:
            columns.append(token)

    return list(dict.fromkeys(columns))


def _safe_value(v):
    import numpy as np
    import math
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        f = float(v)
        return None if math.isnan(f) else f
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, float) and math.isnan(v):
        return None
    return v
