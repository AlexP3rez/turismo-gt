"""Herramientas que el modelo puede llamar. Cada función recibe la conexión a la BD
y los argumentos que el modelo eligió, y devuelve un dict serializable a JSON."""
import math

import httpx

# Nominatim exige identificar tu aplicación: pon tu correo real aquí
HEADERS = {"User-Agent": "TurismoGT/1.0 (proyecto academico; alexp3rez1102@gmail.com)"}
TIMEOUT = 12

WEATHER_CODES = {
    0: "despejado", 1: "mayormente despejado", 2: "parcialmente nublado", 3: "nublado",
    45: "niebla", 48: "niebla",
    51: "llovizna ligera", 53: "llovizna", 55: "llovizna intensa",
    61: "lluvia ligera", 63: "lluvia moderada", 65: "lluvia fuerte",
    80: "chubascos ligeros", 81: "chubascos", 82: "chubascos fuertes",
    95: "tormenta eléctrica", 96: "tormenta con granizo", 99: "tormenta con granizo fuerte",
}


class ToolError(RuntimeError):
    """Falla controlada de una herramienta (API externa caída, lugar no encontrado...)."""


def _get(url: str, params: dict | None = None):
    try:
        r = httpx.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPError, ValueError) as e:
        raise ToolError(f"No se pudo consultar {url.split('/')[2]}: {e}") from e


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _geocode(place: str) -> tuple[float, float]:
    data = _get(
        "https://nominatim.openstreetmap.org/search",
        {"q": f"{place}, Guatemala", "format": "jsonv2", "limit": 1, "countrycodes": "gt"},
    )
    if not data:
        raise ToolError(f"No se encontró el lugar '{place}'")
    return float(data[0]["lat"]), float(data[0]["lon"])


def resolve_coords(conn, place: str) -> tuple[float, float]:
    """Coordenadas de un lugar: primero el promedio de las actividades registradas
    en la BD (destino o departamento), y si no existe, geocodificación con Nominatim."""
    row = conn.execute(
        """SELECT avg(a.latitude) AS lat, avg(a.longitude) AS lon
           FROM destinations d JOIN activities a ON a.destination_id = d.id
           WHERE (d.name ILIKE %s OR d.department ILIKE %s)
             AND a.latitude IS NOT NULL AND a.longitude IS NOT NULL""",
        (f"%{place}%", f"%{place}%"),
    ).fetchone()
    if row and row["lat"] is not None:
        return float(row["lat"]), float(row["lon"])
    return _geocode(place)


# ---------------------------------------------------------------- BD
def listar_destinos(conn) -> dict:
    rows = conn.execute(
        "SELECT id, name, department, category FROM destinations ORDER BY name"
    ).fetchall()
    return {"destinos": rows}


def buscar_actividades(conn, destino=None, categoria=None, costo_max=None, limite=12) -> dict:
    sql = """SELECT a.id, d.name AS destino, a.name AS actividad, a.category AS categoria,
                    a.est_cost_gtq, a.duration_hours, a.latitude, a.longitude
             FROM activities a JOIN destinations d ON d.id = a.destination_id
             WHERE TRUE"""
    params: list = []
    if destino:
        sql += " AND (d.name ILIKE %s OR d.department ILIKE %s)"
        params += [f"%{destino}%"] * 2
    if categoria:
        sql += " AND a.category ILIKE %s"
        params.append(f"%{categoria}%")
    if costo_max is not None:
        sql += " AND a.est_cost_gtq <= %s"
        params.append(float(costo_max))
    sql += " ORDER BY d.name, a.id LIMIT %s"
    params.append(max(1, min(int(limite), 20)))

    rows = conn.execute(sql, params).fetchall()
    for r in rows:  # Decimal -> float para poder serializar a JSON
        r["costo_gtq"] = float(r.pop("est_cost_gtq"))
        r["duracion_horas"] = float(r.pop("duration_hours"))
    return {"actividades": rows, "total": len(rows)}


def calcular_costo_plan(conn, actividad_ids, personas=1) -> dict:
    ids = [int(i) for i in actividad_ids]
    personas = max(1, int(personas))
    rows = conn.execute(
        "SELECT id, name, est_cost_gtq FROM activities WHERE id = ANY(%s) ORDER BY id", (ids,)
    ).fetchall()
    if not rows:
        raise ToolError("Ninguno de los IDs corresponde a una actividad registrada")
    por_persona = sum(float(r["est_cost_gtq"]) for r in rows)
    return {
        "actividades": [{"id": r["id"], "nombre": r["name"], "costo_gtq": float(r["est_cost_gtq"])} for r in rows],
        "costo_por_persona_gtq": round(por_persona, 2),
        "personas": personas,
        "costo_total_gtq": round(por_persona * personas, 2),
        "nota": "Costos aproximados de las actividades; no incluyen transporte ni hospedaje.",
    }


# ---------------------------------------------------------------- APIs externas
def consultar_clima(conn, lugar, dias=3) -> dict:
    dias = max(1, min(int(dias), 7))
    lat, lon = resolve_coords(conn, lugar)
    data = _get(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": lat,
            "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                     "precipitation_probability_max,precipitation_sum",
            "timezone": "America/Guatemala",
            "forecast_days": dias,
        },
    )
    d = data["daily"]
    return {
        "lugar": lugar,
        "fuente": "Open-Meteo",
        "pronostico": [
            {
                "fecha": d["time"][i],
                "cielo": WEATHER_CODES.get(d["weather_code"][i], f"código {d['weather_code'][i]}"),
                "temp_min_c": d["temperature_2m_min"][i],
                "temp_max_c": d["temperature_2m_max"][i],
                "prob_lluvia_pct": d["precipitation_probability_max"][i],
                "lluvia_mm": d["precipitation_sum"][i],
            }
            for i in range(len(d["time"]))
        ],
    }


