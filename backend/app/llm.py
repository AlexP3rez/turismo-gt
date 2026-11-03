import groq
from groq import Groq

from .config import settings


class LLMError(RuntimeError):
    """Falla al llamar a Groq (llave faltante, límite de uso, red...)."""


_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if not settings.groq_api_key:
        raise LLMError("Falta GROQ_API_KEY en el archivo .env")
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key, timeout=30)
    return _client


def chat(messages: list[dict], tools: list[dict] | None = None,
         temperature: float = 0.2, max_tokens: int = 1500):
    """Una llamada al modelo. `tools` se usa en la Fase 5 (agentes)."""
    kwargs = {
        "model": settings.groq_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if "gpt-oss" in settings.groq_model:
        # Menos razonamiento = respuestas más rápidas y menos tokens consumidos
        kwargs["extra_body"] = {"reasoning_effort": "low"}
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    try:
        return _get_client().chat.completions.create(**kwargs)
    except groq.APIError as e:
        raise LLMError(f"Error al llamar a Groq: {e}") from e


def usage_of(response) -> dict:
    """Tokens consumidos en una respuesta."""
    u = response.usage
    return {
        "prompt_tokens": u.prompt_tokens,
        "completion_tokens": u.completion_tokens,
        "total_tokens": u.total_tokens,
    }