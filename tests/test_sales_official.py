import pytest
import uuid

BASE = {
    "limit": 20,
    "offset": 0,
}

def assert_is_paged_response(payload: dict):
    assert isinstance(payload, dict)
    assert "items" in payload
    assert "meta" in payload
    assert isinstance(payload["items"], list)
    assert "limit" in payload["meta"]
    assert "offset" in payload["meta"]
    assert "count" in payload["meta"]
    assert payload["meta"]["count"] == len(payload["items"])

# Basic OK / shape
def test_sales_official_default_ok(client):
    r = client.get("/sales_official", params=BASE)
    assert r.status_code == 200
    assert_is_paged_response(r.json())

def test_sales_official_pagination_ok(client):
    r1 = client.get("/sales_official", params={**BASE, "limit": 2, "offset": 0})
    r2 = client.get("/sales_official", params={**BASE, "limit": 2, "offset": 2})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert_is_paged_response(r1.json())
    assert_is_paged_response(r2.json())


def test_sales_official_filter_by_uuid_prefix_returns_that_item(client):
    r0 = client.get("/sales_official", params={"limit": 1, "offset": 0})
    assert r0.status_code == 200
    item = r0.json()["items"][0]
    prefix = item["transaction_uuid"][:4]

    r = client.get("/sales_official", params={"uuid_prefix": prefix, "limit": 50, "offset": 0})
    assert r.status_code == 200
    uuids = [x["transaction_uuid"] for x in r.json()["items"]]
    assert item["transaction_uuid"] in uuids


def test_sales_official_include_total_sets_total(client):
    r = client.get("/sales_official", params={"include_total": True, "limit": 2, "offset": 0})
    assert r.status_code == 200
    meta = r.json()["meta"]
    assert "total" in meta
    assert meta["total"] is None or isinstance(meta["total"], int)


# Sorting smoke
@pytest.mark.parametrize("sort_by, order", [
    ("transaction_date", "desc"),
    ("transaction_date", "asc"),
    ("price", "desc"),
    ("price", "asc"),
])
def test_sales_official_sorting_smoke(client, sort_by, order):
    r = client.get("/sales_official", params={**BASE, "sort_by": sort_by, "order": order})
    assert r.status_code == 200
    assert_is_paged_response(r.json())


# Single-filter smoke (clean)
@pytest.mark.parametrize("params", [
    {"property_type": "S"},
    {"property_type": "T"},
    {"property_type": "F"},

    {"tenure": "F"},
    {"tenure": "L"},

    # IMPORTANT: your API validates this as Literal['Y','N']
    {"new_build": "Y"},
    {"new_build": "N"},

    {"date_from": "2020-01-01", "date_to": "2020-12-31"},
    {"min_price": 100000, "max_price": 300000},

    # fuzzy postcode sample (doesn't need to match, just shouldn't error)
    {"postcode_like": "LS"},
])
def test_sales_official_single_filters_smoke(client, params):
    r = client.get("/sales_official", params={**BASE, **params})
    assert r.status_code == 200
    assert_is_paged_response(r.json())


# Validation errors (should be 422 in FastAPI by default)

def test_sales_official_uuid_prefix_too_short_422(client):
    r = client.get("/sales_official", params={**BASE, "uuid_prefix": "abc"})  # minLength=4
    assert r.status_code == 422

def test_sales_official_negative_min_price_422(client):
    r = client.get("/sales_official", params={**BASE, "min_price": -1})
    assert r.status_code == 422

def test_sales_official_date_range_invalid(client):
    r = client.get("/sales_official", params={"date_from": "2020-12-31", "date_to": "2020-01-01"})
    assert r.status_code == 400

def test_sales_official_price_range_invalid(client):
    r = client.get("/sales_official", params={"min_price": 300000, "max_price": 100000})
    assert r.status_code == 400


def test_sales_official_get_by_uuid_ok(client):
    # Let's start with a piece of real data.
    r0 = client.get("/sales_official", params={"limit": 1, "offset": 0})
    assert r0.status_code == 200
    items = r0.json()["items"]
    assert len(items) > 0

    sample = items[0]
    txid = sample["transaction_uuid"]

    # Use this UUID to check details
    r = client.get(f"/sales_official/transactions/{txid}")
    assert r.status_code == 200

    data = r.json()
    assert data["transaction_uuid"] == txid
    assert "price" in data
    assert "transaction_date" in data
    assert "postcode" in data


def test_sales_official_get_by_uuid_not_found(client):
    # Construct a UUID that definitely does not exist.
    fake_uuid = str(uuid.uuid4())

    r = client.get(f"/sales_official/{fake_uuid}")
    assert r.status_code == 404
