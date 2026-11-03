import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .database import get_conn
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), conn=Depends(get_conn)) -> dict:
    """Devuelve el usuario autenticado a partir del JWT, o responde 401."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o sesión expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise credentials_error

    user = conn.execute(
        """SELECT id, email, full_name, role, token_limit, tokens_used,
                  is_active, created_at
           FROM users WHERE id = %s""",
        (user_id,),
    ).fetchone()

    if user is None or not user["is_active"]:
        raise credentials_error
    return user


def require_role(*roles: str):
    """Uso: Depends(require_role("admin")) protege un endpoint por rol (403 si no coincide)."""

    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para esta acción",
            )
        return user

    return checker