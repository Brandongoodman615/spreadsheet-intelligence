import json
from pathlib import Path
from openai import OpenAI
from app.config import settings
from app.schemas.query import QueryPlan

_client = OpenAI(api_key=settings.openai_api_key)
_prompt_template = (Path(__file__).parent.parent / "prompts" / "query_planner.txt").read_text()


def plan_query(
    question: str,
    schema: dict,
    relationships: dict | None = None,
    sql_error: str | None = None,
) -> QueryPlan:
    """
    Send the workbook schema and user question to GPT-4o.
    Returns a structured QueryPlan with SQL ready for DuckDB execution.

    The LLM never computes answers — it only translates intent into SQL.

    If sql_error is provided, this is a retry attempt. The previous SQL and the
    error are appended to the prompt so the LLM can self-correct.
    """
    schema_summary = _build_schema_summary(schema, relationships)
    prompt = _prompt_template.replace("{schema}", schema_summary).replace("{question}", question)

    if sql_error:
        prompt += f"\n\nThe previous SQL attempt failed with this error:\n{sql_error}\n\nPlease fix the SQL and try again."

    response = _client.chat.completions.create(
        model=settings.chat_model,
        max_tokens=1024,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nRaw response: {raw}")

    if not data.get("sql"):
        raise ValueError(f"Could not generate a query: {data.get('explanation', 'No explanation provided.')}")

    return QueryPlan(
        relevant_sheets=data["relevant_sheets"],
        sql=data["sql"],
        explanation=data["explanation"],
    )


def _build_schema_summary(schema: dict, relationships: dict | None = None) -> str:
    """
    Format the workbook schema into a concise text representation for the prompt.
    Includes column hints so the LLM knows how to handle dirty data patterns.
    """
    lines = [f"Workbook: {schema['original_name']}", ""]
    for sheet in schema["sheets"]:
        lines.append(f"Sheet: \"{sheet['name']}\" → table: {sheet['table_name']}")
        row_count = sheet['row_count']
        lines.append(f"  Rows: {row_count}")
        for col in sheet["columns"]:
            sample_vals = col["sample_values"]
            sample_str = ", ".join(str(v) for v in sample_vals)
            hints = col.get("hints", [])
            hint_str = f" [hints: {', '.join(hints)}]" if hints else ""
            # Flag repeated-key columns so the LLM knows this is a line-item table
            # and avoids fan-out errors when joining with aggregation.
            unique_count = len(set(str(v) for v in sample_vals))
            if col["dtype"] == "object" and unique_count < len(sample_vals) and row_count > unique_count * 2:
                hint_str += " [repeated key — multiple rows per value]"
            lines.append(f"  - {col['name']} ({col['dtype']}) e.g.: {sample_str}{hint_str}")
        lines.append("")

    # Append cross-sheet relationships so the LLM can write JOIN queries
    if relationships:
        high_confidence = [
            r for r in relationships.get("relationships", [])
            if r.get("confidence", 0) >= 0.7
        ]
        if high_confidence:
            lines.append("Cross-sheet relationships (use for JOINs when the question spans multiple sheets):")
            for r in high_confidence:
                lines.append(
                    f"  - {r['join_hint']}"
                    f"  [{r['relationship_type']}, confidence: {r['confidence']:.2f}]"
                )
                if r.get("notes"):
                    lines.append(f"    Note: {r['notes']}")
            lines.append("")

    return "\n".join(lines)
