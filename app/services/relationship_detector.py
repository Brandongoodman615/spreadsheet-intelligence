import json
import logging
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from pydantic import ValidationError

from app.config import settings
from app.schemas.workbook import WorkbookSchema, WorkbookRelationships, SheetRelationship

logger = logging.getLogger(__name__)

_client = OpenAI(api_key=settings.openai_api_key)
_prompt_template = (Path(__file__).parent.parent / "prompts" / "relationship_detector.txt").read_text()


def detect_relationships(schema: WorkbookSchema) -> WorkbookRelationships:
    """
    Use the LLM to detect cross-sheet relationships in a workbook.

    Called once at upload time. Results are stored on the workbook record and
    passed to the query planner to enable automatic JOIN suggestions.

    Always returns a valid WorkbookRelationships — never raises. Upload must
    not fail because relationship detection fails.
    """
    empty = WorkbookRelationships(detected_at=datetime.utcnow(), relationships=[])

    sheets_with_data = [s for s in schema.sheets if s.row_count > 0]
    if len(sheets_with_data) < 2:
        return empty

    schema_text = _build_schema_text(sheets_with_data)
    prompt = _prompt_template.replace("{schema}", schema_text)

    try:
        response = _client.chat.completions.create(
            model=settings.chat_model,
            max_tokens=1024,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        relationships = _parse_and_validate(data, schema)
        logger.info(
            "Detected %d relationships for workbook '%s'",
            len(relationships), schema.original_name,
        )
        return WorkbookRelationships(detected_at=datetime.utcnow(), relationships=relationships)

    except Exception as exc:
        logger.warning("Relationship detection failed for '%s': %s", schema.original_name, exc)
        return empty


def _parse_and_validate(
    data: dict, schema: WorkbookSchema
) -> list[SheetRelationship]:
    """
    Parse and validate the LLM response.

    Drops any relationship that references a table or column not present in
    the schema — the most important guard against hallucinations.
    """
    # Build lookup of valid table→column sets
    valid: dict[str, set[str]] = {
        sheet.table_name: {col.name for col in sheet.columns}
        for sheet in schema.sheets
    }

    relationships = []
    for item in data.get("relationships", []):
        try:
            rel = SheetRelationship(**item)
        except (ValidationError, TypeError) as e:
            logger.debug("Skipping invalid relationship item: %s — %s", item, e)
            continue

        # Validate all four references exist in the actual schema
        if rel.from_table not in valid:
            logger.debug("Dropping relationship: unknown table '%s'", rel.from_table)
            continue
        if rel.from_column not in valid[rel.from_table]:
            logger.debug("Dropping relationship: unknown column '%s.%s'", rel.from_table, rel.from_column)
            continue
        if rel.to_table not in valid:
            logger.debug("Dropping relationship: unknown table '%s'", rel.to_table)
            continue
        if rel.to_column not in valid[rel.to_table]:
            logger.debug("Dropping relationship: unknown column '%s.%s'", rel.to_table, rel.to_column)
            continue

        relationships.append(rel)

    return relationships


def _build_schema_text(sheets) -> str:
    """Format schema for the relationship detection prompt."""
    lines = []
    for sheet in sheets:
        lines.append(f'Sheet: "{sheet.name}" → table: {sheet.table_name}')
        for col in sheet.columns:
            sample = ", ".join(str(v) for v in col.sample_values[:3])
            lines.append(f"  - {col.name} ({col.dtype}): {sample}")
        lines.append("")
    return "\n".join(lines)
