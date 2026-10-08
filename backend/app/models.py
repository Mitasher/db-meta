from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс моделей meta-db."""
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class TimestampMixin:
    """Даты создания и изменения записи."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


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

    data_source: Mapped[DataSource] = relationship(back_populates="tables")
    meta_columns: Mapped[list["MetaColumn"]] = relationship(
        back_populates="meta_table", order_by="MetaColumn.position"
    )


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

    meta_table: Mapped[MetaTable] = relationship(back_populates="meta_columns")


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

    meta_table: Mapped[MetaTable] = relationship()
