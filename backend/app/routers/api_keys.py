from fastapi import APIRouter, Depends, HTTPException, status

from ..apikeys import generate_api_key, hash_api_key
from ..database import get_conn
from ..deps import require_role
from ..schemas_usage import ApiKeyCreate, ApiKeyCreated, ApiKeyOut

router = APIRouter(prefix="/admin/api-keys", tags=["Admin · API keys"])


@router.get("", response_model=list[ApiKeyOut])
def list_keys(admin: dict = Depends(require_role("admin")), conn=Depends(get_conn)):
    """Lista las llaves (nunca muestra su valor)."""
    return conn.execute(
        "SELECT id, name, is_active, created_at FROM api_keys ORDER BY id"
    ).fetchall()


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_key(data: ApiKeyCreate, admin: dict = Depends(require_role("admin")), conn=Depends(get_conn)):
    """Crea una llave de solo lectura para reportes. El valor de `api_key` se muestra
    UNA sola vez: cópialo ahora, porque en la BD solo queda su hash."""
    key = generate_api_key()
    row = conn.execute(
        """INSERT INTO api_keys (name, key_hash) VALUES (%s, %s)
           RETURNING id, name, is_active, created_at""",
        (data.name.strip(), hash_api_key(key)),
    ).fetchone()
    conn.commit()
    return {**row, "api_key": key}


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_key(key_id: int, admin: dict = Depends(require_role("admin")), conn=Depends(get_conn)):
    """Revoca (elimina) una llave: deja de funcionar de inmediato."""
    row = conn.execute("DELETE FROM api_keys WHERE id = %s RETURNING id", (key_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "API key no encontrada")
    conn.commit()