"""Genera los fragmentos y embeddings (RAG) de todos los destinos.

Uso (desde la carpeta backend):
    python -m scripts.reindex
"""
import psycopg
from psycopg.rows import dict_row

from app.config import settings
from app.knowledge import reindex_destination


def main() -> None:
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM destinations ORDER BY id").fetchall()]
        total = 0
        for dest_id in ids:
            n = reindex_destination(conn, dest_id)
            total += n
            print(f"Destino {dest_id}: {n} fragmentos")
    print(f"Listo: {len(ids)} destinos, {total} fragmentos")


if __name__ == "__main__":
    main()