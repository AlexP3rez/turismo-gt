from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..database import get_conn
from ..deps import get_current_user, require_role
from ..schemas import RegisterIn, Token, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, conn=Depends(get_conn)):
    """Registro público: siempre crea un usuario con rol 'user'."""
    row = conn.execute(
        """INSERT INTO users (email, full_name, password_hash)
           VALUES (%s, %s, %s)
           ON CONFLICT (email) DO NOTHING
           RETURNING id, email, full_name, role, token_limit, tokens_used,
                     is_active, created_at""",
        (data.email.lower(), data.full_name.strip(), hash_password(data.password)),
    ).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un usuario con ese correo")
    conn.commit()
    return row


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), conn=Depends(get_conn)):
    """Inicio de sesión. El campo 'username' es el correo electrónico."""
    user = conn.execute(
        """SELECT id, email, full_name, role, token_limit, tokens_used,
                  is_active, created_at, password_hash
           FROM users WHERE email = %s""",
        (form.username.lower(),),
    ).fetchone()

    if user is None or not verify_password(form.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos")
    if not user["is_active"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tu usuario está desactivado")

    return {
        "access_token": create_access_token(user["id"], user["role"]),
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)):
    """Datos del usuario autenticado."""
    return user


@router.post("/logout")
def logout(user: dict = Depends(get_current_user)):
    """Cierre de sesión. El JWT no se guarda en el servidor: el cliente debe descartarlo."""
    return {"message": "Sesión cerrada", "user": user["email"]}


@router.get("/admin-check")
def admin_check(user: dict = Depends(require_role("admin"))):
    """Endpoint de prueba: solo administradores (demuestra la restricción por rol)."""
    return {"message": f"Acceso de administrador concedido a {user['full_name']}"}