from app import llm
from tests.helpers import VEC_ATITLAN, VEC_OTRO, chat


def test_responde_con_fuentes(client, make_user, chunks, embed_as, fake_llm):
    embed_as(VEC_ATITLAN)
    user = make_user()

    r = chat(client, user["headers"], "¿Qué puedo hacer en el Lago de Atitlán?")

    assert r.status_code == 200
    data = r.json()
    assert data["sufficient_info"] is True
    assert [s["title"] for s in data["sources"]] == ["Lago de Atitlán"]
    assert data["sources"][0]["score"] > 0.99
    # el fragmento recuperado llegó al modelo como contexto
    assert "Paseo en lancha" in fake_llm.calls[0]["messages"][0]["content"]


def test_avisa_cuando_no_hay_informacion(client, make_user, chunks, embed_as, fake_llm):
    embed_as(VEC_OTRO)  # pregunta sin relación con los fragmentos guardados
    user = make_user()

    r = chat(client, user["headers"], "¿Qué hoteles hay en Flores?")

    data = r.json()
    assert r.status_code == 200
    assert data["sufficient_info"] is False
    assert data["sources"] == []
    # no se enviaron fragmentos irrelevantes al modelo
    assert "No se encontraron fragmentos" in fake_llm.calls[0]["messages"][0]["content"]


def test_memoria_conversacional(client, make_user, chunks, embed_as, fake_llm):
    embed_as(VEC_ATITLAN)
    user = make_user()
    first = chat(client, user["headers"], "¿Qué puedo hacer en Atitlán?")
    cid = first.json()["conversation_id"]

    chat(client, user["headers"], "¿Y cuánto cuesta?", cid)

    enviados = fake_llm.calls[1]["messages"]  # system + pregunta previa + respuesta previa + pregunta nueva
    assert len(enviados) == 4
    assert enviados[1] == {"role": "user", "content": "¿Qué puedo hacer en Atitlán?"}
    assert enviados[2]["role"] == "assistant"
    assert enviados[3] == {"role": "user", "content": "¿Y cuánto cuesta?"}
    # las citas [n] de respuestas anteriores se eliminan del historial
    assert all("[1]" not in m["content"] for m in enviados[1:])


def test_no_se_puede_continuar_una_conversacion_ajena(client, make_user, chunks, embed_as, fake_llm):
    embed_as(VEC_ATITLAN)
    a = make_user("a@test.com")
    b = make_user("b@test.com")
    cid = chat(client, a["headers"], "hola").json()["conversation_id"]

    r = chat(client, b["headers"], "hola", cid)

    assert r.status_code == 404


def test_servicio_desactivado_da_403_sin_llamar_a_la_ia(client, make_user, db, fake_llm):
    db.execute("UPDATE ai_services SET is_active = FALSE WHERE code = 'rag_chat'")
    user = make_user()

    r = chat(client, user["headers"], "hola")

    assert r.status_code == 403
    assert fake_llm.calls == []


def test_si_falla_el_llm_no_se_guarda_ni_se_cobra(client, make_user, db, chunks, embed_as, monkeypatch):
    embed_as(VEC_ATITLAN)

    def caido(*args, **kwargs):
        raise llm.LLMError("servicio caído")

    monkeypatch.setattr(llm, "chat", caido)
    user = make_user()

    r = chat(client, user["headers"], "hola")

    assert r.status_code == 502
    assert db.execute("SELECT count(*) AS n FROM messages").fetchone()["n"] == 0
    assert db.execute("SELECT count(*) AS n FROM usage_log").fetchone()["n"] == 0
    row = db.execute("SELECT tokens_used FROM users WHERE id = %s", (user["id"],)).fetchone()
    assert row["tokens_used"] == 0