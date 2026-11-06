from tests.helpers import VEC_ATITLAN, chat


def test_registra_el_consumo_y_lo_suma_al_usuario(client, make_user, db, chunks, embed_as, fake_llm):
    embed_as(VEC_ATITLAN)
    user = make_user(token_limit=20000)

    r1 = chat(client, user["headers"], "pregunta 1")
    r2 = chat(client, user["headers"], "pregunta 2")

    assert r1.json()["usage"] == {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    assert r2.json()["tokens_remaining"] == 20000 - 300
    log = db.execute(
        """SELECT count(*) AS n, sum(prompt_tokens) AS p, sum(completion_tokens) AS c,
                  sum(total_tokens) AS t FROM usage_log WHERE user_id = %s""",
        (user["id"],),
    ).fetchone()
    assert (log["n"], log["p"], log["c"], log["t"]) == (2, 200, 100, 300)
    row = db.execute("SELECT tokens_used FROM users WHERE id = %s", (user["id"],)).fetchone()
    assert row["tokens_used"] == 300


def test_bloquea_al_alcanzar_el_limite_sin_llamar_a_la_ia(client, make_user, db, chunks, embed_as, fake_llm):
    embed_as(VEC_ATITLAN)
    user = make_user(token_limit=100)

    primera = chat(client, user["headers"], "pregunta 1")
    assert primera.status_code == 200          # tenía saldo: se ejecuta (usa 150 de 100)
    assert primera.json()["tokens_remaining"] == 0   # el saldo nunca es negativo
    llamadas = len(fake_llm.calls)

    segunda = chat(client, user["headers"], "pregunta 2")

    assert segunda.status_code == 429
    assert len(fake_llm.calls) == llamadas     # no se llamó a la IA
    assert db.execute("SELECT count(*) AS n FROM usage_log").fetchone()["n"] == 1


def test_usage_me_coincide_con_el_registro(client, make_user, chunks, embed_as, fake_llm):
    embed_as(VEC_ATITLAN)
    user = make_user()
    chat(client, user["headers"], "pregunta 1")
    chat(client, user["headers"], "pregunta 2")

    uso = client.get("/usage/me", headers=user["headers"]).json()

    assert uso["tokens_used"] == 300
    assert uso["tokens_remaining"] == 20000 - 300
    assert uso["total_queries"] == 2
    assert uso["total_tokens"] == 300
    assert uso["by_service"][0]["service_code"] == "rag_chat"
    assert uso["by_service"][0]["queries"] == 2


def test_reporte_web_y_powerbi_coinciden(client, make_user, chunks, embed_as, fake_llm):
    embed_as(VEC_ATITLAN)
    a = make_user("a@test.com")
    b = make_user("b@test.com")
    admin = make_user("admin@test.com", role="admin")
    chat(client, a["headers"], "pregunta 1")
    chat(client, a["headers"], "pregunta 2")
    chat(client, b["headers"], "pregunta 3")
    key = client.post("/admin/api-keys", json={"name": "Power BI"}, headers=admin["headers"]).json()["api_key"]
    powerbi = {"X-API-Key": key}

    resumen_web = client.get("/reports/summary", headers=admin["headers"]).json()
    resumen_pbi = client.get("/reports/summary", headers=powerbi).json()
    assert resumen_web == resumen_pbi
    assert resumen_pbi[0]["service_code"] == "rag_chat"
    assert resumen_pbi[0]["queries"] == 3
    assert resumen_pbi[0]["total_tokens"] == 450

    filas = client.get("/reports/usage", headers=powerbi).json()
    assert sum(f["queries"] for f in filas) == 3
    assert sum(f["total_tokens"] for f in filas) == 450

    solo_a = client.get("/reports/usage", params={"user_id": a["id"]}, headers=powerbi).json()
    assert sum(f["queries"] for f in solo_a) == 2


def test_filtros_de_fecha_de_los_reportes(client, make_user, chunks, embed_as, fake_llm):
    embed_as(VEC_ATITLAN)
    user = make_user()
    admin = make_user("admin@test.com", role="admin")
    chat(client, user["headers"], "pregunta 1")

    futuro = client.get("/reports/usage", params={"date_from": "2999-01-01"}, headers=admin["headers"])
    assert futuro.json() == []
    invertido = client.get(
        "/reports/usage",
        params={"date_from": "2026-12-01", "date_to": "2026-01-01"},
        headers=admin["headers"],
    )
    assert invertido.status_code == 400


def test_api_key_solo_sirve_para_reportes_y_se_puede_revocar(client, make_user):
    admin = make_user("admin@test.com", role="admin")
    creada = client.post("/admin/api-keys", json={"name": "Power BI"}, headers=admin["headers"]).json()
    powerbi = {"X-API-Key": creada["api_key"]}

    assert client.get("/reports/usage", headers=powerbi).status_code == 200
    assert client.get("/admin/users", headers=powerbi).status_code == 401
    assert client.post("/ai/chat", json={"message": "hola"}, headers=powerbi).status_code == 401
    assert client.get("/reports/usage", headers={"X-API-Key": "tgt_invalida"}).status_code == 401

    client.delete(f"/admin/api-keys/{creada['id']}", headers=admin["headers"])
    assert client.get("/reports/usage", headers=powerbi).status_code == 401


def test_usuario_normal_no_accede_a_los_reportes(client, make_user):
    user = make_user()
    assert client.get("/reports/usage", headers=user["headers"]).status_code == 403
    assert client.get("/admin/usage", headers=user["headers"]).status_code == 403
    assert client.get("/reports/usage").status_code == 401