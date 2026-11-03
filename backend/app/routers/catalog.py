import logging

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status

from ..database import get_conn
from ..deps import get_current_user, require_role
from ..knowledge import EmbeddingError, reindex_destination
from ..schemas import (
    ActivityBase,
    ActivityCreate,
    ActivityOut,
    ActivitySaved,
    DestinationDetail,
    DestinationIn,
    DestinationOut,
    DestinationSaved,
)
from ..sql_utils import update_row

log = logging.getLogger("catalog")
router = APIRouter()

DEST_COLS = "id, name, department, category, description, created_at"
ACT_COLS = (
    "id, destination_id, name, description, category, "
    "est_cost_gtq, duration_hours, latitude, longitude"
)


def try_reindex(conn, destination_id: int) -> bool:
    """Actualiza los fragmentos del RAG sin romper el CRUD si Gemini falla."""
    try:
        reindex_destination(conn, destination_id)
        return True
    except EmbeddingError as e:
        log.warning("No se pudo indexar el destino %s: %s", destination_id, e)
        return False


# ======================= DESTINOS =======================
@router.get("/destinations", response_model=list[DestinationOut], tags=["Destinos"])
def list_destinations(
    search: str | None = None,
    category: str | None = None,
    department: str | None = None,
    user: dict = Depends(get_current_user),
    conn=Depends(get_conn),
):
    """Lista destinos (cualquier usuario autenticado)."""
    sql = f"SELECT {DEST_COLS} FROM destinations WHERE TRUE"
    params: list = []
    if search:
        sql += " AND (name ILIKE %s OR description ILIKE %s)"
        params += [f"%{search}%"] * 2
    if category:
        sql += " AND category = %s"
        params.append(category)
    if department:
        sql += " AND department = %s"
        params.append(department)
    return conn.execute(sql + " ORDER BY name", params).fetchall()


