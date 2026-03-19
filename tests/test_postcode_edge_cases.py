from app.services.service_postcode_map import get_postcode_map_by_area_code


def test_get_postcode_map_rejects_invalid_format(client):
    resp = client.get("/postcode_map/AB12")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid postcode format"


def test_get_postcode_map_normalizes_spacing_and_case(client):
    resp = client.get("/postcode_map/al1 3bh")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["postcode"] == "AL13BH"
    assert data["area_code"] == "E07000240"


def test_postcode_fuzzy_query_rejects_blank_q(client):
    resp = client.get("/postcode_map", params={"q": "   "})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "q cannot be empty"


def test_postcode_fuzzy_query_normalizes_spaces(client):
    resp = client.get("/postcode_map", params={"q": " al1 3 "})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert any(item["postcode"] == "AL13BH" for item in data)


def test_get_postcode_map_by_area_code_rejects_blank_area_code(db_conn):
    try:
        get_postcode_map_by_area_code(db_conn, "   ", 10)
    except Exception as exc:
        assert str(exc) == "area_code cannot be empty"
    else:
        raise AssertionError("Expected blank area_code to raise an error.")
