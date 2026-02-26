import pytest

BASE = {"limit": 20, "offset": 0}

def assert_is_paged_response(payload: dict):
    assert "items" in payload and "meta" in payload
    assert isinstance(payload["items"], list)
    assert payload["meta"]["count"] == len(payload["items"])

def get_any_area_code(client) -> str:
    r = client.get("/sales_official", params={"limit": 1, "offset": 0})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items, "No seed data in sales_official"
    return items[0]["area_code"]

def test_sales_official_area_ok(client):
    area_code = get_any_area_code(client)
    r = client.get(f"/sales_official/areas/{area_code}", params=BASE)
    assert r.status_code == 200
    data = r.json()
    assert_is_paged_response(data)
    for it in data["items"]:
        assert it["area_code"] == area_code

def test_sales_official_area_not_found(client):
    r = client.get("/sales_official/areas/NO_SUCH_AREA", params=BASE)
    assert r.status_code == 404

def test_sales_official_area_pagination_ok(client):
    area_code = get_any_area_code(client)
    r = client.get(f"/sales_official/areas/{area_code}", params={"limit": 1, "offset": 0})
    assert r.status_code == 200
    assert_is_paged_response(r.json())
    assert r.json()["meta"]["limit"] == 1
    assert len(r.json()["items"]) <= 1


@pytest.mark.parametrize("params", [
    {"postcode_like": "LS"},
    {"date_from": "2020-01-01", "date_to": "2020-12-31"},
    {"min_price": 100000, "max_price": 300000},
    {"property_type": "F"},
    {"tenure": "F"},
    {"new_build": "Y"},
    {"new_build": "N"},
    {"sort_by": "transaction_date", "order": "desc"},
    {"sort_by": "price", "order": "asc"},
    {"include_total": True},
])
def test_sales_official_area_filters_smoke(client, params):
    area_code = get_any_area_code(client)
    r = client.get(f"/sales_official/areas/{area_code}", params={**BASE, **params})
    assert r.status_code == 200
    assert_is_paged_response(r.json())


def test_sales_official_area_invalid_new_build_422(client):
    area_code = get_any_area_code(client)
    r = client.get(f"/sales_official/areas/{area_code}", params={**BASE, "new_build": "1"})
    assert r.status_code == 422


def test_sales_official_area_negative_min_price_422(client):
    area_code = get_any_area_code(client)
    r = client.get(f"/sales_official/areas/{area_code}", params={**BASE, "min_price": -1})
    assert r.status_code == 422