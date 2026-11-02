from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import settings

# Neon cierra conexiones inactivas, por eso se valida cada conexión antes de usarla
pool = ConnectionPool(
    settings.database_url,
    min_size=1,
    max_size=5,
    kwargs={"row_factory": dict_row},
    check=ConnectionPool.check_connection,
    open=False,
)


def get_conn():
    """Dependencia de FastAPI: entrega una conexión y confirma al terminar."""
    with pool.connection() as conn:
        yield conn