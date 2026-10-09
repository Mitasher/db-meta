from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChangeLog(Base):
    """Запись журнала: правка строки или запрос из SQL-консоли."""

    __tablename__ = "change_log"
    __table_args__ = (
        CheckConstraint(
            "action IN ('update', 'insert', 'delete', 'sql_select', 'sql_preview', 'sql_write', 'sql_rejected')",
            name="action",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    data_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_source.id", ondelete="SET NULL"), index=True
    )
    meta_table_id: Mapped[int | None] = mapped_column(
        ForeignKey("meta_table.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(20))
    row_key: Mapped[dict | None] = mapped_column(JSONB)
    old_values: Mapped[dict | None] = mapped_column(JSONB)
    new_values: Mapped[dict | None] = mapped_column(JSONB)
    sql_text: Mapped[str | None] = mapped_column(Text)
    affected_rows: Mapped[int | None]
    message: Mapped[str | None] = mapped_column(Text)
    client_address: Mapped[str | None] = mapped_column(String(100))
