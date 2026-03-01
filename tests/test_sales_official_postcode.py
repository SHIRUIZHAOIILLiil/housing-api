# tests/test_sales_official_postcodes.py
import re
from datetime import date

import pytest


# helpers
def _norm_postcode(s: str) -> str:
    """Normalize postcodes for comparison: uppercase + remove spaces."""
    return re.sub(r"\s+", "", s or "").upper()

def _get_any_official_sales_postcode(client) -> str:
    """
    Find a postcode that definitely exists in official sales data
    by calling the list endpoint and taking the first item.
    """
    r = client.get("/sales_official", params={"limit": 1, "offset": 0})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "items" in data and isinstance(data["items"], list) and len(data["items"]) >= 1
    pc = data["items"][0]["postcode"]
    assert pc
    return pc

def _assert_paged_response_shape(payload: dict):
    assert isinstance(payload, dict)
    assert "items" in payload and isinstance(payload["items"], list)
    assert "meta" in payload and isinstance(payload["meta"], dict)
    meta = payload["meta"]
    assert set(["limit", "offset", "count"]).issubset(meta.keys())
    assert isinstance(meta["limit"], int)
    assert isinstance(meta["offset"], int)
    assert isinstance(meta["count"], int)
    # total is optional (present when include_total=true)
    if "total" in meta:
        assert (meta["total"] is None) or isinstance(meta["total"], int)


def _assert_official_txn_shape(item: dict):
    # Based on OfficialSalesTransactionOut schema in openapi :contentReference[oaicite:1]{index=1}
    assert "transaction_uuid" in item and isinstance(item["transaction_uuid"], str)
    assert "price" in item and (isinstance(item["price"], int) or isinstance(item["price"], float))
    assert "transaction_date" in item and isinstance(item["transaction_date"], str)
    assert "postcode" in item and isinstance(item["postcode"], str)

    # Optional fields
    if "property_type" in item and item["property_type"] is not None:
        assert item["property_type"] in ("D", "S", "T", "F", "O")
    if "new_build" in item and item["new_build"] is not None:
        assert item["new_build"] in (1, 0)
    if "tenure" in item and item["tenure"] is not None:
        assert item["tenure"] in ("F", "L", "U")


def _assert_error_out(resp):
    # Try to be compatible with your existing helper.
    try:
        payload = resp.json()
    except Exception:
        pytest.fail(f"Expected JSON error body but got: {resp.text}")
    assert isinstance(payload, dict)
    # ErrorOut is {"detail": "..."} in openapi :contentReference[oaicite:2]{index=2}
    assert "detail" in payload and isinstance(payload["detail"], str)


# tests: happy path
def test_sales_official_postcodes_happy_path(client):
    postcode = _get_any_official_sales_postcode(client)

    r = client.get(f"/sales_official/postcodes/{postcode}")
    assert r.status_code == 200, r.text
    payload = r.json()
    _assert_paged_response_shape(payload)

    # all items match postcode (ignoring spaces/case)
    for it in payload["items"]:
        _assert_official_txn_shape(it)
        assert _norm_postcode(it["postcode"]) == _norm_postcode(postcode)


def test_sales_official_postcodes_accepts_spaced_or_lowercase_postcode(client):
    postcode = _get_any_official_sales_postcode(client)

    # Create a "messy" variant: lowercased + add a space before last 3 chars if long enough
    pc = _norm_postcode(postcode)
    if len(pc) > 3:
        messy = (pc[:-3] + " " + pc[-3:]).lower()
    else:
        messy = pc.lower()

    r = client.get(f"/sales_official/postcodes/{messy}")
    assert r.status_code == 200, r.text
    payload = r.json()
    _assert_paged_response_shape(payload)
    for it in payload["items"]:
        assert _norm_postcode(it["postcode"]) == _norm_postcode(messy)


def test_sales_official_postcodes_include_total_true(client):
    postcode = _get_any_official_sales_postcode(client)

    r = client.get(f"/sales_official/postcodes/{postcode}", params={"include_total": True})
    assert r.status_code == 200, r.text
    payload = r.json()
    _assert_paged_response_shape(payload)
    assert "total" in payload["meta"]
    assert isinstance(payload["meta"]["total"], int)
    assert payload["meta"]["total"] >= payload["meta"]["count"]


def test_sales_official_postcodes_pagination_limit_offset(client):
    postcode = _get_any_official_sales_postcode(client)

    r1 = client.get(f"/sales_official/postcodes/{postcode}", params={"limit": 1, "offset": 0, "include_total": True})
    assert r1.status_code == 200, r1.text
    p1 = r1.json()
    _assert_paged_response_shape(p1)
    assert p1["meta"]["limit"] == 1
    assert p1["meta"]["offset"] == 0
    assert p1["meta"]["count"] in (0, 1)

    # if there are 2+ rows, offset 1 should give different UUID
    if p1["meta"]["total"] and p1["meta"]["total"] >= 2:
        r2 = client.get(f"/sales_official/postcodes/{postcode}", params={"limit": 1, "offset": 1})
        assert r2.status_code == 200, r2.text
        p2 = r2.json()
        _assert_paged_response_shape(p2)
        assert p2["meta"]["limit"] == 1
        assert p2["meta"]["offset"] == 1
        assert len(p2["items"]) == 1
        assert p2["items"][0]["transaction_uuid"] != p1["items"][0]["transaction_uuid"]


