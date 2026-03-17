from openai import OpenAI
from sqlalchemy.orm import Session
from app.config import settings
from app.models.sheet_embedding import SheetEmbedding

_client = OpenAI(api_key=settings.openai_api_key)


def embed_workbook_schema(workbook_id: int, schema: dict, db: Session) -> None:
    """
    Generate and store embeddings for each sheet in a workbook.

    Each sheet gets one embedding based on its name, column names, and sample values.
    This lets us retrieve the most relevant sheets for a given question via
    vector similarity search, rather than dumping the entire schema into the prompt.

    # Future: embed at column level for very wide sheets (100+ columns).
    """
    # Remove any existing embeddings for this workbook (e.g. re-upload)
    db.query(SheetEmbedding).filter(SheetEmbedding.workbook_id == workbook_id).delete()

    for sheet in schema["sheets"]:
        description = _build_sheet_description(sheet)
        vector = _embed_text(description)

        record = SheetEmbedding(
            workbook_id=workbook_id,
            sheet_name=sheet["name"],
            table_name=sheet["table_name"],
            description=description,
            embedding=vector,
        )
        db.add(record)

    db.commit()


def find_relevant_sheets(workbook_id: int, question: str, db: Session, top_k: int = 3) -> list[dict]:
    """
    Find the most relevant sheets for a question using vector similarity search.

    Returns top_k sheets ordered by cosine similarity to the question embedding.
    Used to narrow the schema context passed to the LLM query planner.
    """
    question_vector = _embed_text(question)

    results = (
        db.query(SheetEmbedding)
        .filter(SheetEmbedding.workbook_id == workbook_id)
        .order_by(SheetEmbedding.embedding.cosine_distance(question_vector))
        .limit(top_k)
        .all()
    )

    return [
        {
            "sheet_name": r.sheet_name,
            "table_name": r.table_name,
            "description": r.description,
        }
        for r in results
    ]


def _build_sheet_description(sheet: dict) -> str:
    """
    Build a plain-text description of a sheet for embedding.

    Includes sheet name, column names, types, and sample values so the
    embedding captures both structural and semantic meaning.
    """
    lines = [f"Sheet: {sheet['name']}"]
    lines.append(f"Table name: {sheet['table_name']}")
    lines.append(f"Rows: {sheet['row_count']}")
    lines.append("Columns:")
    for col in sheet["columns"]:
        samples = ", ".join(str(v) for v in col["sample_values"])
        lines.append(f"  - {col['name']} ({col['dtype']}): e.g. {samples}")
    return "\n".join(lines)


def _embed_text(text: str) -> list[float]:
    """Call OpenAI embeddings API and return the vector."""
    response = _client.embeddings.create(
        model=settings.embedding_model,
        input=text,
    )
    return response.data[0].embedding
