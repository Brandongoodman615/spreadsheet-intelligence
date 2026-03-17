import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models.workbook import Workbook
from app.services.workbook_loader import load_workbook
from app.services.schema_profiler import profile_workbook
from app.services.duckdb_registry import register_workbook
from app.services.embedding_service import embed_workbook_schema

router = APIRouter(prefix="/workbooks", tags=["workbooks"])


@router.post("/")
async def upload_workbook(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_size_mb}MB limit.")

    # Save file to disk with unique name
    unique_name = f"{uuid.uuid4()}.xlsx"
    dest = settings.upload_path / unique_name
    dest.write_bytes(contents)

    # Parse workbook and build schema
    frames = load_workbook(dest)
    schema = profile_workbook(frames, original_name=file.filename)

    # Register DataFrames in DuckDB (keyed by workbook id — assigned after DB insert)
    record = Workbook(
        filename=unique_name,
        original_name=file.filename,
        upload_path=str(dest),
        sheet_count=schema.sheet_count,
        schema_json=schema.model_dump(),
        has_formulas=schema.has_formulas,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    register_workbook(workbook_id=record.id, frames=frames)
    embed_workbook_schema(workbook_id=record.id, schema=schema.model_dump(), db=db)

    return JSONResponse({"id": record.id, "schema": schema.model_dump()})


@router.get("/")
def list_workbooks(db: Session = Depends(get_db)):
    workbooks = db.query(Workbook).order_by(Workbook.created_at.desc()).all()
    return [
        {
            "id": w.id,
            "original_name": w.original_name,
            "sheet_count": w.sheet_count,
            "has_formulas": w.has_formulas,
            "created_at": w.created_at.isoformat(),
        }
        for w in workbooks
    ]


@router.get("/{workbook_id}")
def get_workbook(workbook_id: int, db: Session = Depends(get_db)):
    workbook = db.query(Workbook).filter(Workbook.id == workbook_id).first()
    if not workbook:
        raise HTTPException(status_code=404, detail="Workbook not found.")

    # Re-register in DuckDB if not already loaded (e.g. after server restart)
    from app.services.duckdb_registry import is_registered
    if not is_registered(workbook_id):
        frames = load_workbook(Path(workbook.upload_path))
        register_workbook(workbook_id=workbook_id, frames=frames)

    return {"id": workbook.id, "schema": workbook.schema_json, "original_name": workbook.original_name}
