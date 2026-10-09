from pydantic import BaseModel


class SourceStatusOut(BaseModel):
    """Состояние подключения к одному источнику."""

    id: int
    name: str
    status: str


class HealthOut(BaseModel):
    """Ответ health-check."""

    meta_db: str
    sources: list[SourceStatusOut]
