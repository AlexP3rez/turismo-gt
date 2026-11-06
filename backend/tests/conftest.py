"""Configuración común de las pruebas.

Usan una BASE DE DATOS APARTE (TEST_DATABASE_URL) porque al iniciar borran y
recrean todas las tablas. El LLM y los embeddings se simulan.
"""
import os
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent


def _env_file() -> dict:
    values = {}
    path = BACKEND / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip("\"'")
    return values


_dotenv = _env_file()
TEST_DB_URL = (os.environ.get("TEST_DATABASE_URL") or _dotenv.get("TEST_DATABASE_URL") or "").strip()
DEV_DB_URL = (_dotenv.get("DATABASE_URL") or "").strip()

if not TEST_DB_URL:
    raise RuntimeError(
        "Falta TEST_DATABASE_URL: define una base de datos DESECHABLE para las pruebas "
        "(en backend/.env o como variable de entorno)."
    )
if TEST_DB_URL == DEV_DB_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL es igual a DATABASE_URL. Las pruebas borran todas las tablas: "
        "usa una rama o base de datos distinta."
    )

# Deben fijarse ANTES de importar la app (lee la configuración al importarse).
# Las llaves vacías impiden que una prueba llame por error a Groq o Gemini.
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["GROQ_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["JWT_SECRET"] = "secreto-solo-para-pruebas-0123456789abcdef"

import psycopg  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from app import knowledge, llm  # noqa: E402
from app.main import app  # noqa: E402
from app.security import create_access_token, hash_password  # noqa: E402
from tests.helpers import VEC_ATITLAN, make_response  # noqa: E402

PASSWORD_HASH = hash_password("Clave12345")  # se calcula una sola vez (bcrypt es lento)


@pytest.fixture(scope="session", autouse=True)
def setup_schema():
    """Crea las tablas y carga los datos de ejemplo en la BD de pruebas."""
    for name in ("schema.sql", "seed.sql"):
        sql = (BACKEND / "db" / name).read_text(encoding="utf-8")
        with psycopg.connect(TEST_DB_URL, autocommit=True) as conn:
            conn.execute(sql)


@pytest.fixture(scope="session")
def client(setup_schema):
    with TestClient(app) as c:  # el "with" ejecuta el lifespan (abre el pool)
        yield c


@pytest.fixture
def db():
    """Conexión directa para preparar y verificar datos."""
    with psycopg.connect(TEST_DB_URL, autocommit=True, row_factory=dict_row) as conn:
        yield conn


@pytest.fixture(autouse=True)
def clean_db(db):
    """Estado limpio antes de cada prueba (se conservan destinos y actividades)."""
    db.execute("TRUNCATE users, api_keys, document_chunks RESTART IDENTITY CASCADE")
    db.execute("UPDATE ai_services SET is_active = TRUE")


@pytest.fixture
def make_user(db):
    def _make(email="user@test.com", role="user", token_limit=20000):
        row = db.execute(
            """INSERT INTO users (email, full_name, password_hash, role, token_limit)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (email, "Usuario de prueba", PASSWORD_HASH, role, token_limit),
        ).fetchone()
        token = create_access_token(row["id"], role)
        return {"id": row["id"], "email": email, "headers": {"Authorization": f"Bearer {token}"}}

    return _make


class FakeLLM:
    """Reemplaza a llm.chat. Registra las llamadas y responde con una cola de
    respuestas programadas; si la cola está vacía, simula un RAG obediente."""

    def __init__(self):
        self.calls = []
        self.queue = []

    def __call__(self, messages, tools=None, temperature=0.2, max_tokens=1500, tool_choice="auto"):
        self.calls.append(
            {"messages": [dict(m) for m in messages], "tools": tools, "tool_choice": tool_choice}
        )
        if self.queue:
            return self.queue.pop(0)
        if "No se encontraron fragmentos" in messages[0]["content"]:
            return make_response("No tengo información suficiente en la base de datos sobre eso.")
        return make_response("Puedes hacer un paseo en lancha entre pueblos por Q100 [1].")


@pytest.fixture
def fake_llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(llm, "chat", fake)
    return fake


@pytest.fixture
def embed_as(monkeypatch):
    """embed_as(vector): fija el embedding que devolverá la pregunta del usuario."""

    def _set(vec):
        monkeypatch.setattr(knowledge, "embed_query", lambda text: vec)

    return _set


@pytest.fixture
def chunks(db):
    """Un fragmento indexado del destino 2 (Lago de Atitlán)."""
    db.execute(
        """INSERT INTO document_chunks (destination_id, source_title, content, embedding)
           VALUES (2, 'Lago de Atitlán',
                   'Lago de Atitlán (Sololá, naturaleza). Paseo en lancha entre pueblos: costo Q100.',
                   %s::vector)""",
        (knowledge.to_pgvector(VEC_ATITLAN),),
    )