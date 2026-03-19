from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Workbook(Base):
    __tablename__ = "workbooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))          # stored filename on disk
    original_name: Mapped[str] = mapped_column(String(255))     # user's original filename
    upload_path: Mapped[str] = mapped_column(String(500))
    sheet_count: Mapped[int] = mapped_column(Integer, default=0)
    schema_json: Mapped[dict] = mapped_column(JSON, nullable=True)       # full WorkbookSchema
    relationships_json: Mapped[dict] = mapped_column(JSON, nullable=True) # WorkbookRelationships
    has_formulas: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
