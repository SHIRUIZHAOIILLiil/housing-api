
def test_list_postcode_map_default(client):
    r = client.get("/postcode_map")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 4

    assert "postcode" in data[0]
    assert "area_code" in data[0]
    assert "area_name" in data[0]

def test_list_postcode_with_q_fuzzy(client):
    # q=al13 should be able to find St Albans
    # (depending on the like/fuzzy logic implemented in the code).
    r = client.get("/postcode_map", params={"q": "al13"}) # Find AL1 3BH in St Albans
    assert r.status_code == 200
    data = r.json()
    assert any(x["area_name"].lower() == "st albans" for x in data)

def test_list_areas_limit_validation_maximum(client):
    # In OpenAPI, `limit <= 200` and `>200` should be 422.
    r = client.get("/postcode_map", params={"limit": 1000})
    assert r.status_code == 422

def test_list_areas_limit_validation_minimum(client):
    # In OpenAPI, `limit <= 200` and `>200` should be 422.
    r = client.get("/areas", params={"limit": 0})
    assert r.status_code == 422

def test_get_area_success(client):
    r = client.get("/postcode_map/al13bh")
    assert r.status_code == 200
    data = r.json()
    assert data["area_code"] == "E07000240"
    assert data["area_name"] == "St Albans"

def test_get_area_fail(client):
    r = client.get("/postcode_map/al13bh2")
    assert r.status_code == 404
    err = r.json()
    assert "detail" in err
