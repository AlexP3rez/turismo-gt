"""Crea las tablas y carga los datos de ejemplo.

Uso (desde la carpeta backend):
    python -m scripts.init_db              # schema + seed
    python -m scripts.init_db --no-seed    # solo schema
"""
import sys
from pathlib import Path

import psycopg

from app.config import settings

DB_DIR = Path(__file__).resolve().parent.parent / "db"


def run(filename: str) -> None:
    sql = (DB_DIR / filename).read_text(encoding="utf-8")
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        conn.execute(sql)
    print(f"OK: {filename}")


if __name__ == "__main__":
    run("schema.sql")
    if "--no-seed" not in sys.argv:
        run("seed.sql")