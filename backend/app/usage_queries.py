"""Consultas sobre usage_log. Las usan el usuario, el administrador y los reportes,
para que todas las vistas calculen los números de la misma forma."""
from datetime import date

from fastapi import HTTPException

TZ = "America/Guatemala"
# Día local (Guatemala) de cada consulta; created_at está guardado en UTC
LOCAL_DAY = f"(u.created_at AT TIME ZONE '{TZ}')::date"

FROM_USAGE = """FROM usage_log u
                JOIN ai_services s ON s.id = u.service_id
                JOIN users us ON us.id = u.user_id"""


def check_range(date_from: date | None, date_to: date | None) -> None:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(400, "date_from no puede ser posterior a date_to")


def build_filters(user_id=None, service=None, date_from=None, date_to=None) -> tuple[str, list]:
    """Devuelve (cláusula WHERE, parámetros). Todos los filtros son opcionales."""
    where, params = ["TRUE"], []
    if user_id is not None:
        where.append("u.user_id = %s")
        params.append(user_id)
    if service:
        where.append("s.code = %s")
        params.append(service)
    if date_from:
        where.append(f"{LOCAL_DAY} >= %s")
        params.append(date_from)
    if date_to:
        where.append(f"{LOCAL_DAY} <= %s")
        params.append(date_to)
    return " AND ".join(where), params


def records(conn, where: str, params: list, limit: int, offset: int) -> list[dict]:
    """Una fila por consulta, de la más reciente a la más antigua."""
    return conn.execute(
        f"""SELECT u.id, u.user_id, us.email AS user_email,
                   s.code AS service_code, s.name AS service_name,
                   u.conversation_id, u.prompt_tokens, u.completion_tokens,
                   u.total_tokens, u.created_at
            {FROM_USAGE}
            WHERE {where}
            ORDER BY u.id DESC
            LIMIT %s OFFSET %s""",
        (*params, limit, offset),
    ).fetchall()


def by_service(conn, where: str, params: list) -> list[dict]:
    """Consultas y tokens acumulados por servicio."""
    return conn.execute(
        f"""SELECT s.code AS service_code, s.name AS service_name,
                   count(*) AS queries,
                   sum(u.prompt_tokens) AS prompt_tokens,
                   sum(u.completion_tokens) AS completion_tokens,
                   sum(u.total_tokens) AS total_tokens
            {FROM_USAGE}
            WHERE {where}
            GROUP BY s.code, s.name
            ORDER BY s.code""",
        params,
    ).fetchall()


def daily(conn, where: str, params: list) -> list[dict]:
    """Filas planas por día, servicio y usuario (formato ideal para Power BI)."""
    return conn.execute(
        f"""SELECT {LOCAL_DAY} AS day,
                   s.code AS service_code, s.name AS service_name,
                   u.user_id, us.email AS user_email,
                   count(*) AS queries,
                   sum(u.prompt_tokens) AS prompt_tokens,
                   sum(u.completion_tokens) AS completion_tokens,
                   sum(u.total_tokens) AS total_tokens
            {FROM_USAGE}
            WHERE {where}
            GROUP BY {LOCAL_DAY}, s.code, s.name, u.user_id, us.email
            ORDER BY {LOCAL_DAY}, s.code, us.email""",
        params,
    ).fetchall()