from datetime import date

from fastapi import APIRouter, Depends, Query

from ..apikeys import report_access
from ..database import get_conn
from ..schemas_usage import ReportRow, ServiceUsageOut
from ..usage_queries import build_filters, by_service, check_range, daily

router = APIRouter(prefix="/reports", tags=["Reportes"])

DATE_FROM = Query(None, description="YYYY-MM-DD (hora de Guatemala)")
DATE_TO = Query(None, description="YYYY-MM-DD (hora de Guatemala)")


@router.get("/summary", response_model=list[ServiceUsageOut])
def report_summary(
    user_id: int | None = None,
    service: str | None = None,
    date_from: date | None = DATE_FROM,
    date_to: date | None = DATE_TO,
    access: dict = Depends(report_access),
    conn=Depends(get_conn),
):
    """Consultas realizadas y consumo acumulado por servicio.
    Acceso: X-API-Key o JWT de administrador."""
    check_range(date_from, date_to)
    where, params = build_filters(user_id, service, date_from, date_to)
    return by_service(conn, where, params)


@router.get("/usage", response_model=list[ReportRow])
def report_usage(
    user_id: int | None = None,
    service: str | None = None,
    date_from: date | None = DATE_FROM,
    date_to: date | None = DATE_TO,
    access: dict = Depends(report_access),
    conn=Depends(get_conn),
):
    """Filas planas (día, servicio, usuario, consultas, tokens). Es el origen de datos
    de Power BI. Acceso: X-API-Key o JWT de administrador."""
    check_range(date_from, date_to)
    where, params = build_filters(user_id, service, date_from, date_to)
    return daily(conn, where, params)