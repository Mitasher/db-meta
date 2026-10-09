from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.data_source import DataSource
    from app.db.models.meta_column import MetaColumn


class MetaTable(TimestampMixin, Base):
    """Таблица источника и её настройки отображения."""

    __tablename__ = "meta_table"
    __table_args__ = (
        UniqueConstraint("data_source_id", "schema_name", "table_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    data_source_id: Mapped[int] = mapped_column(ForeignKey("data_source.id", ondelete="CASCADE"))
    schema_name: Mapped[str] = mapped_column(String(255))
    table_name: Mapped[str] = mapped_column(String(255))
    label: Mapped[str | None] = mapped_column(String(255))
    is_visible: Mapped[bool] = mapped_column(server_default=text("true"))
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))

    data_source: Mapped["DataSource"] = relationship(back_populates="tables")
    meta_columns: Mapped[list["MetaColumn"]] = relationship(
        back_populates="meta_table", order_by="MetaColumn.position"
    )
