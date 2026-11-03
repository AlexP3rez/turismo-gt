from fastapi import HTTPException


def ensure_can_run(conn, user: dict, service_code: str) -> dict:
    """Verifica, ANTES de llamar a la IA, que el servicio esté activo y que el
    usuario tenga tokens disponibles. Devuelve el servicio o lanza 404/403/429."""
    service = conn.execute(
        "SELECT id, code, name, is_active FROM ai_services WHERE code = %s", (service_code,)
    ).fetchone()
    if service is None:
        raise HTTPException(404, "Servicio no encontrado")
    if not service["is_active"]:
        raise HTTPException(403, f"El servicio '{service['name']}' está desactivado por el administrador")

    row = conn.execute(
        "SELECT tokens_used, token_limit FROM users WHERE id = %s", (user["id"],)
    ).fetchone()
    if row["tokens_used"] >= row["token_limit"]:
        raise HTTPException(
            429,
            f"Alcanzaste tu límite de tokens ({row['token_limit']}). "
            "Solicita al administrador que lo amplíe.",
        )
    return service


def record_usage(conn, user_id: int, service_id: int, conversation_id: int | None, usage: dict) -> int:
    """Registra el consumo en usage_log y lo suma al usuario.
    NO hace commit: lo hace quien llama, junto con el resto de lo que guarde.
    Devuelve los tokens que le quedan al usuario."""
    conn.execute(
        """INSERT INTO usage_log
             (user_id, service_id, conversation_id, prompt_tokens, completion_tokens, total_tokens)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (
            user_id,
            service_id,
            conversation_id,
            usage["prompt_tokens"],
            usage["completion_tokens"],
            usage["total_tokens"],
        ),
    )
    row = conn.execute(
        """UPDATE users SET tokens_used = tokens_used + %s
           WHERE id = %s RETURNING token_limit, tokens_used""",
        (usage["total_tokens"], user_id),
    ).fetchone()
    return max(row["token_limit"] - row["tokens_used"], 0)