from fastapi import APIRouter, Depends, HTTPException
from psycopg.types.json import Jsonb

from .. import agents, knowledge, llm, rag
from ..ai_gateway import ensure_can_run, record_usage
from ..database import get_conn
from ..deps import get_current_user
from ..schemas import AdjustIn, AgentIn, AgentOut, ChatIn, ChatOut

router = APIRouter(prefix="/ai", tags=["Servicios de IA"])


def load_history(conn, conversation_id: int, limit: int = rag.HISTORY_MESSAGES) -> list[dict]:
    rows = conn.execute(
        """SELECT role, content FROM messages
           WHERE conversation_id = %s ORDER BY id DESC LIMIT %s""",
        (conversation_id, limit),
    ).fetchall()
    return list(reversed(rows))  # del más antiguo al más reciente


@router.post("/chat", response_model=ChatOut)
def chat(data: ChatIn, user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    """Chatbot con RAG sobre los destinos y actividades registrados.

    Sin `conversation_id` inicia una conversación; con él, continúa la existente (memoria)."""
    # 1. Servicio activo y tokens disponibles (si no, 403 / 429 y no se llama a la IA)
    service = ensure_can_run(conn, user, "rag_chat")

    # 2. Conversación existente: debe ser del usuario y de este servicio
    history: list[dict] = []
    if data.conversation_id:
        conv = conn.execute(
            "SELECT id FROM conversations WHERE id = %s AND user_id = %s AND service_id = %s",
            (data.conversation_id, user["id"], service["id"]),
        ).fetchone()
        if conv is None:
            raise HTTPException(404, "Conversación no encontrada")
        history = load_history(conn, conv["id"])

    # 3. RAG + modelo
    try:
        result = rag.answer(conn, data.message, history)
    except (knowledge.EmbeddingError, llm.LLMError) as e:
        raise HTTPException(502, f"El servicio de IA no está disponible: {e}")

    # 4. Guardar conversación, mensajes y consumo en una sola transacción
    conversation_id = data.conversation_id
    if conversation_id is None:
        conversation_id = conn.execute(
            """INSERT INTO conversations (user_id, service_id, title)
               VALUES (%s, %s, %s) RETURNING id""",
            (user["id"], service["id"], data.message[:60]),
        ).fetchone()["id"]

    conn.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (%s, 'user', %s)",
        (conversation_id, data.message),
    )
    conn.execute(
        """INSERT INTO messages (conversation_id, role, content, sources)
           VALUES (%s, 'assistant', %s, %s)""",
        (conversation_id, result["answer"], Jsonb(result["sources"])),
    )
    remaining = record_usage(conn, user["id"], service["id"], conversation_id, result["usage"])
    conn.commit()

    return {
        "conversation_id": conversation_id,
        "answer": result["answer"],
        "sources": result["sources"],
        "sufficient_info": result["sufficient_info"],
        "usage": result["usage"],
        "tokens_remaining": remaining,
    }

# ======================= AGENTES (Fase 5) =======================
def run_agent_service(conn, user: dict, service_code: str, title: str,
                      user_text: str, system_prompt: str) -> dict:
    """Flujo común de los agentes: verificar -> ejecutar -> guardar -> registrar consumo."""
    service = ensure_can_run(conn, user, service_code)

    try:
        result = agents.run_agent(conn, system_prompt, user_text)
    except llm.LLMError as e:
        raise HTTPException(502, f"El servicio de IA no está disponible: {e}")

    conversation_id = conn.execute(
        """INSERT INTO conversations (user_id, service_id, title)
           VALUES (%s, %s, %s) RETURNING id""",
        (user["id"], service["id"], title[:60]),
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (%s, 'user', %s)",
        (conversation_id, user_text),
    )
    conn.execute(
        """INSERT INTO messages (conversation_id, role, content, steps)
           VALUES (%s, 'assistant', %s, %s)""",
        (conversation_id, result["answer"], Jsonb(result["steps"])),
    )
    remaining = record_usage(conn, user["id"], service["id"], conversation_id, result["usage"])
    conn.commit()

    return {
        "conversation_id": conversation_id,
        "answer": result["answer"],
        "steps": result["steps"],
        "usage": result["usage"],
        "tokens_remaining": remaining,
    }


@router.post("/itinerary", response_model=AgentOut)
def itinerary(data: AgentIn, user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    """Agente planificador: busca actividades, consulta clima y distancias,
    calcula costos y arma el itinerario."""
    return run_agent_service(
        conn, user, "itinerary_planner", data.message, data.message, agents.planner_prompt()
    )


@router.post("/adjust-plan", response_model=AgentOut)
def adjust_plan(data: AdjustIn, user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    """Agente ajustador: recibe un plan y un cambio (presupuesto o clima),
    busca alternativas y reajusta las actividades."""
    user_text = f"CAMBIO SOLICITADO:\n{data.change}\n\nPLAN ACTUAL:\n{data.plan}"
    return run_agent_service(
        conn, user, "plan_adjuster", data.change, user_text, agents.adjuster_prompt()
    )