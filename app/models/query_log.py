from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class QueryLog(Base):
    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workbook_id: Mapped[int] = mapped_column(Integer, ForeignKey("workbooks.id"))
    question: Mapped[str] = mapped_column(Text)
    generated_sql: Mapped[str] = mapped_column(Text, nullable=True)
    answer_raw: Mapped[str] = mapped_column(Text, nullable=True)
    attribution_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
