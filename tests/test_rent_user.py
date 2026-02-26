import pytest


def assert_status(r, code: int):
    assert r.status_code == code, f"Expected {code}, got {r.status_code}, body={r.text}"

def assert_error_has_detail(r):
    data = r.json()
    assert "detail" in data

def _get_valid_postcode_and_area_code(client):
    r = client.get("/postcode_map", params={"limit": 1})
    assert_status(r, 200)
    items = r.json()
    assert isinstance(items, list) and len(items) >= 1, "postcode_map is empty, cannot test rent_user."
    return items[0]["postcode"], items[0]["area_code"]

def _create_rent_user_record(client, payload: dict):
    r = client.post("/rent_user", json=payload)
    assert_status(r, 201)
    data = r.json()
    assert "id" in data and isinstance(data["id"], int)
    assert "created_at" in data
    return data

def _delete_rent_user_record(client, record_id: int):
    r = client.delete(f"/rent_user/{record_id}")
    assert_status(r, 204)

@pytest.fixture
def rent_user_seed(client):

    postcode, area_code = _get_valid_postcode_and_area_code(client)

    tp1 = "2024-06"
    tp2 = "2024-07"

    rec1 = _create_rent_user_record(client, {
        "postcode": postcode,
        "area_code": area_code,
        "time_period": tp1,
        "rent": 950,
        "bedrooms": 1,
        "property_type": "flat",
        "source": "user"
    })

    rec2 = _create_rent_user_record(client, {
        "postcode": postcode,
        "area_code": area_code,
        "time_period": tp2,
        "rent": 1200,
        "bedrooms": 2,
        "property_type": "terraced",
        "source": "survey"
    })

    yield {"postcode": postcode, "area_code": area_code, "rec1": rec1, "rec2": rec2}

    for rec in [rec1, rec2]:
        rid = rec["id"]
        r = client.delete(f"/rent_user/{rid}")
        if r.status_code not in (204, 404):
            pytest.fail(f"Cleanup failed for id={rid}: {r.status_code}, {r.text}")


def test_rent_user_create_201_and_get_by_id(client):
    postcode, area_code = _get_valid_postcode_and_area_code(client)

    created = _create_rent_user_record(client, {
        "postcode": postcode,
        "area_code": area_code,
        "time_period": "2024-07",
        "rent": 999,
        "bedrooms": 2,
        "property_type": "flat",
        "source": "partner"
    })

    rid = created["id"]

    r_get = client.get(f"/rent_user/{rid}")
    assert_status(r_get, 200)
    got = r_get.json()
    assert got["id"] == rid
    assert got["postcode"]
    assert got["time_period"] == "2024-07"
    assert got["rent"] == 999

    _delete_rent_user_record(client, rid)


def test_rent_user_list_basic(client, rent_user_seed):
    r = client.get("/rent_user")
    assert_status(r, 200)
    data = r.json()
    assert "items" in data and isinstance(data["items"], list)


def test_rent_user_put_replaces_fields(client, rent_user_seed):
    rid = rent_user_seed["rec1"]["id"]

    r_put = client.put(f"/rent_user/{rid}", json={
        "postcode": rent_user_seed["postcode"],
        "area_code": rent_user_seed["area_code"],
        "time_period": "2024-09",
        "rent": 1500,
        "bedrooms": 3,
        "property_type": "detached",
        "source": "user"
    })
    assert_status(r_put, 200)
    updated = r_put.json()
    assert updated["id"] == rid
    assert updated["time_period"] == "2024-09"
    assert updated["rent"] == 1500
    assert updated["bedrooms"] == 3
    assert updated["property_type"] == "detached"


def test_rent_user_patch_partial_update(client, rent_user_seed):
    rid = rent_user_seed["rec2"]["id"]

    r_patch = client.patch(f"/rent_user/{rid}", json={"rent": 1300})
    assert_status(r_patch, 200)
    patched = r_patch.json()
    assert patched["id"] == rid
    assert patched["rent"] == 1300


def test_rent_user_delete_then(client):
    postcode, area_code = _get_valid_postcode_and_area_code(client)

    created = _create_rent_user_record(client, {
        "postcode": postcode,
        "area_code": area_code,
        "time_period": "2024-07",
        "rent": 888
    })
    rid = created["id"]

    _delete_rent_user_record(client, rid)

    r_get = client.get(f"/rent_user/{rid}")
    assert_status(r_get, 404)
    assert_error_has_detail(r_get)



