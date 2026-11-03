from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status

from ..database import get_conn
from ..deps import require_role
from ..schemas import UserCreate, UserOut, UserUpdate
from ..security import hash_password
from ..sql_utils import update_row

router = APIRouter(prefix="/admin/users", tags=["Admin · Usuarios"])

USER_COLS = "id, email, full_name, role, token_limit, tokens_used, is_active, created_at"


@router.get("", response_model=list[UserOut])
def list_users(
    search: str | None = None,
    role: Literal["admin", "user"] | None = None,
    admin: dict = Depends(require_role("admin")),
    conn=Depends(get_conn),
):
    """Lista usuarios. Filtros opcionales: búsqueda por nombre/correo y rol."""
    sql = f"SELECT {USER_COLS} FROM users WHERE TRUE"
    params: list = []
    if search:
        sql += " AND (email ILIKE %s OR full_name ILIKE %s)"
        params += [f"%{search}%"] * 2
    if role:
        sql += " AND role = %s"
        params.append(role)
    return conn.execute(sql + " ORDER BY id", params).fetchall()


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, admin: dict = Depends(require_role("admin")), conn=Depends(get_conn)):
    row = conn.execute(f"SELECT {USER_COLS} FROM users WHERE id = %s", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Usuario no encontrado")
    return row


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, admin: dict = Depends(require_role("admin")), conn=Depends(get_conn)):
    """Crea un usuario con rol y límite de tokens definidos por el admin."""
    row = conn.execute(
        f"""INSERT INTO users (email, full_name, password_hash, role, token_limit)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
            RETURNING {USER_COLS}""",
        (
            data.email.lower(),
            data.full_name.strip(),
            hash_password(data.password),
            data.role,
            data.token_limit,
        ),
    ).fetchone()
    if row is None:
        raise HTTPException(409, "Ya existe un usuario con ese correo")
    conn.commit()
    return row


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    admin: dict = Depends(require_role("admin")),
    conn=Depends(get_conn),
):
    """Actualiza solo los campos enviados (nombre, correo, contraseña, rol,
    límite de tokens, activo/inactivo)."""
    values = data.model_dump(exclude_unset=True, exclude_none=True)
    if not values:
        raise HTTPException(400, "No se envió ningún campo para actualizar")

    if user_id == admin["id"] and (values.get("role") == "user" or values.get("is_active") is False):
        raise HTTPException(400, "No puedes quitarte el rol de administrador ni desactivarte")

    if "password" in values:
        values["password_hash"] = hash_password(values.pop("password"))
    if "email" in values:
        values["email"] = values["email"].lower()

    try:
        row = update_row(conn, "users", user_id, values, USER_COLS)
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(409, "Ya existe un usuario con ese correo")
    if row is None:
        raise HTTPException(404, "Usuario no encontrado")
    conn.commit()
    return row


@router.post("/{user_id}/reset-tokens", response_model=UserOut)
def reset_tokens(user_id: int, admin: dict = Depends(require_role("admin")), conn=Depends(get_conn)):
    """Pone en cero el consumo acumulado del usuario (no borra su historial)."""
    row = conn.execute(
        f"UPDATE users SET tokens_used = 0 WHERE id = %s RETURNING {USER_COLS}", (user_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Usuario no encontrado")
    conn.commit()
    return row


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, admin: dict = Depends(require_role("admin")), conn=Depends(get_conn)):
    """Elimina al usuario y, en cascada, sus conversaciones y consumo.
    Para conservar el historial, mejor desactívalo con PATCH (is_active=false)."""
    if user_id == admin["id"]:
        raise HTTPException(400, "No puedes eliminar tu propio usuario")
    row = conn.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Usuario no encontrado")
    conn.commit()