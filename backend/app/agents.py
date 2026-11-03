import json
from datetime import date

from . import llm, tools

MAX_STEPS = 6              # vueltas máximas del bucle
MAX_REQUEST_TOKENS = 15000  # tope de tokens por petición de agente
MAX_TOOL_CHARS = 4000      # tamaño máximo de cada resultado enviado al modelo
MAX_ANSWER_TOKENS = 2500


def planner_prompt() -> str:
    return f"""Eres el planificador de itinerarios de Turismo GT, una aplicación de turismo en Guatemala. Hoy es {date.today().isoformat()}.
Armas itinerarios usando HERRAMIENTAS. Nunca inventes precios, duraciones, distancias ni datos del clima.

PROCESO:
1. Identifica destino(s), número de días, número de personas, intereses y presupuesto por persona en quetzales. Si falta algo, asume un valor razonable y dilo al inicio.
2. Usa listar_destinos y buscar_actividades: las actividades registradas en la base de datos son tu fuente principal.
3. Consulta el clima del destino con consultar_clima.
4. Si el viaje incluye más de un destino, usa calcular_distancia entre ellos y considera el tiempo de traslado.
5. Si el usuario pide algo que no está en la base de datos (restaurantes, hoteles...), usa buscar_lugares_externos.
6. Elige las actividades y obtén el costo con calcular_costo_plan usando sus IDs. Si supera el presupuesto, reemplaza actividades y vuelve a calcular.

RESPUESTA FINAL (Markdown, en español):
- Un resumen de los supuestos que tomaste.
- Clima esperado y cómo afecta el plan.
- Itinerario por día: actividad, duración y costo aproximado. Considera que un día tiene unas 8 horas de actividades.
- Traslados (km y minutos) si hubo más de un destino.
- Costo total por persona y total del grupo.
- Notas o limitaciones (qué información no pudiste obtener).
Los costos son aproximados. Si no hay actividades registradas para lo pedido, dilo claramente."""


def adjuster_prompt() -> str:
    return f"""Eres el ajustador de planes de Turismo GT, una aplicación de turismo en Guatemala. Hoy es {date.today().isoformat()}.
Recibes un PLAN ACTUAL y un CAMBIO (de presupuesto, de clima u otra circunstancia). Debes reajustar el plan usando HERRAMIENTAS. Nunca inventes precios, duraciones ni datos del clima.

PROCESO:
1. Entiende el cambio y qué partes del plan afecta.
2. Si el cambio involucra clima, usa consultar_clima. Las actividades de categoría naturaleza o aventura (al aire libre) son las más afectadas por lluvia fuerte.
3. Si el cambio involucra presupuesto, usa buscar_actividades (con costo_max) y calcular_costo_plan para encontrar combinaciones que cumplan el nuevo límite.
4. Busca alternativas en la base de datos con buscar_actividades; si no alcanzan, usa buscar_lugares_externos.
5. Obtén el costo del plan nuevo con calcular_costo_plan (no sumes manualmente).

RESPUESTA FINAL (Markdown, en español):
- Qué cambió y por qué (una o dos frases).
- Tabla "Cambios realizados": actividad original -> actividad nueva, con el motivo.
- Plan ajustado por día, con duración y costo aproximado.
- Costo total anterior vs. nuevo.
- Si no fue posible cumplir el cambio por completo, dilo y explica qué se logró.
Los costos son aproximados."""


def _add_usage(total: dict, new: dict) -> None:
    for k in total:
        total[k] += new[k]


def _compact(result: dict, limit: int) -> str:
    text = json.dumps(result, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + '..."(resultado recortado)'


def run_agent(conn, system_prompt: str, user_text: str) -> dict:
    """Bucle de tool calling. Devuelve la respuesta, los pasos y los tokens acumulados."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    steps: list[dict] = []

    for _ in range(MAX_STEPS):
        if usage["total_tokens"] >= MAX_REQUEST_TOKENS:
            break
        response = llm.chat(messages, tools=tools.TOOL_SCHEMAS, max_tokens=MAX_ANSWER_TOKENS)
        _add_usage(usage, llm.usage_of(response))
        msg = response.choices[0].message

        if not msg.tool_calls:  # el modelo ya tiene la respuesta final
            return {"answer": (msg.content or "").strip(), "steps": steps, "usage": usage}

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
                if not isinstance(args, dict):
                    raise ValueError("los argumentos deben ser un objeto JSON")
            except ValueError:
                args, result = {}, {"error": "Los argumentos no son un JSON válido"}
            else:
                result = tools.execute(conn, tc.function.name, args)

            steps.append({
                "step": len(steps) + 1,
                "tool": tc.function.name,
                "arguments": args,
                "result": _compact(result, 700),  # resumen para mostrar en la interfaz
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": _compact(result, MAX_TOOL_CHARS),
            })

    # Se agotaron los pasos o el tope de tokens: se pide la respuesta con lo reunido
    messages.append({
        "role": "user",
        "content": "Redacta ya la respuesta final con la información reunida, sin llamar más "
                   "herramientas. Indica claramente qué información no pudiste obtener.",
    })
    response = llm.chat(messages, tools=tools.TOOL_SCHEMAS, tool_choice="none",
                        max_tokens=MAX_ANSWER_TOKENS)
    _add_usage(usage, llm.usage_of(response))
    answer = (response.choices[0].message.content or "").strip()
    return {
        "answer": answer or "No pude completar la solicitud con la información disponible.",
        "steps": steps,
        "usage": usage,
    }