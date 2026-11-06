import json
from types import SimpleNamespace

# Vectores de 768 dimensiones en direcciones ortogonales (similitud coseno = 0)
VEC_ATITLAN = [1.0] + [0.0] * 767
VEC_OTRO = [0.0, 1.0] + [0.0] * 766


def make_response(content="", tool_calls=None, prompt=100, completion=50):
    """Imita la respuesta del SDK de Groq (solo los campos que usa la app)."""
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    usage = SimpleNamespace(
        prompt_tokens=prompt, completion_tokens=completion, total_tokens=prompt + completion
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)


def make_tool_call(name, args, call_id="call_1"):
    """Imita una llamada a herramienta pedida por el modelo."""
    function = SimpleNamespace(name=name, arguments=json.dumps(args))
    return SimpleNamespace(id=call_id, function=function)


def chat(client, headers, message, conversation_id=None):
    body = {"message": message}
    if conversation_id:
        body["conversation_id"] = conversation_id
    return client.post("/ai/chat", json=body, headers=headers)