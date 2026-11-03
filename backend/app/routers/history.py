from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_conn
from ..deps import get_current_user, require_role
from ..schemas_usage import ConversationDetail, ConversationOut

router = APIRouter()

CONV_SELECT = """
SELECT c.id, c.user_id, us.email AS user_email,
       s.code AS service_code, s.name AS service_name,
       c.title, c.created_at,
       (SELECT count(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count,
       (SELECT COALESCE(sum(u.total_tokens), 0)
          FROM usage_log u WHERE u.conversation_id = c.id) AS total_tokens
FROM conversations c
JOIN ai_services s ON s.id = c.service_id
JOIN users us ON us.id = c.user_id
"""


def _list(conn, user_id, service, limit, offset) -> list[dict]:
    where, params = ["TRUE"], []
    if user_id is not None:
        where.append("c.user_id = %s")
        params.append(user_id)
    if service:
        where.append("s.code = %s")
        params.append(service)
    return conn.execute(
        f"{CONV_SELECT} WHERE {' AND '.join(where)} ORDER BY c.id DESC LIMIT %s OFFSET %s",
        (*params, limit, offset),
    ).fetchall()


def _detail(conn, conversation_id: int, user_id: int | None = None) -> dict:
    sql, params = f"{CONV_SELECT} WHERE c.id = %s", [conversation_id]
    if user_id is not None:  # el usuario solo puede ver lo suyo
        sql += " AND c.user_id = %s"
        params.append(user_id)
    conv = conn.execute(sql, params).fetchone()
    if conv is None:
        raise HTTPException(404, "Conversación no encontrada")
    msgs = conn.execute(
        """SELECT id, role, content, sources, steps, created_at
           FROM messages WHERE conversation_id = %s ORDER BY id""",
        (conversation_id,),
    ).fetchall()
    return {**conv, "messages": msgs}


# ---------------- Usuario: su propio historial ----------------
@router.get("/history/conversations", response_model=list[ConversationOut], tags=["Historial"])
def my_conversations(
    service: str | None = Query(None, description="Código del servicio: rag_chat, itinerary_planner, plan_adjuster"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
    conn=Depends(get_conn),
):
    """Mis conversaciones, de la más reciente a la más antigua."""
    return _list(conn, user["id"], service, limit, offset)


@router.get("/history/conversations/{conversation_id}", response_model=ConversationDetail, tags=["Historial"])
def my_conversation(conversation_id: int, user: dict = Depends(get_current_user), conn=Depends(get_conn)):
    """Mensajes de una conversación mía, con sus fuentes (RAG) o pasos (agentes)."""
    return _detail(conn, conversation_id, user["id"])


# ---------------- Administrador: todas las conversaciones ----------------
@router.get("/admin/history/conversations", response_model=list[ConversationOut], tags=["Admin · Historial"])
def all_conversations(
    user_id: int | None = None,
    service: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(require_role("admin")),
    conn=Depends(get_conn),
):
    return _list(conn, user_id, service, limit, offset)


@router.get(
    "/admin/history/conversations/{conversation_id}",
    response_model=ConversationDetail,
    tags=["Admin · Historial"],
)
def any_conversation(
    conversation_id: int, admin: dict = Depends(require_role("admin")), conn=Depends(get_conn)
):
    return _detail(conn, conversation_id)