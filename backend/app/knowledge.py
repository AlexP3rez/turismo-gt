import re

import httpx

from .config import settings

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768  # debe coincidir con vector(768) de schema.sql
_BASE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBED_MODEL}"
_BATCH = 50


class EmbeddingError(RuntimeError):
    """Falla al generar embeddings (llave faltante, límite de uso, red...)."""


def _call(endpoint: str, payload: dict) -> dict:
    if not settings.gemini_api_key:
        raise EmbeddingError("Falta GEMINI_API_KEY en el archivo .env")
    try:
        r = httpx.post(
            f"{_BASE_URL}:{endpoint}",
            json=payload,
            headers={"x-goog-api-key": settings.gemini_api_key},
            timeout=30,
        )
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise EmbeddingError(f"Error al llamar a Gemini: {e}") from e
    return r.json()


def _request(text: str, task_type: str) -> dict:
    return {
        "model": f"models/{EMBED_MODEL}",
        "content": {"parts": [{"text": text}]},
        "taskType": task_type,
        "outputDimensionality": EMBED_DIM,
    }


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embeddings para guardar (documentos)."""
    out: list[list[float]] = []
    for i in range(0, len(texts), _BATCH):
        batch = texts[i : i + _BATCH]
        data = _call(
            "batchEmbedContents",
            {"requests": [_request(t, "RETRIEVAL_DOCUMENT") for t in batch]},
        )
        out.extend(e["values"] for e in data["embeddings"])
    return out


def embed_query(text: str) -> list[float]:
    """Embedding de una pregunta del usuario (se usa en la Fase 4)."""
    return _call("embedContent", _request(text, "RETRIEVAL_QUERY"))["embedding"]["values"]


def to_pgvector(vec: list[float]) -> str:
    return "[" + ",".join(map(str, vec)) + "]"


def split_text(text: str, max_chars: int = 600) -> list[str]:
    """Divide un texto en fragmentos de hasta ~max_chars, cortando en fin de oración."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks, current = [], ""
    for s in sentences:
        if current and len(current) + len(s) + 1 > max_chars:
            chunks.append(current)
            current = s
        else:
            current = f"{current} {s}".strip()
    if current:
        chunks.append(current)
    return chunks


def build_chunks(dest: dict, activities: list[dict]) -> list[tuple[str, str]]:
    """Devuelve (título_fuente, contenido). Cada fragmento menciona el destino
    para que tenga sentido por sí solo al ser recuperado."""
    header = f"{dest['name']} ({dest['department']}, {dest['category']})"
    chunks = [(dest["name"], f"{header}. {part}") for part in split_text(dest["description"])]
    for a in activities:
        text = (
            f"Actividad en {dest['name']}: {a['name']}. Categoría: {a['category']}. "
            f"Costo aproximado: Q{float(a['est_cost_gtq']):.2f}. "
            f"Duración: {float(a['duration_hours']):g} horas."
        )
        if a["description"]:
            text += f" {a['description']}"
        chunks.append((f"{dest['name']} - {a['name']}", text))
    return chunks


def reindex_destination(conn, destination_id: int) -> int:
    """Reconstruye los fragmentos de un destino. Devuelve cuántos generó (0 si no existe).

    Los embeddings se piden ANTES de borrar los fragmentos anteriores: si Gemini
    falla, lo que ya estaba indexado se conserva.
    """
    dest = conn.execute(
        "SELECT id, name, department, category, description FROM destinations WHERE id = %s",
        (destination_id,),
    ).fetchone()
    if dest is None:
        return 0

    acts = conn.execute(
        """SELECT name, description, category, est_cost_gtq, duration_hours
           FROM activities WHERE destination_id = %s ORDER BY id""",
        (destination_id,),
    ).fetchall()

    chunks = build_chunks(dest, acts)
    vectors = embed_documents([content for _, content in chunks])

    conn.execute("DELETE FROM document_chunks WHERE destination_id = %s", (destination_id,))
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO document_chunks (destination_id, source_title, content, embedding)
               VALUES (%s, %s, %s, %s::vector)""",
            [
                (destination_id, title, content, to_pgvector(vec))
                for (title, content), vec in zip(chunks, vectors)
            ],
        )
    conn.commit()
    return len(chunks)