def update_row(conn, table: str, row_id: int, values: dict, returning: str):
    """UPDATE dinámico por id. Devuelve la fila actualizada o None si no existe.

    `table` y las llaves de `values` salen del código (campos de los esquemas
    Pydantic), nunca de texto escrito por el usuario; los valores sí van parametrizados.
    """
    cols = ", ".join(f"{k} = %s" for k in values)
    return conn.execute(
        f"UPDATE {table} SET {cols} WHERE id = %s RETURNING {returning}",
        (*values.values(), row_id),
    ).fetchone()