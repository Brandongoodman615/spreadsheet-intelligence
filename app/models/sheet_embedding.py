from datetime import datetime
from sqlalchemy import Integer, DateTime, Text, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.database import Base


class SheetEmbedding(Base):
    __tablename__ = "sheet_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workbook_id: Mapped[int] = mapped_column(Integer, ForeignKey("workbooks.id", ondelete="CASCADE"), index=True)
    sheet_name: Mapped[str] = mapped_column(String(255))
    table_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)          # human-readable text that was embedded
    embedding: Mapped[list] = mapped_column(Vector(1536))   # text-embedding-3-small dimensions
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
