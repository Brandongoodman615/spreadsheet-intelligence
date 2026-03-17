import json
from pathlib import Path
from openai import OpenAI
from app.config import settings
from app.schemas.query import QueryPlan

_client = OpenAI(api_key=settings.openai_api_key)
_prompt_template = (Path(__file__).parent.parent / "prompts" / "query_planner.txt").read_text()


def plan_query(question: str, schema: dict) -> QueryPlan:
    """
    Send the workbook schema and user question to GPT-4o.
    Returns a structured QueryPlan with SQL ready for DuckDB execution.

    The LLM never computes answers — it only translates intent into SQL.

    # Future: support multi-step plans for complex questions that require
    # intermediate results or joins across multiple sheets.
    """
    schema_summary = _build_schema_summary(schema)
    prompt = _prompt_template.format(schema=schema_summary, question=question)

    response = _client.chat.completions.create(
        model=settings.openai_model,
        max_tokens=1024,
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


def _build_schema_summary(schema: dict) -> str:
    """
    Format the workbook schema into a concise text representation for the prompt.
    Keeps the prompt focused — no raw data, just structure and samples.
    """
    lines = [f"Workbook: {schema['original_name']}", ""]
    for sheet in schema["sheets"]:
        lines.append(f"Sheet: \"{sheet['name']}\" → table: {sheet['table_name']}")
        lines.append(f"  Rows: {sheet['row_count']}")
        for col in sheet["columns"]:
            sample_str = ", ".join(str(v) for v in col["sample_values"])
            lines.append(f"  - {col['name']} ({col['dtype']}) e.g.: {sample_str}")
        lines.append("")
    return "\n".join(lines)
