import importlib

import pytest
from werkzeug.security import generate_password_hash

import database.db as db_module


@pytest.fixture
def seeded_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test_spendly.db"))
    db_module.init_db()
    db_module.seed_db()

    conn = db_module.get_db()
    seed_user_id = conn.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()["id"]

    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Empty User", "empty@spendly.com", generate_password_hash("password123")),
    )
    empty_user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"seed_user_id": seed_user_id, "empty_user_id": empty_user_id}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test_spendly.db"))

    import app as app_module
    importlib.reload(app_module)

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as test_client:
        yield test_client


def register_and_login(client, name, email, password):
    client.post(
        "/register",
        data={
            "name": name,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
    )
    client.post("/login", data={"email": email, "password": password})
