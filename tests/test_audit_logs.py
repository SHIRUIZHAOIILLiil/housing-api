import json


def get_valid_postcode_and_area_code(client):
    r = client.get("/postcode_map", params={"limit": 1})
    assert r.status_code == 200, r.text
    items = r.json()
    assert items
    return items[0]["postcode"], items[0]["area_code"]


def test_rent_create_writes_audit_and_request_id(client, db_conn, auth_headers):
    postcode, area_code = get_valid_postcode_and_area_code(client)

    r = client.post(
        "/rent_user",
        json={
            "postcode": postcode,
            "area_code": area_code,
            "time_period": "2024-09",
            "rent": 1450,
            "bedrooms": 2,
            "property_type": "flat",
            "source": "user",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()

    assert "X-Request-ID" in r.headers
    request_id = r.headers["X-Request-ID"]

    audit = db_conn.execute(
        "SELECT * FROM audit_logs WHERE resource_type = 'rent_stats_user' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert audit is not None
    assert audit["action"] == "CREATE"
    assert audit["resource_id"] == body["id"]
    assert audit["request_id"] == request_id

    detail = json.loads(audit["detail"])
    assert detail["after"]["postcode"] == postcode
    assert detail["after"]["area_code"] == area_code
    assert detail["after"]["rent"] == 1450.0


def test_rent_update_writes_update_audit(client, db_conn, auth_headers):
    postcode, area_code = get_valid_postcode_and_area_code(client)

    created = client.post(
        "/rent_user",
        json={
            "postcode": postcode,
            "area_code": area_code,
            "time_period": "2024-09",
            "rent": 1450,
            "bedrooms": 2,
            "property_type": "flat",
            "source": "user",
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    rid = created.json()["id"]

    updated = client.patch(
        f"/rent_user/{rid}",
        json={"rent": 1520},
        headers=auth_headers,
    )
    assert updated.status_code == 200, updated.text

    audit = db_conn.execute(
        "SELECT * FROM audit_logs WHERE action = 'UPDATE' AND resource_type = 'rent_stats_user' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert audit is not None
    assert audit["resource_id"] == rid

    detail = json.loads(audit["detail"])
    assert detail["before"]["rent"] == 1450.0
    assert detail["after"]["rent"] == 1520.0


def test_rent_delete_writes_delete_audit(client, db_conn, auth_headers):
    postcode, area_code = get_valid_postcode_and_area_code(client)

    created = client.post(
        "/rent_user",
        json={
            "postcode": postcode,
            "area_code": area_code,
            "time_period": "2024-09",
            "rent": 1450,
            "bedrooms": 2,
            "property_type": "flat",
            "source": "user",
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    rid = created.json()["id"]

    deleted = client.delete(f"/rent_user/{rid}", headers=auth_headers)
    assert deleted.status_code == 204, deleted.text

    audit = db_conn.execute(
        "SELECT * FROM audit_logs WHERE action = 'DELETE' AND resource_type = 'rent_stats_user' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert audit is not None
    assert audit["resource_id"] == rid

    detail = json.loads(audit["detail"])
    assert detail["before"]["id"] == rid


def test_sales_create_writes_audit_and_request_id(client, db_conn, auth_headers):
    postcode, area_code = get_valid_postcode_and_area_code(client)

    r = client.post(
        "/user-sales-transactions",
        json={
            "postcode": postcode,
            "area_code": area_code,
            "time_period": "2024-09",
            "price": 320000,
            "property_type": "flat",
            "source": "user",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()

    assert "X-Request-ID" in r.headers
    request_id = r.headers["X-Request-ID"]

    audit = db_conn.execute(
        "SELECT * FROM audit_logs WHERE resource_type = 'sales_transactions_user' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert audit is not None
    assert audit["action"] == "CREATE"
    assert audit["resource_id"] == body["id"]
    assert audit["request_id"] == request_id

    detail = json.loads(audit["detail"])
    assert detail["after"]["postcode"] == postcode
    assert detail["after"]["price"] == 320000.0


def test_protected_endpoints_require_token(client):
    r1 = client.post(
        "/rent_user",
        json={
            "postcode": "LS29JT",
            "area_code": "E08000035",
            "time_period": "2024-09",
            "rent": 1400,
            "bedrooms": 2,
            "property_type": "flat",
            "source": "user",
        },
    )
    assert r1.status_code == 401, r1.text

    r2 = client.post(
        "/user-sales-transactions",
        json={
            "postcode": "LS29JT",
            "area_code": "E08000035",
            "time_period": "2024-09",
            "price": 320000,
            "property_type": "flat",
            "source": "user",
        },
    )
    assert r2.status_code == 401, r2.text

def test_sales_create_increases_audit_log_count_by_one(client, db_conn, auth_headers):
    before = db_conn.execute("SELECT COUNT(*) AS c FROM audit_logs").fetchone()["c"]

    r = client.post(
        "/user-sales-transactions",
        json={
            "postcode": "LS29JT",
            "area_code": "E08000035",
            "time_period": "2024-09",
            "price": 350000,
            "property_type": "flat",
            "source": "user",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text

    after = db_conn.execute("SELECT COUNT(*) AS c FROM audit_logs").fetchone()["c"]
    assert after == before + 1