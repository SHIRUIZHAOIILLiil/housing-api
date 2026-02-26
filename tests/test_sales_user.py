import pytest
def assert_status(r, code: int):
    assert r.status_code == code, f"Expected {code}, got {r.status_code}, body={r.text}"


def assert_error_has_detail(r):
    data = r.json()
    assert "detail" in data


def get_valid_postcode_and_area_code(client):
    """
    Fetch one valid postcode + area_code from postcode_map to avoid hardcoding test data.
    """
    r = client.get("/postcode_map", params={"limit": 1})
    assert_status(r, 200)
    items = r.json()
    assert isinstance(items, list) and items, "postcode_map is empty; cannot run user sales tests."
    return items[0]["postcode"], items[0]["area_code"]


def create_user_sale(client, payload: dict):
    r = client.post("/user-sales-transactions", json=payload)
    assert_status(r, 201)
    data = r.json()
    assert "id" in data and isinstance(data["id"], int)
    assert "created_at" in data
    return data


def delete_user_sale(client, record_id: int):
    r = client.delete(f"/user-sales-transactions/{record_id}")
    assert_status(r, 204)


@pytest.fixture
def sales_user_seed(client):
    """
    Create a couple of user sales transactions for filtering/pagination tests and clean them up afterwards.
    """
    postcode, area_code = get_valid_postcode_and_area_code(client)

    rec1 = create_user_sale(client, {
        "postcode": postcode,
        "area_code": area_code,
        "time_period": "2024-07",
        "price": 250000,
        "property_type": "flat",
        "source": "user"
    })

    rec2 = create_user_sale(client, {
        "postcode": postcode,
        "area_code": area_code,
        "time_period": "2024-08",
        "price": 315000,
        "property_type": "semidetached",
        "source": "partner"
    })

    yield {
        "postcode": postcode,
        "area_code": area_code,
        "rec1": rec1,
        "rec2": rec2,
    }

    for rec in (rec1, rec2):
        rid = rec["id"]
        r = client.delete(f"/user-sales-transactions/{rid}")
        if r.status_code not in (204, 404):
            pytest.fail(f"Cleanup failed for id={rid}: {r.status_code}, {r.text}")


def test_sales_user_create_and_get_by_id(client):
    postcode, area_code = get_valid_postcode_and_area_code(client)

    created = create_user_sale(client, {
        "postcode": postcode,
        "area_code": area_code,
        "time_period": "2024-07",
        "price": 275000,
        "property_type": "terraced",
        "source": "survey"
    })

    rid = created["id"]

    r_get = client.get(f"/user-sales-transactions/{rid}")
    assert_status(r_get, 200)
    got = r_get.json()
    assert got["id"] == rid
    assert got["postcode"] == postcode
    assert got["time_period"] == "2024-07"
    assert got["price"] == 275000

    delete_user_sale(client, rid)


def test_sales_user_create_without_area_code_allows_derivation(client):
    """
    area_code is optional in the schema; service may derive it from postcode_map.
    """
    postcode, _ = get_valid_postcode_and_area_code(client)

    created = create_user_sale(client, {
        "postcode": postcode,
        "time_period": "2024-07",
        "price": 300000,
        "property_type": "other"
    })

    assert created["postcode"] == postcode
    assert created["price"] == 300000

    delete_user_sale(client, created["id"])


def test_sales_user_list_basic(client, sales_user_seed):
    r = client.get("/user-sales-transactions")
    assert_status(r, 200)
    data = r.json()
    assert "items" in data and isinstance(data["items"], list)


def test_sales_user_put_replaces_fields(client, sales_user_seed):
    rid = sales_user_seed["rec1"]["id"]
    postcode = sales_user_seed["postcode"]
    area_code = sales_user_seed["area_code"]

    r_put = client.put(f"/user-sales-transactions/{rid}", json={
        "postcode": postcode,
        "area_code": area_code,
        "time_period": "2024-09",
        "price": 410000,
        "property_type": "detached",
        "source": "user"
    })
    assert_status(r_put, 200)
    updated = r_put.json()
    assert updated["id"] == rid
    assert updated["time_period"] == "2024-09"
    assert updated["price"] == 410000
    assert updated["property_type"] == "detached"


def test_sales_user_patch_partial_update(client, sales_user_seed):
    rid = sales_user_seed["rec2"]["id"]

    r_patch = client.patch(f"/user-sales-transactions/{rid}", json={"price": 320000})
    assert_status(r_patch, 200)
    patched = r_patch.json()
    assert patched["id"] == rid
    assert patched["price"] == 320000


