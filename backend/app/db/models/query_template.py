from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.meta_table import MetaTable


class QueryTemplate(TimestampMixin, Base):
    """Сохранённый шаблон запроса: фильтры в JSON, не текст SQL."""

    __tablename__ = "query_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    meta_table_id: Mapped[int] = mapped_column(
        ForeignKey("meta_table.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    body: Mapped[dict] = mapped_column(JSONB)

    meta_table: Mapped["MetaTable"] = relationship()