def test_rent_user_filter_by_time_period(client, rent_user_seed):
    tp = rent_user_seed["rec1"]["time_period"]
    r = client.get("/rent_user", params={"time_period": tp})
    assert_status(r, 200)
    items = r.json()["items"]
    assert all(it["time_period"] == tp for it in items)


def test_rent_user_filter_by_area_code(client, rent_user_seed):
    ac = rent_user_seed["area_code"]
    r = client.get("/rent_user", params={"area_code": ac})
    assert_status(r, 200)
    items = r.json()["items"]
    assert all(it.get("area_code") == ac for it in items)


def test_rent_user_filter_by_postcode(client, rent_user_seed):
    pc = rent_user_seed["postcode"]
    r = client.get("/rent_user", params={"postcode": pc})
    assert_status(r, 200)
    items = r.json()["items"]
    assert all(it["postcode"] == pc for it in items)


def test_rent_user_filter_by_bedrooms_and_property_type(client, rent_user_seed):
    r = client.get("/rent_user", params={"bedrooms": 2, "property_type": "terraced"})
    assert_status(r, 200)
    items = r.json()["items"]
    for it in items:
        assert it.get("bedrooms") == 2
        assert it.get("property_type") == "terraced"


def test_rent_user_pagination_limit_offset(client, rent_user_seed):
    r1 = client.get("/rent_user", params={"limit": 1, "offset": 0})
    assert_status(r1, 200)
    items1 = r1.json()["items"]
    assert len(items1) <= 1

    r2 = client.get("/rent_user", params={"limit": 1, "offset": 1})
    assert_status(r2, 200)
    items2 = r2.json()["items"]
    assert len(items2) <= 1


def test_rent_user_get_unknown_id(client):
    r = client.get("/rent_user/999999999")
    assert_status(r, 404)
    assert_error_has_detail(r)


def test_rent_user_put_unknown_id(client):
    postcode, area_code = _get_valid_postcode_and_area_code(client)
    r = client.put("/rent_user/999999999", json={
        "postcode": postcode,
        "area_code": area_code,
        "time_period": "2024-07",
        "rent": 1000
    })
    assert_status(r, 404)
    assert_error_has_detail(r)


def test_rent_user_patch_unknown_id(client):
    r = client.patch("/rent_user/999999999", json={"rent": 1234})
    assert_status(r, 404)
    assert_error_has_detail(r)


def test_rent_user_delete_unknown_id(client):
    r = client.delete("/rent_user/999999999")
    assert_status(r, 404)
    assert_error_has_detail(r)


def test_rent_user_create_rent_must_be_positive(client):
    postcode, area_code = _get_valid_postcode_and_area_code(client)
    r = client.post("/rent_user", json={
        "postcode": postcode,
        "area_code": area_code,
        "time_period": "2024-07",
        "rent": 0
    })
    assert_status(r, 422)


def test_rent_user_create_postcode_too_short(client):
    r = client.post("/rent_user", json={
        "postcode": "L",        # minLength=2
        "time_period": "2024-07",
        "rent": 900
    })
    assert_status(r, 422)


def test_rent_user_create_bedrooms_too_large(client):
    postcode, area_code = _get_valid_postcode_and_area_code(client)
    r = client.post("/rent_user", json={
        "postcode": postcode,
        "area_code": area_code,
        "time_period": "2024-07",
        "rent": 900,
        "bedrooms": 11           # max=10
    })
    assert_status(r, 422)


def test_rent_user_create_invalid_property_type_(client):
    postcode, area_code = _get_valid_postcode_and_area_code(client)
    r = client.post("/rent_user", json={
        "postcode": postcode,
        "area_code": area_code,
        "time_period": "2024-07",
        "rent": 900,
        "property_type": "castle"
    })
    assert_status(r, 422)


def test_rent_user_patch_invalid_source(client, rent_user_seed):
    rid = rent_user_seed["rec1"]["id"]
    r = client.patch(f"/rent_user/{rid}", json={"source": "twitter"})
    assert_status(r, 422)