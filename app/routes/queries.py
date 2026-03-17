from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.workbook import Workbook
from app.models.query_log import QueryLog
from app.services.query_planner import plan_query
from app.services.query_executor import execute_plan
from app.services.attribution_builder import build_attribution
from app.services.duckdb_registry import get_connection, is_registered
from app.services.workbook_loader import load_workbook
from app.services.duckdb_registry import register_workbook
from pathlib import Path
from pydantic import BaseModel


router = APIRouter(prefix="/queries", tags=["queries"])


class QueryRequest(BaseModel):
    workbook_id: int
    question: str


@router.post("/")
def run_query(payload: QueryRequest, db: Session = Depends(get_db)):
    workbook = db.query(Workbook).filter(Workbook.id == payload.workbook_id).first()
    if not workbook:
        raise HTTPException(status_code=404, detail="Workbook not found.")

    # Ensure DuckDB is loaded (handles server restart gracefully)
    if not is_registered(payload.workbook_id):
        frames = load_workbook(Path(workbook.upload_path))
        register_workbook(workbook_id=payload.workbook_id, frames=frames)

    schema = workbook.schema_json
    conn = get_connection(payload.workbook_id)

    try:
        plan = plan_query(question=payload.question, schema=schema)
        result = execute_plan(plan=plan, conn=conn)
        attribution = build_attribution(plan=plan, result=result)

        log = QueryLog(
            workbook_id=payload.workbook_id,
            question=payload.question,
            generated_sql=plan.sql,
            answer_raw=str(result.answer),
            attribution_json=attribution.model_dump(),
        )
        db.add(log)
        db.commit()

        return JSONResponse(result.model_dump())

    except Exception as e:
        log = QueryLog(
            workbook_id=payload.workbook_id,
            question=payload.question,
            error=str(e),
        )
        db.add(log)
        db.commit()
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{workbook_id}/history")
def query_history(workbook_id: int, db: Session = Depends(get_db)):
    logs = (
        db.query(QueryLog)
        .filter(QueryLog.workbook_id == workbook_id)
        .order_by(QueryLog.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": l.id,
            "question": l.question,
            "answer_raw": l.answer_raw,
            "generated_sql": l.generated_sql,
            "error": l.error,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]
