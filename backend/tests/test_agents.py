from app import agents, tools
from tests.helpers import make_response, make_tool_call

PLAN = "Día 1: Paseo en lancha entre pueblos (Q100, 5 h). Día 2: Kayak al amanecer (Q120, 3 h)."


def test_planificador_ejecuta_herramientas_y_devuelve_pasos(client, make_user, db, fake_llm):
    ids = [
        r["id"]
        for r in db.execute(
            "SELECT id FROM activities WHERE name IN "
            "('Paseo en lancha entre pueblos', 'Cooperativa de tejidos en San Juan')"
        ).fetchall()
    ]
    fake_llm.queue = [
        make_response(tool_calls=[make_tool_call("buscar_actividades", {"destino": "Atitlán"}, "c1")]),
        make_response(
            tool_calls=[make_tool_call("calcular_costo_plan", {"actividad_ids": ids, "personas": 2}, "c2")]
        ),
        make_response("Itinerario: Día 1 paseo en lancha y tejidos. Costo total Q260."),
    ]
    user = make_user()

    r = client.post(
        "/ai/itinerary",
        json={"message": "Viaje de 1 día a Atitlán para 2 personas con Q300"},
        headers=user["headers"],
    )

    assert r.status_code == 200
    data = r.json()
    assert [s["tool"] for s in data["steps"]] == ["buscar_actividades", "calcular_costo_plan"]
    assert "Paseo en lancha" in data["steps"][0]["result"]   # datos reales de la BD
    assert "260.0" in data["steps"][1]["result"]             # (100 + 30) x 2 personas
    assert data["answer"].startswith("Itinerario")
    # el resultado de la herramienta se le devolvió al modelo
    assert fake_llm.calls[1]["messages"][-1]["role"] == "tool"
    # 3 llamadas al modelo de 150 tokens = 1 sola consulta registrada de 450
    assert data["usage"]["total_tokens"] == 450
    log = db.execute("SELECT count(*) AS n, sum(total_tokens) AS t FROM usage_log").fetchone()
    assert (log["n"], log["t"]) == (1, 450)
    used = db.execute("SELECT tokens_used FROM users WHERE id = %s", (user["id"],)).fetchone()
    assert used["tokens_used"] == 450


def test_ajustador_recibe_plan_y_cambio(client, make_user, db, fake_llm):
    fake_llm.queue = [make_response("Plan ajustado: se reemplaza el kayak. Total Q130.")]
    user = make_user()

    r = client.post(
        "/ai/adjust-plan",
        json={"plan": PLAN, "change": "El presupuesto bajó a Q150 por persona"},
        headers=user["headers"],
    )

    assert r.status_code == 200
    enviado = fake_llm.calls[0]["messages"][1]["content"]
    assert "CAMBIO SOLICITADO" in enviado and "Kayak" in enviado
    code = db.execute(
        "SELECT s.code FROM usage_log u JOIN ai_services s ON s.id = u.service_id"
    ).fetchone()["code"]
    assert code == "plan_adjuster"


def test_herramienta_inexistente_se_informa_al_modelo(client, make_user, fake_llm):
    fake_llm.queue = [
        make_response(tool_calls=[make_tool_call("volar_a_la_luna", {}, "c1")]),
        make_response("No pude usar esa herramienta."),
    ]
    user = make_user()

    r = client.post("/ai/itinerary", json={"message": "Quiero un viaje a la luna"}, headers=user["headers"])

    assert r.status_code == 200
    assert "no existe" in r.json()["steps"][0]["result"]


def test_el_bucle_se_corta_al_llegar_al_maximo_de_pasos(client, make_user, fake_llm):
    fake_llm.queue = [
        make_response(tool_calls=[make_tool_call("listar_destinos", {}, f"c{i}")])
        for i in range(agents.MAX_STEPS)
    ] + [make_response("Respuesta final forzada")]
    user = make_user()

    r = client.post("/ai/itinerary", json={"message": "Plan interminable"}, headers=user["headers"])

    data = r.json()
    assert len(data["steps"]) == agents.MAX_STEPS
    assert data["answer"] == "Respuesta final forzada"
    assert fake_llm.calls[-1]["tool_choice"] == "none"  # última llamada: sin herramientas


def test_el_bucle_se_corta_por_tope_de_tokens(client, make_user, fake_llm):
    pesada = dict(prompt=9000, completion=1000)  # 10,000 tokens por llamada
    fake_llm.queue = [
        make_response(tool_calls=[make_tool_call("listar_destinos", {}, "c1")], **pesada),
        make_response(tool_calls=[make_tool_call("listar_destinos", {}, "c2")], **pesada),
        make_response("Respuesta con lo reunido"),
    ]
    user = make_user(token_limit=100000)

    r = client.post("/ai/itinerary", json={"message": "Plan costoso"}, headers=user["headers"])

    data = r.json()
    assert len(fake_llm.calls) == 3                      # 2 con herramientas + la respuesta forzada
    assert fake_llm.calls[-1]["tool_choice"] == "none"
    assert data["usage"]["total_tokens"] == 20150


# ----------------------------- herramientas -----------------------------
def test_buscar_actividades_filtra_por_destino_y_costo(db):
    atitlan = tools.execute(db, "buscar_actividades", {"destino": "Atitlán"})
    assert atitlan["total"] == 3
    assert all(a["destino"] == "Lago de Atitlán" for a in atitlan["actividades"])

    baratas = tools.execute(db, "buscar_actividades", {"costo_max": 50})
    assert len(baratas["actividades"]) >= 5
    assert all(a["costo_gtq"] <= 50 for a in baratas["actividades"])


def test_calcular_costo_con_ids_invalidos_devuelve_error(db):
    assert "error" in tools.execute(db, "calcular_costo_plan", {"actividad_ids": [999999]})
    assert "error" in tools.execute(db, "buscar_actividades", {"argumento_falso": 1})


def test_consultar_clima_interpreta_la_respuesta(db, monkeypatch):
    fake = {
        "daily": {
            "time": ["2026-11-05"],
            "weather_code": [63],
            "temperature_2m_max": [24.0],
            "temperature_2m_min": [12.0],
            "precipitation_probability_max": [80],
            "precipitation_sum": [9.5],
        }
    }
    monkeypatch.setattr(tools, "_get", lambda url, params=None: fake)

    res = tools.execute(db, "consultar_clima", {"lugar": "Atitlán", "dias": 1})

    assert res["pronostico"][0]["cielo"] == "lluvia moderada"
    assert res["pronostico"][0]["prob_lluvia_pct"] == 80


def test_distancia_usa_estimacion_si_falla_el_servicio_de_rutas(db, monkeypatch):
    def sin_red(url, params=None):
        raise tools.ToolError("sin conexión")

    monkeypatch.setattr(tools, "_get", sin_red)

    res = tools.execute(db, "calcular_distancia", {"origen": "Antigua", "destino": "Quetzaltenango"})

    assert "ESTIMACIÓN" in res["fuente"]
    assert 50 < res["distancia_km"] < 300