from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.meta_table import MetaTable


class DataSource(TimestampMixin, Base):
    """Подключение к исходной БД."""

    __tablename__ = "data_source"
    __table_args__ = (
        CheckConstraint("db_type IN ('postgresql', 'mysql')", name="db_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    db_type: Mapped[str] = mapped_column(String(20))
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int]
    database: Mapped[str] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(String(255))
    password_encrypted: Mapped[str] = mapped_column(Text)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tables: Mapped[list["MetaTable"]] = relationship(back_populates="data_source")
