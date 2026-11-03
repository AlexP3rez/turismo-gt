from fastapi import APIRouter, Depends, HTTPException

from ..database import get_conn
from ..deps import get_current_user, require_role
from ..schemas import ServiceOut, ServiceUpdate
from ..sql_utils import update_row

router = APIRouter(tags=["Servicios de IA"])

SERVICE_COLS = "id, code, name, description, is_active"


@router.get("/services", response_model=list[ServiceOut])
def list_services(user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    """Menú de servicios: el admin ve todos; el usuario solo los activos."""
    sql = f"SELECT {SERVICE_COLS} FROM ai_services"
    if user["role"] != "admin":
        sql += " WHERE is_active"
    return conn.execute(sql + " ORDER BY id").fetchall()


@router.patch("/admin/services/{service_id}", response_model=ServiceOut)
def update_service(
    service_id: int,
    data: ServiceUpdate,
    admin: dict = Depends(require_role("admin")),
    conn=Depends(get_conn),
):
    """Configura un servicio: nombre, descripción y activo/inactivo."""
    values = data.model_dump(exclude_unset=True, exclude_none=True)
    if not values:
        raise HTTPException(400, "No se envió ningún campo para actualizar")
    row = update_row(conn, "ai_services", service_id, values, SERVICE_COLS)
    if row is None:
        raise HTTPException(404, "Servicio no encontrado")
    conn.commit()
    return row