def calcular_distancia(conn, origen, destino) -> dict:
    la1, lo1 = resolve_coords(conn, origen)
    la2, lo2 = resolve_coords(conn, destino)
    try:
        data = _get(
            f"https://router.project-osrm.org/route/v1/driving/{lo1},{la1};{lo2},{la2}",
            {"overview": "false"},
        )
        route = data["routes"][0]
        return {
            "origen": origen,
            "destino": destino,
            "distancia_km": round(route["distance"] / 1000, 1),
            "duracion_min": round(route["duration"] / 60),
            "fuente": "OSRM (ruta por carretera)",
        }
    except (ToolError, KeyError, IndexError):
        km = _haversine_km(la1, lo1, la2, lo2) * 1.4
        return {
            "origen": origen,
            "destino": destino,
            "distancia_km": round(km, 1),
            "duracion_min": round(km / 40 * 60),
            "fuente": "ESTIMACIÓN (línea recta x1.4 a 40 km/h): el servicio de rutas no respondió",
        }


def buscar_lugares_externos(conn, tipo, lugar, limite=5) -> dict:
    data = _get(
        "https://nominatim.openstreetmap.org/search",
        {
            "q": f"{tipo} {lugar}",
            "format": "jsonv2",
            "limit": max(1, min(int(limite), 8)),
            "countrycodes": "gt",
            "accept-language": "es",
        },
    )
    return {
        "fuente": "OpenStreetMap (Nominatim)",
        "resultados": [
            {
                "nombre": r.get("name") or r["display_name"].split(",")[0],
                "direccion": r["display_name"],
                "tipo": r.get("type"),
                "lat": float(r["lat"]),
                "lon": float(r["lon"]),
            }
            for r in data
        ],
    }


# ---------------------------------------------------------------- Registro para el modelo
def _schema(name: str, description: str, properties: dict, required: tuple = ()) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": list(required)},
        },
    }


TOOL_SCHEMAS = [
    _schema("listar_destinos", "Lista los destinos turísticos registrados en la base de datos.", {}),
    _schema(
        "buscar_actividades",
        "Busca actividades registradas en la base de datos, con costo en quetzales (GTQ), "
        "duración en horas y categoría. Todos los filtros son opcionales.",
        {
            "destino": {"type": "string", "description": "Nombre del destino o departamento, p. ej. 'Atitlán'"},
            "categoria": {"type": "string", "description": "cultura, naturaleza, aventura, gastronomía, arqueología"},
            "costo_max": {"type": "number", "description": "Costo máximo por persona en GTQ"},
            "limite": {"type": "integer", "description": "Máximo de resultados (por defecto 12)"},
        },
    ),
    _schema(
        "consultar_clima",
        "Pronóstico del clima de un lugar para los próximos días (1 a 7).",
        {
            "lugar": {"type": "string", "description": "Destino, p. ej. 'Antigua Guatemala'"},
            "dias": {"type": "integer", "description": "Cantidad de días de pronóstico (1 a 7)"},
        },
        ("lugar",),
    ),
    _schema(
        "calcular_distancia",
        "Distancia por carretera (km) y tiempo de viaje (minutos) entre dos lugares.",
        {
            "origen": {"type": "string", "description": "Lugar de origen"},
            "destino": {"type": "string", "description": "Lugar de destino"},
        },
        ("origen", "destino"),
    ),
    _schema(
        "buscar_lugares_externos",
        "Busca lugares que NO están en la base de datos (restaurantes, hoteles, museos...) "
        "en OpenStreetMap. Úsala solo cuando la base de datos no tenga lo que se necesita.",
        {
            "tipo": {"type": "string", "description": "Tipo de lugar, p. ej. 'restaurante', 'hotel', 'museo'"},
            "lugar": {"type": "string", "description": "Ciudad o zona, p. ej. 'Antigua Guatemala'"},
            "limite": {"type": "integer", "description": "Máximo de resultados (por defecto 5)"},
        },
        ("tipo", "lugar"),
    ),
    _schema(
        "calcular_costo_plan",
        "Calcula el costo total de un conjunto de actividades de la base de datos a partir de sus IDs. "
        "Úsala siempre para obtener el costo; no sumes manualmente.",
        {
            "actividad_ids": {"type": "array", "items": {"type": "integer"}, "description": "IDs de actividades"},
            "personas": {"type": "integer", "description": "Número de personas (por defecto 1)"},
        },
        ("actividad_ids",),
    ),
]

FUNCTIONS = {
    "listar_destinos": listar_destinos,
    "buscar_actividades": buscar_actividades,
    "consultar_clima": consultar_clima,
    "calcular_distancia": calcular_distancia,
    "buscar_lugares_externos": buscar_lugares_externos,
    "calcular_costo_plan": calcular_costo_plan,
}


def execute(conn, name: str, args: dict) -> dict:
    """Ejecuta una herramienta. Nunca lanza: los errores se devuelven al modelo
    para que pueda explicarlos o intentar otra cosa."""
    fn = FUNCTIONS.get(name)
    if fn is None:
        return {"error": f"La herramienta '{name}' no existe"}
    try:
        return fn(conn, **args)
    except ToolError as e:
        return {"error": str(e)}
    except TypeError as e:
        return {"error": f"Argumentos incorrectos: {e}"}
    except Exception as e:  # noqa: BLE001  (cualquier fallo debe llegar al modelo, no tumbar la API)
        conn.rollback()  # si falló una consulta SQL, la transacción queda abortada
        return {"error": f"La herramienta falló: {e}"}