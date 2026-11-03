from datetime import date

from fastapi import APIRouter, Depends, Query

from ..database import get_conn
from ..deps import get_current_user, require_role
from ..schemas_usage import MyUsageOut, UsageRecordOut
from ..usage_queries import build_filters, by_service, check_range, records

router = APIRouter()


@router.get("/usage/me", response_model=MyUsageOut, tags=["Consumo"])
def my_usage(
    service: str | None = None,
    date_from: date | None = Query(None, description="YYYY-MM-DD (hora de Guatemala)"),
    date_to: date | None = Query(None, description="YYYY-MM-DD (hora de Guatemala)"),
    user: dict = Depends(get_current_user),
    conn=Depends(get_conn),
):
    """Mi límite, mi saldo y mi consumo acumulado por servicio (filtrable por fecha)."""
    check_range(date_from, date_to)
    where, params = build_filters(user["id"], service, date_from, date_to)
    rows = by_service(conn, where, params)
    return {
        "token_limit": user["token_limit"],
        "tokens_used": user["tokens_used"],
        "tokens_remaining": max(user["token_limit"] - user["tokens_used"], 0),
        "total_queries": sum(r["queries"] for r in rows),
        "total_tokens": sum(r["total_tokens"] for r in rows),
        "by_service": rows,
    }


@router.get("/usage/me/records", response_model=list[UsageRecordOut], tags=["Consumo"])
def my_usage_records(
    service: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
    conn=Depends(get_conn),
):
    """Detalle de mis consultas (una fila por petición a la IA)."""
    check_range(date_from, date_to)
    where, params = build_filters(user["id"], service, date_from, date_to)
    return records(conn, where, params, limit, offset)


@router.get("/admin/usage", response_model=list[UsageRecordOut], tags=["Admin · Consumo"])
def admin_usage(
    user_id: int | None = None,
    service: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(require_role("admin")),
    conn=Depends(get_conn),
):
    """Uso general de todos los usuarios, con filtros por usuario, servicio y fecha."""
    check_range(date_from, date_to)
    where, params = build_filters(user_id, service, date_from, date_to)
    return records(conn, where, params, limit, offset)