@router.get("/destinations/{destination_id}", response_model=DestinationDetail, tags=["Destinos"])
def get_destination(destination_id: int, user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    dest = conn.execute(
        f"SELECT {DEST_COLS} FROM destinations WHERE id = %s", (destination_id,)
    ).fetchone()
    if dest is None:
        raise HTTPException(404, "Destino no encontrado")
    acts = conn.execute(
        f"SELECT {ACT_COLS} FROM activities WHERE destination_id = %s ORDER BY id", (destination_id,)
    ).fetchall()
    return {**dest, "activities": acts}


@router.post(
    "/destinations", response_model=DestinationSaved, status_code=status.HTTP_201_CREATED, tags=["Destinos"]
)
def create_destination(
    data: DestinationIn, admin: dict = Depends(require_role("admin")), conn=Depends(get_conn)
):
    row = conn.execute(
        f"""INSERT INTO destinations (name, department, category, description)
            VALUES (%(name)s, %(department)s, %(category)s, %(description)s)
            RETURNING {DEST_COLS}""",
        data.model_dump(),
    ).fetchone()
    conn.commit()
    return {**row, "indexed": try_reindex(conn, row["id"])}


@router.put("/destinations/{destination_id}", response_model=DestinationSaved, tags=["Destinos"])
def update_destination(
    destination_id: int,
    data: DestinationIn,
    admin: dict = Depends(require_role("admin")),
    conn=Depends(get_conn),
):
    """Reemplaza los datos del destino y regenera sus fragmentos del RAG."""
    row = update_row(conn, "destinations", destination_id, data.model_dump(), DEST_COLS)
    if row is None:
        raise HTTPException(404, "Destino no encontrado")
    conn.commit()
    return {**row, "indexed": try_reindex(conn, destination_id)}


@router.delete("/destinations/{destination_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Destinos"])
def delete_destination(
    destination_id: int, admin: dict = Depends(require_role("admin")), conn=Depends(get_conn)
):
    """Borra el destino y, en cascada, sus actividades y fragmentos del RAG."""
    row = conn.execute("DELETE FROM destinations WHERE id = %s RETURNING id", (destination_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Destino no encontrado")
    conn.commit()


# ======================= ACTIVIDADES =======================
@router.get("/activities", response_model=list[ActivityOut], tags=["Actividades"])
def list_activities(
    destination_id: int | None = None,
    category: str | None = None,
    user: dict = Depends(get_current_user),
    conn=Depends(get_conn),
):
    sql = f"SELECT {ACT_COLS} FROM activities WHERE TRUE"
    params: list = []
    if destination_id:
        sql += " AND destination_id = %s"
        params.append(destination_id)
    if category:
        sql += " AND category = %s"
        params.append(category)
    return conn.execute(sql + " ORDER BY destination_id, id", params).fetchall()


@router.post(
    "/activities", response_model=ActivitySaved, status_code=status.HTTP_201_CREATED, tags=["Actividades"]
)
def create_activity(
    data: ActivityCreate, admin: dict = Depends(require_role("admin")), conn=Depends(get_conn)
):
    try:
        row = conn.execute(
            f"""INSERT INTO activities
                  (destination_id, name, description, category,
                   est_cost_gtq, duration_hours, latitude, longitude)
                VALUES (%(destination_id)s, %(name)s, %(description)s, %(category)s,
                        %(est_cost_gtq)s, %(duration_hours)s, %(latitude)s, %(longitude)s)
                RETURNING {ACT_COLS}""",
            data.model_dump(),
        ).fetchone()
    except psycopg.errors.ForeignKeyViolation:
        conn.rollback()
        raise HTTPException(404, "El destino indicado no existe")
    conn.commit()
    return {**row, "indexed": try_reindex(conn, row["destination_id"])}


@router.put("/activities/{activity_id}", response_model=ActivitySaved, tags=["Actividades"])
def update_activity(
    activity_id: int,
    data: ActivityBase,
    admin: dict = Depends(require_role("admin")),
    conn=Depends(get_conn),
):
    row = update_row(conn, "activities", activity_id, data.model_dump(), ACT_COLS)
    if row is None:
        raise HTTPException(404, "Actividad no encontrada")
    conn.commit()
    return {**row, "indexed": try_reindex(conn, row["destination_id"])}


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Actividades"])
def delete_activity(
    activity_id: int, admin: dict = Depends(require_role("admin")), conn=Depends(get_conn)
):
    row = conn.execute(
        "DELETE FROM activities WHERE id = %s RETURNING destination_id", (activity_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Actividad no encontrada")
    conn.commit()
    try_reindex(conn, row["destination_id"])


# ======================= BASE DE CONOCIMIENTO (RAG) =======================
@router.get("/admin/knowledge", tags=["Admin · Base de conocimiento"])
def knowledge_status(admin: dict = Depends(require_role("admin")), conn=Depends(get_conn)):
    """Cantidad de fragmentos indexados por destino (un destino con 0 no responde en el RAG)."""
    return conn.execute(
        """SELECT d.id, d.name, count(c.id) AS chunks
           FROM destinations d
           LEFT JOIN document_chunks c ON c.destination_id = d.id
           GROUP BY d.id, d.name ORDER BY d.id"""
    ).fetchall()


@router.post("/admin/knowledge/reindex", tags=["Admin · Base de conocimiento"])
def reindex_all(admin: dict = Depends(require_role("admin")), conn=Depends(get_conn)):
    """Regenera los fragmentos y embeddings de TODOS los destinos."""
    ids = [r["id"] for r in conn.execute("SELECT id FROM destinations ORDER BY id").fetchall()]
    total = 0
    try:
        for dest_id in ids:
            total += reindex_destination(conn, dest_id)
    except EmbeddingError as e:
        raise HTTPException(502, str(e))
    return {"destinations": len(ids), "chunks": total}


@router.post("/admin/knowledge/reindex/{destination_id}", tags=["Admin · Base de conocimiento"])
def reindex_one(
    destination_id: int, admin: dict = Depends(require_role("admin")), conn=Depends(get_conn)
):
    try:
        n = reindex_destination(conn, destination_id)
    except EmbeddingError as e:
        raise HTTPException(502, str(e))
    if n == 0:
        raise HTTPException(404, "Destino no encontrado")
    return {"destination_id": destination_id, "chunks": n}