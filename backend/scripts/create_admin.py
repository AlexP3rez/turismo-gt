"""Crea (o actualiza) un usuario administrador.

Uso (desde la carpeta backend):
    python -m scripts.create_admin admin@turismo.gt "Administrador"
La contraseña se pide por consola para no dejarla en el historial.
"""
import getpass
import sys

import psycopg

from app.config import settings
from app.security import hash_password


def main() -> None:
    if len(sys.argv) < 3:
        print('Uso: python -m scripts.create_admin correo@ejemplo.com "Nombre completo"')
        sys.exit(1)

    email = sys.argv[1].strip().lower()
    full_name = sys.argv[2].strip()

    password = getpass.getpass("Contraseña (mínimo 8 caracteres): ")
    if len(password) < 8:
        print("La contraseña debe tener al menos 8 caracteres.")
        sys.exit(1)
    if password != getpass.getpass("Repite la contraseña: "):
        print("Las contraseñas no coinciden.")
        sys.exit(1)

    with psycopg.connect(settings.database_url) as conn:
        conn.execute(
            """INSERT INTO users (email, full_name, password_hash, role, token_limit)
               VALUES (%s, %s, %s, 'admin', 1000000)
               ON CONFLICT (email) DO UPDATE
               SET role = 'admin',
                   full_name = EXCLUDED.full_name,
                   password_hash = EXCLUDED.password_hash""",
            (email, full_name, hash_password(password)),
        )
    print(f"Administrador listo: {email}")


if __name__ == "__main__":
    main()