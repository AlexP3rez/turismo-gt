import hashlib
import secrets

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

from .database import get_conn
from .deps import get_current_user

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
optional_bearer = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def generate_api_key() -> str:
    return "tgt_" + secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def report_access(
    api_key: str | None = Security(api_key_header),
    token: str | None = Depends(optional_bearer),
    conn=Depends(get_conn),
) -> dict:
    """Acceso a los reportes: una API key activa (Power BI) o un JWT de administrador (web)."""
    if api_key:
        row = conn.execute(
            "SELECT id, name FROM api_keys WHERE key_hash = %s AND is_active",
            (hash_api_key(api_key.strip()),),
        ).fetchone()
        if row is None:
            raise HTTPException(401, "API key inválida o revocada")
        return {"via": "api_key", "name": row["name"]}

    if token:
        user = get_current_user(token, conn)  # 401 si el token no sirve
        if user["role"] != "admin":
            raise HTTPException(403, "No tienes permisos para esta acción")
        return {"via": "jwt", "name": user["email"]}

    raise HTTPException(401, "Se requiere una API key (X-API-Key) o un token de administrador")