def test_sales_user_delete_then_get_not_found(client):
    postcode, area_code = get_valid_postcode_and_area_code(client)

    created = create_user_sale(client, {
        "postcode": postcode,
        "area_code": area_code,
        "time_period": "2024-07",
        "price": 260000
    })

    rid = created["id"]
    delete_user_sale(client, rid)

    r_get = client.get(f"/user-sales-transactions/{rid}")
    assert_status(r_get, 404)
    assert_error_has_detail(r_get)


def test_sales_user_filters_by_postcode(client, sales_user_seed):
    pc = sales_user_seed["postcode"]
    r = client.get("/user-sales-transactions", params={"postcode": pc})
    assert_status(r, 200)
    items = r.json()["items"]
    assert all(it["postcode"] == pc for it in items)


def test_sales_user_filters_by_area_code(client, sales_user_seed):
    ac = sales_user_seed["area_code"]
    r = client.get("/user-sales-transactions", params={"area_code": ac})
    assert_status(r, 200)
    items = r.json()["items"]
    assert all(it.get("area_code") == ac for it in items)


def test_sales_user_filters_by_property_type(client, sales_user_seed):
    r = client.get("/user-sales-transactions", params={"property_type": "semidetached"})
    assert_status(r, 200)
    items = r.json()["items"]
    for it in items:
        assert it.get("property_type") == "semidetached"


def test_sales_user_filters_by_price_range(client, sales_user_seed):
    r = client.get("/user-sales-transactions", params={"min_price": 300000, "max_price": 330000})
    assert_status(r, 200)
    items = r.json()["items"]
    for it in items:
        assert it["price"] >= 300000
        assert it["price"] <= 330000


def test_sales_user_filters_by_period_range(client, sales_user_seed):
    """
    Filters use from_period / to_period; exact semantics depend on implementation
    (usually inclusive bounds on YYYY-MM).
    """
    r = client.get("/user-sales-transactions", params={"from_period": "2024-08", "to_period": "2024-08"})
    assert_status(r, 200)
    items = r.json()["items"]
    for it in items:
        assert it["time_period"] == "2024-08"


def test_sales_user_pagination_limit_offset(client, sales_user_seed):
    r1 = client.get("/user-sales-transactions", params={"limit": 1, "offset": 0})
    assert_status(r1, 200)
    items1 = r1.json()["items"]
    assert len(items1) <= 1

    r2 = client.get("/user-sales-transactions", params={"limit": 1, "offset": 1})
    assert_status(r2, 200)
    items2 = r2.json()["items"]
    assert len(items2) <= 1


def test_sales_user_unknown_id_not_found(client):
    r = client.get("/user-sales-transactions/999999999")
    assert_status(r, 404)
    assert_error_has_detail(r)


def test_sales_user_validation_price_must_be_positive(client):
    postcode, area_code = get_valid_postcode_and_area_code(client)
    r = client.post("/user-sales-transactions", json={
        "postcode": postcode,
        "area_code": area_code,
        "time_period": "2024-07",
        "price": 0
    })
    assert_status(r, 422)


def test_sales_user_validation_postcode_too_short(client):
    r = client.post("/user-sales-transactions", json={
        "postcode": "L",
        "time_period": "2024-07",
        "price": 250000
    })
    assert_status(r, 422)


def test_sales_user_validation_invalid_property_type(client):
    postcode, area_code = get_valid_postcode_and_area_code(client)
    r = client.post("/user-sales-transactions", json={
        "postcode": postcode,
        "area_code": area_code,
        "time_period": "2024-07",
        "price": 250000,
        "property_type": "castle"
    })
    assert_status(r, 422)


def test_sales_user_validation_invalid_source(client):
    postcode, area_code = get_valid_postcode_and_area_code(client)
    r = client.post("/user-sales-transactions", json={
        "postcode": postcode,
        "area_code": area_code,
        "time_period": "2024-07",
        "price": 250000,
        "source": "twitter"
    })
    assert_status(r, 422)


def test_sales_user_patch_validation_invalid_price(client, sales_user_seed):
    rid = sales_user_seed["rec1"]["id"]
    r = client.patch(f"/user-sales-transactions/{rid}", json={"price": 0})
    assert_status(r, 422)


def test_sales_user_delete_unknown_id_not_found(client):
    r = client.delete("/user-sales-transactions/999999999")
    assert_status(r, 404)
    assert_error_has_detail(r)