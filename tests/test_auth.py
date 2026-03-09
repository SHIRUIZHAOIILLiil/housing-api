import json


def test_register_success_creates_user_and_audit_log(client, db_conn):
    payload = {
        "username": "alice01",
        "email": "alice01@example.com",
        "password": "Alice123"
    }

    r = client.post("/auth/register", json=payload)
    assert r.status_code == 200, r.text

    body = r.json()
    assert body["username"] == "alice01"
    assert body["email"] == "alice01@example.com"
    assert "id" in body
    assert "created_at" in body

    row = db_conn.execute(
        "SELECT * FROM users WHERE username = ?",
        ("alice01",)
    ).fetchone()
    assert row is not None

    audit = db_conn.execute(
        "SELECT * FROM audit_logs WHERE resource_type = 'users' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert audit is not None
    assert audit["action"] == "CREATE"
    assert audit["resource_id"] == body["id"]

    detail = json.loads(audit["detail"])
    assert detail["username"] == "alice01"
    assert detail["email"] == "alice01@example.com"


def test_register_duplicate_user_returns_409(client):
    payload = {
        "username": "dupuser",
        "email": "dupuser@example.com",
        "password": "Dup12345"
    }

    r1 = client.post("/auth/register", json=payload)
    assert r1.status_code == 200, r1.text

    r2 = client.post("/auth/register", json=payload)
    assert r2.status_code == 409, r2.text
    assert "detail" in r2.json()


def test_login_success_returns_token_and_request_id(client, registered_user, db_conn):
    payload, user = registered_user

    r = client.post(
        "/auth/login",
        data={
            "username": payload["username"],
            "password": payload["password"],
        },
    )
    assert r.status_code == 200, r.text

    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert "X-Request-ID" in r.headers
    assert r.headers["X-Request-ID"]

    audit = db_conn.execute(
        "SELECT * FROM audit_logs WHERE action = 'LOGIN_SUCCESS' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert audit is not None
    assert audit["resource_type"] == "auth"
    assert audit["user_id"] == user["id"]
    assert audit["request_id"] == r.headers["X-Request-ID"]

    detail = json.loads(audit["detail"])
    assert detail["login"] == payload["username"]


def test_login_wrong_password_returns_401_and_failed_audit(client, registered_user, db_conn):
    payload, user = registered_user

    r = client.post(
        "/auth/login",
        data={
            "username": payload["username"],
            "password": "Wrong1234",
        },
    )
    assert r.status_code == 401, r.text
    assert "detail" in r.json()

    audit = db_conn.execute(
        "SELECT * FROM audit_logs WHERE action = 'LOGIN_FAILED' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert audit is not None
    assert audit["resource_type"] == "auth"
    assert audit["user_id"] == user["id"]

    detail = json.loads(audit["detail"])
    assert detail["login"] == payload["username"]
    assert detail["reason"] == "invalid password"


def test_login_unknown_user_returns_401_and_failed_audit(client, db_conn):
    r = client.post(
        "/auth/login",
        data={
            "username": "nobody",
            "password": "Nobody123",
        },
    )
    assert r.status_code == 401, r.text
    assert "detail" in r.json()

    audit = db_conn.execute(
        "SELECT * FROM audit_logs WHERE action = 'LOGIN_FAILED' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert audit is not None
    assert audit["resource_type"] == "auth"
    assert audit["user_id"] is None

    detail = json.loads(audit["detail"])
    assert detail["login"] == "nobody"
    assert detail["reason"] == "user not found"

def test_register_duplicate_does_not_create_extra_user(client, db_conn):
    payload = {
        "username": "dupcheck",
        "email": "dupcheck@example.com",
        "password": "DupCheck123"
    }

    before = db_conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]

    r1 = client.post("/auth/register", json=payload)
    assert r1.status_code == 200, r1.text

    mid = db_conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    assert mid == before + 1

    r2 = client.post("/auth/register", json=payload)
    assert r2.status_code == 409, r2.text

    after = db_conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    assert after == mid

def test_login_failed_request_id_matches_response_header(client, registered_user, db_conn):
    payload, _ = registered_user

    r = client.post(
        "/auth/login",
        data={"username": payload["username"], "password": "Wrong1234"},
    )
    assert r.status_code == 401, r.text
    assert "X-Request-ID" in r.headers

    audit = db_conn.execute(
        "SELECT * FROM audit_logs WHERE action = 'LOGIN_FAILED' ORDER BY id DESC LIMIT 1"
    ).fetchone()

    assert audit is not None
    assert audit["request_id"] == r.headers["X-Request-ID"]