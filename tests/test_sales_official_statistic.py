import re
import pytest


YYYY_MM_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def assert_error_out(resp):
    data = resp.json()
    assert isinstance(data, dict)
    assert "detail" in data and isinstance(data["detail"], str)


def assert_sales_stats_out(obj: dict):
    # SalesStatsOut required: area_code, time_period, count
    assert isinstance(obj, dict)
    assert isinstance(obj.get("area_code"), str) and obj["area_code"]
    assert isinstance(obj.get("time_period"), str) and obj["time_period"]
    assert isinstance(obj.get("count"), int) and obj["count"] >= 0

    # Optional numeric fields
    for k in ("avg_price", "min_price", "max_price", "total_value"):
        if k in obj and obj[k] is not None:
            assert isinstance(obj[k], (int, float))
            assert obj[k] >= 0

    # Optional filters echoed back
    if obj.get("property_type") is not None:
        assert obj["property_type"] in ("D", "S", "T", "F", "O")
    if obj.get("new_build") is not None:
        assert obj["new_build"] in ("Y", "N")
    if obj.get("tenure") is not None:
        assert obj["tenure"] in ("F", "L", "U")


def assert_sales_stats_series_out(obj: dict):
    assert isinstance(obj, dict)
    assert isinstance(obj.get("area_code"), str) and obj["area_code"]
    assert "items" in obj and isinstance(obj["items"], list)

    for it in obj["items"]:
        assert isinstance(it.get("time_period"), str) and it["time_period"]
        assert isinstance(it.get("count"), int) and it["count"] >= 0
        for k in ("avg_price", "min_price", "max_price", "total_value"):
            if k in it and it[k] is not None:
                assert isinstance(it[k], (int, float))
                assert it[k] >= 0


def find_area_with_sales_stats(client):
    """
    Find an area_code such that /sales_official/areas/{area_code}/sales-stats/availability
    returns months>0 and min/max are not null.
    """
    r = client.get("/areas", params={"limit": 200})
    assert r.status_code == 200, r.text
    areas = r.json()
    assert isinstance(areas, list) and areas, "No areas returned from /areas"

    for a in areas:
        area_code = a.get("area_code")
        if not area_code:
            continue
        av = client.get(f"/sales_official/areas/{area_code}/sales-stats/availability")
        if av.status_code != 200:
            continue
        avj = av.json()
        months = avj.get("months", 0)
        if months and avj.get("min_time_period") and avj.get("max_time_period"):
            return area_code, avj

    pytest.skip("No area found with available official sales stats (months>0).")


def month_in_range(x: str, lo: str, hi: str) -> bool:
    # YYYY-MM string compare works lexicographically
    return lo <= x <= hi


# tests: availability
def test_sales_official_sales_stats_availability_happy_path(client):
    area_code, av = find_area_with_sales_stats(client)

    assert av["area_code"] == area_code
    assert isinstance(av["months"], int) and av["months"] > 0
    assert isinstance(av["min_time_period"], str) and YYYY_MM_RE.match(av["min_time_period"])
    assert isinstance(av["max_time_period"], str) and YYYY_MM_RE.match(av["max_time_period"])
    assert av["min_time_period"] <= av["max_time_period"]


def test_sales_official_sales_stats_availability_unknown_area(client):
    r = client.get("/sales_official/areas/ZZZ999/sales-stats/availability")
    assert r.status_code == 404, r.text
    assert_error_out(r)


def test_sales_official_sales_stats_availability_empty_area(client):
    r = client.get("/sales_official/areas//sales-stats/availability")
    assert r.status_code in (404, 422), r.text


# tests: point
def test_sales_official_sales_stats_point_happy_path(client):
    area_code, av = find_area_with_sales_stats(client)
    tp = av["min_time_period"]

    r = client.get("/sales_official/sales-stats", params={"area_code": area_code, "time_period": tp})
    assert r.status_code == 200, r.text
    out = r.json()
    assert_sales_stats_out(out)
    assert out["area_code"] == area_code
    assert out["time_period"] == tp


