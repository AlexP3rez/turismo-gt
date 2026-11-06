def test_registro_y_login(client):
    r = client.post(
        "/auth/register",
        json={"email": "nuevo@test.com", "full_name": "Nuevo Usuario", "password": "Clave12345"},
    )
    assert r.status_code == 201
    assert r.json()["role"] == "user"   # el registro público nunca crea administradores

    login = client.post("/auth/login", data={"username": "nuevo@test.com", "password": "Clave12345"})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/auth/me", headers=headers).json()["email"] == "nuevo@test.com"

    mala = client.post("/auth/login", data={"username": "nuevo@test.com", "password": "incorrecta"})
    assert mala.status_code == 401


def test_roles_restringen_los_endpoints_de_administrador(client, make_user):
    user = make_user("user@test.com")
    admin = make_user("admin@test.com", role="admin")

    assert client.get("/admin/users").status_code == 401
    assert client.get("/admin/users", headers=user["headers"]).status_code == 403
    assert client.get("/admin/users", headers=admin["headers"]).status_code == 200


def test_usuario_desactivado_pierde_el_acceso(client, make_user, db):
    user = make_user()
    assert client.get("/auth/me", headers=user["headers"]).status_code == 200

    db.execute("UPDATE users SET is_active = FALSE WHERE id = %s", (user["id"],))

    assert client.get("/auth/me", headers=user["headers"]).status_code == 401