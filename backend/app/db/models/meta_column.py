from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.meta_table import MetaTable


class MetaColumn(TimestampMixin, Base):
    """Колонка таблицы источника и её настройки отображения."""

    __tablename__ = "meta_column"
    __table_args__ = (
        UniqueConstraint("meta_table_id", "column_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    meta_table_id: Mapped[int] = mapped_column(ForeignKey("meta_table.id", ondelete="CASCADE"))
    column_name: Mapped[str] = mapped_column(String(255))
    data_type: Mapped[str] = mapped_column(String(255))
    label: Mapped[str | None] = mapped_column(String(255))
    position: Mapped[int]
    is_visible: Mapped[bool] = mapped_column(server_default=text("true"))
    is_primary_key: Mapped[bool] = mapped_column(server_default=text("false"))
    is_filterable: Mapped[bool] = mapped_column(server_default=text("true"))
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))

    meta_table: Mapped["MetaTable"] = relationship(back_populates="meta_columns")
