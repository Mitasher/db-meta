from sqlalchemy import types as sa_types
from sqlalchemy.types import TypeEngine


def detect_type_group(column_type: TypeEngine) -> str:
    """Группа типа колонки: по ней выбираются операторы фильтра и разбор значений."""
    if isinstance(column_type, sa_types.Boolean):
        return "boolean"
    if isinstance(column_type, sa_types.Integer):
        return "integer"
    if isinstance(column_type, sa_types.Numeric):
        return "number"
    if isinstance(column_type, sa_types.DateTime):
        return "datetime"
    if isinstance(column_type, sa_types.Date):
        return "date"
    if isinstance(column_type, sa_types.String):
        return "string"
    return "other"


def allowed_operators(type_group: str) -> list[str]:
    """Операторы фильтра, которые имеют смысл для группы типа."""
    if type_group in ("integer", "number", "date", "datetime"):
        return ["eq", "ne", "gt", "lt", "between", "in", "is_null", "is_not_null"]
    if type_group == "string":
        return ["eq", "ne", "like", "in", "is_null", "is_not_null"]
    if type_group == "boolean":
        return ["eq", "ne", "is_null", "is_not_null"]
    return ["is_null", "is_not_null"]
