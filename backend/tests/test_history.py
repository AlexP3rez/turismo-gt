from tests.helpers import VEC_ATITLAN, chat


def test_se_guarda_la_conversacion_con_sus_mensajes(client, make_user, db, chunks, embed_as, fake_llm):
    embed_as(VEC_ATITLAN)
    user = make_user()

    cid = chat(client, user["headers"], "¿Qué hacer en Atitlán?").json()["conversation_id"]

    rows = db.execute(
        "SELECT role, content, sources FROM messages WHERE conversation_id = %s ORDER BY id", (cid,)
    ).fetchall()
    assert [r["role"] for r in rows] == ["user", "assistant"]
    assert rows[0]["content"] == "¿Qué hacer en Atitlán?"
    assert rows[1]["sources"][0]["title"] == "Lago de Atitlán"


def test_usuario_consulta_su_historial(client, make_user, chunks, embed_as, fake_llm):
    embed_as(VEC_ATITLAN)
    user = make_user()
    cid = chat(client, user["headers"], "¿Qué hacer en Atitlán?").json()["conversation_id"]

    lista = client.get("/history/conversations", headers=user["headers"]).json()
    assert [c["id"] for c in lista] == [cid]
    assert lista[0]["service_code"] == "rag_chat"

    detalle = client.get(f"/history/conversations/{cid}", headers=user["headers"]).json()
    assert detalle["message_count"] == 2
    assert detalle["total_tokens"] == 150
    assert [m["role"] for m in detalle["messages"]] == ["user", "assistant"]

    # filtro por servicio
    otros = client.get(
        "/history/conversations", params={"service": "itinerary_planner"}, headers=user["headers"]
    ).json()
    assert otros == []


def test_usuario_no_ve_el_historial_de_otro(client, make_user, chunks, embed_as, fake_llm):
    embed_as(VEC_ATITLAN)
    a = make_user("a@test.com")
    b = make_user("b@test.com")
    cid = chat(client, a["headers"], "hola").json()["conversation_id"]

    assert client.get("/history/conversations", headers=b["headers"]).json() == []
    assert client.get(f"/history/conversations/{cid}", headers=b["headers"]).status_code == 404


def test_admin_ve_el_historial_de_todos(client, make_user, chunks, embed_as, fake_llm):
    embed_as(VEC_ATITLAN)
    user = make_user("user@test.com")
    admin = make_user("admin@test.com", role="admin")
    cid = chat(client, user["headers"], "hola").json()["conversation_id"]

    lista = client.get("/admin/history/conversations", headers=admin["headers"]).json()
    assert [c["id"] for c in lista] == [cid]
    assert client.get(f"/admin/history/conversations/{cid}", headers=admin["headers"]).status_code == 200

    filtrada = client.get(
        "/admin/history/conversations", params={"user_id": admin["id"]}, headers=admin["headers"]
    ).json()
    assert filtrada == []

    # el usuario normal no puede usar los endpoints de administrador
    assert client.get("/admin/history/conversations", headers=user["headers"]).status_code == 403