def test_sales_official_sales_stats_point_missing_required_params(client):
    r1 = client.get("/sales_official/sales-stats", params={"area_code": "E08000035"})
    assert r1.status_code == 422, r1.text

    r2 = client.get("/sales_official/sales-stats", params={"time_period": "2020-01"})
    assert r2.status_code == 422, r2.text


@pytest.mark.parametrize(
    "params",
    [
        {"min_price": -1},                 # minimum=0
        {"max_price": -10},
        {"property_type": "X"},            # enum D/S/T/F/O
        {"new_build": "maybe"},            # enum Y/N
        {"tenure": "Z"},                   # enum F/L/U
    ],
)
def test_sales_official_sales_stats_point_invalid_filters(client, params):
    area_code, av = find_area_with_sales_stats(client)
    tp = av["min_time_period"]

    p = {"area_code": area_code, "time_period": tp, **params}
    r = client.get("/sales_official/sales-stats", params=p)
    assert r.status_code == 422, r.text


def test_sales_official_sales_stats_point_unknown_area_or_month(client):
    r = client.get("/sales_official/sales-stats", params={"area_code": "ZZZ999", "time_period": "2020-01"})
    assert r.status_code == 404, r.text
    assert_error_out(r)


# tests: series
def test_sales_official_sales_stats_series_happy_path(client):
    area_code, av = find_area_with_sales_stats(client)
    lo, hi = av["min_time_period"], av["max_time_period"]

    r = client.get(
        f"/sales_official/areas/{area_code}/sales-stats",
        params={"from_period": lo, "to_period": hi, "limit": 240, "offset": 0},
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert_sales_stats_series_out(out)
    assert out["area_code"] == area_code

    # all items in range
    for it in out["items"]:
        assert month_in_range(it["time_period"], lo, hi)


def test_sales_official_sales_stats_series_limit_offset_validation(client):
    area_code, _ = find_area_with_sales_stats(client)

    r1 = client.get(f"/sales_official/areas/{area_code}/sales-stats", params={"limit": 0})
    assert r1.status_code == 422, r1.text

    r2 = client.get(f"/sales_official/areas/{area_code}/sales-stats", params={"limit": 501})
    assert r2.status_code == 422, r2.text

    r3 = client.get(f"/sales_official/areas/{area_code}/sales-stats", params={"offset": -1})
    assert r3.status_code == 422, r3.text


@pytest.mark.parametrize(
    "params",
    [
        {"min_price": -1},
        {"max_price": -1},
        {"property_type": "X"},
        {"new_build": "maybe"},
        {"tenure": "Z"},
    ],
)
def test_sales_official_sales_stats_series_invalid_filters(client, params):
    area_code, _ = find_area_with_sales_stats(client)
    r = client.get(f"/sales_official/areas/{area_code}/sales-stats", params=params)
    assert r.status_code == 422, r.text


def test_sales_official_sales_stats_series_unknown_area(client):
    r = client.get("/sales_official/areas/ZZZ999/sales-stats")
    assert r.status_code == 404, r.text
    assert_error_out(r)


# tests: latest
def test_sales_official_sales_stats_latest_happy_path(client):
    area_code, av = find_area_with_sales_stats(client)
    expected_latest = av["max_time_period"]

    r = client.get(f"/sales_official/areas/{area_code}/sales-stats/latest")
    assert r.status_code == 200, r.text
    out = r.json()
    assert_sales_stats_out(out)
    assert out["area_code"] == area_code

    assert out["time_period"] == expected_latest


@pytest.mark.parametrize(
    "params",
    [
        {"min_price": -1},
        {"property_type": "X"},
        {"new_build": "maybe"},
        {"tenure": "Z"},
    ],
)
def test_sales_official_sales_stats_latest_invalid_filters(client, params):
    area_code, _ = find_area_with_sales_stats(client)
    r = client.get(f"/sales_official/areas/{area_code}/sales-stats/latest", params=params)
    assert r.status_code == 422, r.text


def test_sales_official_sales_stats_latest_unknown_area(client):
    r = client.get("/sales_official/areas/ZZZ999/sales-stats/latest")
    assert r.status_code == 404, r.text
    assert_error_out(r)