# tests: filtering
def test_sales_official_postcodes_filter_by_date_range(client):
    postcode = _get_any_official_sales_postcode(client)

    # First get a sample item to derive a valid date window.
    base = client.get(f"/sales_official/postcodes/{postcode}", params={"limit": 1})
    assert base.status_code == 200, base.text
    it = base.json()["items"][0]
    d = date.fromisoformat(it["transaction_date"])

    # window that includes the exact date (should return >=1)
    r_ok = client.get(
        f"/sales_official/postcodes/{postcode}",
        params={"date_from": d.isoformat(), "date_to": d.isoformat()},
    )
    assert r_ok.status_code == 200, r_ok.text
    assert r_ok.json()["meta"]["count"] >= 1

    # window that excludes the date (should be empty OR 404 depending on your design)
    r_empty = client.get(
        f"/sales_official/postcodes/{postcode}",
        params={"date_from": "1900-01-01", "date_to": "1900-01-02"},
    )

    assert r_empty.status_code in (200, 404), r_empty.text
    if r_empty.status_code == 200:
        assert r_empty.json()["meta"]["count"] == 0


def test_sales_official_postcodes_filter_by_min_max_price(client):
    postcode = _get_any_official_sales_postcode(client)
    r_all = client.get(f"/sales_official/postcodes/{postcode}", params={"include_total": True})
    assert r_all.status_code == 200, r_all.text
    items = r_all.json()["items"]
    if not items:
        pytest.skip("No items for this postcode; cannot test price filtering")

    prices = [it["price"] for it in items]
    pmin, pmax = min(prices), max(prices)

    r = client.get(f"/sales_official/postcodes/{postcode}", params={"min_price": pmin, "max_price": pmax})
    assert r.status_code == 200, r.text
    for it in r.json()["items"]:
        assert it["price"] >= pmin and it["price"] <= pmax

    # narrow filter likely returns <= all
    mid = (pmin + pmax) / 2
    r2 = client.get(f"/sales_official/postcodes/{postcode}", params={"min_price": mid})
    assert r2.status_code == 200, r2.text
    for it in r2.json()["items"]:
        assert it["price"] >= mid


@pytest.mark.parametrize("sort_by,order", [("transaction_date", "asc"), ("transaction_date", "desc"), ("price", "asc"), ("price", "desc")])
def test_sales_official_postcodes_sorting(client, sort_by, order):
    postcode = _get_any_official_sales_postcode(client)

    r = client.get(f"/sales_official/postcodes/{postcode}", params={"sort_by": sort_by, "order": order, "limit": 50})
    assert r.status_code == 200, r.text
    items = r.json()["items"]

    if len(items) < 2:
        return

    if sort_by == "transaction_date":
        vals = [date.fromisoformat(it["transaction_date"]) for it in items]
    else:
        vals = [it["price"] for it in items]

    sorted_vals = sorted(vals, reverse=(order == "desc"))
    assert vals == sorted_vals


#tests: validation / errors (422, 404, 400)
def test_sales_official_postcodes_invalid_date_format(client):
    postcode = _get_any_official_sales_postcode(client)
    r = client.get(f"/sales_official/postcodes/{postcode}", params={"date_from": "2020-13-01"})
    assert r.status_code == 422, r.text


def test_sales_official_postcodes_invalid_date_range(client):
    postcode = _get_any_official_sales_postcode(client)
    r = client.get(f"/sales_official/postcodes/{postcode}", params={"date_from": "2020-12-31", "date_to": "2020-01-01"})
    assert r.status_code == 400, r.text


def test_sales_official_postcodes_invalid_property_type(client):
    postcode = _get_any_official_sales_postcode(client)
    r = client.get(f"/sales_official/postcodes/{postcode}", params={"property_type": "X"})
    assert r.status_code == 422, r.text


def test_sales_official_postcodes_invalid_new_build(client):
    postcode = _get_any_official_sales_postcode(client)
    r = client.get(f"/sales_official/postcodes/{postcode}", params={"new_build": "maybe"})
    assert r.status_code == 422, r.text


def test_sales_official_postcodes_invalid_tenure(client):
    postcode = _get_any_official_sales_postcode(client)
    r = client.get(f"/sales_official/postcodes/{postcode}", params={"tenure": "Z"})
    assert r.status_code == 422, r.text


def test_sales_official_postcodes_limit_offset_validation(client):
    postcode = _get_any_official_sales_postcode(client)

    r1 = client.get(f"/sales_official/postcodes/{postcode}", params={"limit": 0})
    assert r1.status_code == 422, r1.text

    r2 = client.get(f"/sales_official/postcodes/{postcode}", params={"limit": 201})
    assert r2.status_code == 422, r2.text

    r3 = client.get(f"/sales_official/postcodes/{postcode}", params={"offset": -1})
    assert r3.status_code == 422, r3.text


def test_sales_official_postcodes_unknown_postcode(client):
    # choose something extremely unlikely; your service may normalize/strip spaces
    unknown = "ZZ99ZZZ"
    r = client.get(f"/sales_official/postcodes/{unknown}")

    # OpenAPI includes 404 for this route :contentReference[oaicite:3]{index=3}
    assert r.status_code == 404, r.text
    _assert_error_out(r)