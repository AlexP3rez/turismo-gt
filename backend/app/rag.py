import re

from . import knowledge, llm

TOP_K = 5              # fragmentos que se recuperan
MIN_SCORE = 0.55       # similitud mínima (0 a 1). Ajústala según tus pruebas
HISTORY_MESSAGES = 8   # mensajes previos que se envían como memoria

SYSTEM_PROMPT = """Eres el asistente virtual de Turismo GT, una aplicación sobre turismo en Guatemala.

REGLAS:
1. Responde ÚNICAMENTE con la información del CONTEXTO. No uses conocimiento propio ni inventes datos, precios, horarios o lugares.
2. Cada dato que uses debe llevar la cita de su fragmento, por ejemplo [1] o [2].
3. Si el CONTEXTO no contiene información suficiente para responder, dilo claramente ("No tengo información suficiente en la base de datos sobre eso"), sin citar fuentes y sin inventar. Puedes sugerir reformular la pregunta.
4. Si el usuario solo saluda o agradece, responde con cortesía y ofrece ayuda sobre destinos y actividades, sin citas.
5. Responde en español, de forma clara y breve.

CONTEXTO:
{context}"""


def retrieve(conn, query: str, k: int = TOP_K, min_score: float = MIN_SCORE) -> list[dict]:
    """Búsqueda vectorial: los k fragmentos más cercanos con similitud >= min_score."""
    vec = knowledge.to_pgvector(knowledge.embed_query(query))
    rows = conn.execute(
        """SELECT id, destination_id, source_title, content,
                  1 - (embedding <=> %s::vector) AS score
           FROM document_chunks
           WHERE embedding IS NOT NULL
           ORDER BY embedding <=> %s::vector
           LIMIT %s""",
        (vec, vec, k),
    ).fetchall()
    return [r for r in rows if r["score"] >= min_score]


def build_context(chunks: list[dict]) -> str:
    if not chunks:
        return "(No se encontraron fragmentos relevantes en la base de datos.)"
    return "\n\n".join(
        f"[{i}] Fuente: {c['source_title']}\n{c['content']}" for i, c in enumerate(chunks, 1)
    )


def clean_history(history: list[dict]) -> list[dict]:
    """Quita las citas [n] de las respuestas previas: su numeración ya no aplica."""
    return [
        {"role": m["role"], "content": re.sub(r"\s*\[\d+\]", "", m["content"])}
        for m in history
    ]


def answer(conn, question: str, history: list[dict]) -> dict:
    """Responde una pregunta con RAG. `history` son los mensajes previos
    (dicts con role y content, del más antiguo al más reciente)."""
    # Para preguntas de seguimiento, la búsqueda incluye el mensaje anterior del usuario
    prev_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
    chunks = retrieve(conn, f"{prev_user} {question}".strip())

    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT.format(context=build_context(chunks))}]
        + clean_history(history)
        + [{"role": "user", "content": question}]
    )
    response = llm.chat(messages)
    text = (response.choices[0].message.content or "").strip()

    # Fuentes = solo los fragmentos que el modelo citó
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", text)})
    sources = [
        {
            "id": chunks[i - 1]["id"],
            "destination_id": chunks[i - 1]["destination_id"],
            "title": chunks[i - 1]["source_title"],
            "score": round(float(chunks[i - 1]["score"]), 3),
        }
        for i in cited
        if 1 <= i <= len(chunks)
    ]
    return {
        "answer": text,
        "sources": sources,
        "sufficient_info": bool(sources),
        "usage": llm.usage_of(response),
    }