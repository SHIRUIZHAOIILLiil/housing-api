import pytest
from fastapi.testclient import TestClient

# Adjust this import to match your project if needed.
# Common choices:
# from app.main import app
# from app.main import create_app
from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login_and_get_token(client: TestClient, username: str, password: str) -> str:
    """
    OAuth2 password flow: application/x-www-form-urlencoded
    """
    resp = client.post(
        "/auth/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "access_token" in body
    return body["access_token"]


def register_user(client: TestClient, username: str, email: str, password: str) -> None:
    resp = client.post(
        "/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    # allow 201 or 200 depending on your implementation
    assert resp.status_code in (200, 201), resp.text



def test_frontend_homepage_serves_index_html(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    text = resp.text

    # key UI markers from your demo client
    assert "Housing API Demo Client" in text
    assert "Official Sales Stats" in text
    assert "Official Sales Transactions" in text
    assert "Create Rent Record" in text
    assert "Manage Rent Records" in text


def test_static_js_is_served(client: TestClient):
    resp = client.get("/static/app.js")
    assert resp.status_code == 200
    assert "javascript" in resp.headers.get("content-type", "") or resp.text.strip() != ""
    assert "salesPointBtn" in resp.text
    assert "officialSalesByAreaBtn" in resp.text



def test_sales_point_stats_requires_time_period(client: TestClient):
    resp = client.get("/sales_official/sales-stats", params={"area_code": "E08000035"})
    assert resp.status_code == 422


def test_official_sales_by_area_smoke(client: TestClient):
    resp = client.get(
        "/sales_official/areas/E08000035",
        params={
            "limit": 5,
            "offset": 0,
            "sort_by": "transaction_date",
            "order": "desc",
            "include_total": "false",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # support both plain list and wrapped payloads
    assert isinstance(body, (list, dict))


@pytest.fixture()
def demo_user_credentials():
    return {
        "username": "frontend_demo_user",
        "email": "frontend_demo_user@example.com",
        "password": "StrongPass123!",
    }


@pytest.fixture()
def demo_token(client: TestClient, demo_user_credentials: dict):
    # register once; if your test DB persists and this can collide,
    # either randomise the username or tolerate duplicate-user responses.
    resp = client.post("/auth/register", json=demo_user_credentials)
    assert resp.status_code in (200, 201, 409), resp.text

    token = login_and_get_token(
        client,
        demo_user_credentials["username"],
        demo_user_credentials["password"],
    )
    return token


@pytest.fixture()
def created_rent_record(client: TestClient, demo_token: str):
    payload = {
        "postcode": "LS1 1AA",
        "area_code": "E08000035",
        "time_period": "2024-07",
        "rent": 1200,
        "bedrooms": 2,
        "property_type": "flat",
        "source": "user",
    }

    resp = client.post("/rent_user", json=payload, headers=auth_headers(demo_token))
    assert resp.status_code in (200, 201), resp.text
    body = resp.json()
    assert "id" in body
    return body


def test_create_and_get_rent_record_smoke(client: TestClient, demo_token: str):
    create_payload = {
        "postcode": "LS11AA",
        "area_code": "E08000035",
        "time_period": "2024-07",
        "rent": 1200,
        "bedrooms": 2,
        "property_type": "flat",
        "source": "user",
    }

    create_resp = client.post("/rent_user", json=create_payload, headers=auth_headers(demo_token))
    assert create_resp.status_code in (200, 201), create_resp.text
    created = create_resp.json()
    record_id = created["id"]

    get_resp = client.get(f"/rent_user/{record_id}")
    assert get_resp.status_code == 200, get_resp.text
    fetched = get_resp.json()
    assert fetched["id"] == record_id
    assert fetched["postcode"] == "LS11AA"


def test_put_rent_record_smoke(client: TestClient, demo_token: str, created_rent_record: dict):
    record_id = created_rent_record["id"]

    put_payload = {
        "postcode": "LS11AA",
        "area_code": "E08000035",
        "time_period": "2024-08",
        "rent": 1350,
        "bedrooms": 3,
        "property_type": "terraced",
        "source": "user",
    }

    resp = client.put(
        f"/rent_user/{record_id}",
        json=put_payload,
        headers=auth_headers(demo_token),
    )
    assert resp.status_code == 200, resp.text

    verify = client.get(f"/rent_user/{record_id}")
    assert verify.status_code == 200, verify.text
    body = verify.json()
    assert body["postcode"] == "LS11AA"
    assert body["time_period"] == "2024-08"
    assert body["rent"] == 1350


def test_patch_rent_record_smoke(client: TestClient, demo_token: str, created_rent_record: dict):
    record_id = created_rent_record["id"]

    patch_payload = {
        "rent": 1400,
        "bedrooms": 1,
    }

    resp = client.patch(
        f"/rent_user/{record_id}",
        json=patch_payload,
        headers=auth_headers(demo_token),
    )
    assert resp.status_code == 200, resp.text

    verify = client.get(f"/rent_user/{record_id}")
    assert verify.status_code == 200, verify.text
    body = verify.json()
    assert body["rent"] == 1400
    assert body["bedrooms"] == 1


def test_delete_rent_record_smoke(client: TestClient, demo_token: str, created_rent_record: dict):
    record_id = created_rent_record["id"]

    resp = client.delete(
        f"/rent_user/{record_id}",
        headers=auth_headers(demo_token),
    )
    assert resp.status_code in (200, 204), resp.text

    verify = client.get(f"/rent_user/{record_id}")
    assert verify.status_code == 404



@pytest.fixture()
def created_sales_record(client: TestClient, demo_token: str):
    payload = {
        "postcode": "LS11AA",
        "area_code": "E08000035",
        "time_period": "2024-07",
        "price": 250000,
        "property_type": "flat",
        "source": "user",
    }

    resp = client.post(
        "/user-sales-transactions",
        json=payload,
        headers=auth_headers(demo_token),
    )
    assert resp.status_code in (200, 201), resp.text
    body = resp.json()
    assert "id" in body
    return body


def test_create_and_get_sales_record_smoke(client: TestClient, demo_token: str):
    payload = {
        "postcode": "LS11AA",
        "area_code": "E08000035",
        "time_period": "2024-07",
        "price": 250000,
        "property_type": "flat",
        "source": "user",
    }

    create_resp = client.post(
        "/user-sales-transactions",
        json=payload,
        headers=auth_headers(demo_token),
    )
    assert create_resp.status_code in (200, 201), create_resp.text
    created = create_resp.json()
    record_id = created["id"]

    get_resp = client.get(f"/user-sales-transactions/{record_id}")
    assert get_resp.status_code == 200, get_resp.text
    fetched = get_resp.json()
    assert fetched["id"] == record_id
    assert fetched["price"] == 250000


def test_list_sales_records_smoke(client: TestClient):
    resp = client.get(
        "/user-sales-transactions",
        params={"limit": 10},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, (list, dict))


def test_put_sales_record_smoke(client: TestClient, demo_token: str, created_sales_record: dict):
    record_id = created_sales_record["id"]

    put_payload = {
        "postcode": "LS11AA",
        "area_code": "E08000035",
        "time_period": "2024-08",
        "price": 300000,
        "property_type": "terraced",
        "source": "user",
    }

    resp = client.put(
        f"/user-sales-transactions/{record_id}",
        json=put_payload,
        headers=auth_headers(demo_token),
    )
    assert resp.status_code == 200, resp.text

    verify = client.get(f"/user-sales-transactions/{record_id}")
    assert verify.status_code == 200, verify.text
    body = verify.json()
    assert body["price"] == 300000
    assert body["property_type"] == "terraced"


def test_patch_sales_record_smoke(client: TestClient, demo_token: str, created_sales_record: dict):
    record_id = created_sales_record["id"]

    patch_payload = {
        "price": 320000,
    }

    resp = client.patch(
        f"/user-sales-transactions/{record_id}",
        json=patch_payload,
        headers=auth_headers(demo_token),
    )
    assert resp.status_code == 200, resp.text

    verify = client.get(f"/user-sales-transactions/{record_id}")
    assert verify.status_code == 200, verify.text
    body = verify.json()
    assert body["price"] == 320000


def test_delete_sales_record_smoke(client: TestClient, demo_token: str, created_sales_record: dict):
    record_id = created_sales_record["id"]

    resp = client.delete(
        f"/user-sales-transactions/{record_id}",
        headers=auth_headers(demo_token),
    )
    assert resp.status_code in (200, 204), resp.text

    verify = client.get(f"/user-sales-transactions/{record_id}")
    assert verify.status_code == 404
