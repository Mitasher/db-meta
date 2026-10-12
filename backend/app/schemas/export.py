from pydantic import BaseModel, Field, model_validator

from app.schemas.tables import DataQueryIn


class ExportIn(BaseModel):
    """Что выгружать: таблицу с тем же запросом, что у /data, или сохранённый шаблон."""

    table_id: int | None = None
    query: DataQueryIn = Field(default_factory=DataQueryIn)
    template_id: int | None = None

    @model_validator(mode="after")
    def one_target(self) -> "ExportIn":
        """Ровно одно из table_id и template_id."""
        if (self.table_id is None) == (self.template_id is None):
            raise ValueError("Нужно указать ровно одно: table_id или template_id")
        return self
