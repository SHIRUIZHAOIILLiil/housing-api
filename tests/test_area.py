# tests/test_areas.py

def test_list_areas_default(client):
    r = client.get("/areas")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 3

    assert "area_code" in data[0]
    assert "area_name" in data[0]


def test_list_areas_with_q_fuzzy(client):
    # q=lee should be able to find Leeds
    # (depending on the like/fuzzy logic implemented in the code).
    r = client.get("/areas", params={"q": "lee"})
    assert r.status_code == 200
    data = r.json()
    assert any(x["area_name"].lower() == "leeds" for x in data)


def test_list_areas_limit_validation(client):
    # In OpenAPI, `limit <= 200` and `>200` should be 422.
    r = client.get("/areas", params={"limit": 1000})
    assert r.status_code == 422


def test_get_area_success(client):
    r = client.get("/areas/E08000035")
    assert r.status_code == 200
    data = r.json()
    assert data["area_code"] == "E08000035"
    assert data["area_name"] == "Leeds"


def test_get_area_not_found(client):
    r = client.get("/areas/NOTEXIST")
    # The OpenAPI defines a 404 (ErrorOut) response.
    assert r.status_code == 404
    err = r.json()
    assert "detail" in err


def test_get_area_postcodes_success(client):
    r = client.get("/areas/E08000035/postcodes", params={"limit": 50})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2

    # PostcodeOut: postcode, area_code, area_name
    assert data[0]["area_code"] == "E08000035"
    assert data[0]["area_name"] == "Leeds"
    assert "postcode" in data[0]


def test_get_area_postcodes_not_found(client):
    r = client.get("/areas/NOTEXIST/postcodes")
    assert r.status_code == 404
    err = r.json()
    assert "detail" in err