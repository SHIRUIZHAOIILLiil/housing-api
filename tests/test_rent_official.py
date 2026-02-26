
def test_list_rent_official_success(client):
    r = client.get("/rent_stats_official/rent-stats", params={"area_code": "E08000035", "time_period": "2017-02"})
    assert r.status_code == 200
    data = r.json()
    assert data["region_or_country_name"] == "Yorkshire and The Humber"

def test_list_rent_official_with_wrong_area_code(client):
    r = client.get("/rent_stats_official/rent-stats", params={"area_code": "E0800003x", "time_period": "2017-02"})
    assert r.status_code == 404
    err = r.json()
    assert "detail" in err

def test_list_rent_official_with_wrong_time_period(client):
    r = client.get("/rent_stats_official/rent-stats", params={"area_code": "E08000035", "time_period": "2018-02"})
    assert r.status_code == 404
    err = r.json()
    assert "detail" in err

def test_list_rent_official_series(client):
    area_code = "E08000035"
    r = client.get(f"/rent_stats_official/areas/{area_code}/rent-stats",
                   params={"from": "2017-02", "to": "2017-06"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 5

def test_list_rent_official_series_with_wrong_area_code(client):
    area_code = "E0800003x"
    r = client.get(f"/rent_stats_official/areas/{area_code}/rent-stats",
                   params={"from": "2017-02", "to": "2017-06"})
    assert r.status_code == 404
    err = r.json()
    assert "detail" in err

def test_list_rent_official_series_no_data(client):
    area_code = "E08000035"
    r = client.get(f"/rent_stats_official/areas/{area_code}/rent-stats",
                   params={"from": "2017-01", "to": "2017-01"})
    assert r.status_code == 200
    assert r.json() == []

def test_rent_series_invalid_time_format(client):
    area_code = "E08000035"
    r = client.get(
        f"/rent_stats_official/areas/{area_code}/rent-stats",
        params={"from": "2017-99", "to": "abcd"}
    )
    assert r.status_code == 422
    err = r.json()
    assert "detail" in err

def test_rent_series_invalid_time(client):
    area_code = "E08000035"
    r = client.get(
        f"/rent_stats_official/areas/{area_code}/rent-stats",
        params={"from": "2017-06", "to": "2017-02"}
    )
    assert r.status_code == 400
    err = r.json()
    assert "detail" in err

def test_rent_official_latest(client):
    area_code = "E08000035"
    r = client.get(f"/rent_stats_official/areas/{area_code}/rent-stats/latest")
    assert r.status_code == 200
    data = r.json()
    assert data["time_period"] == "2017-06"

def test_rent_official_latest_failed(client):
    area_code = "E0800003x"
    r = client.get(f"/rent_stats_official/areas/{area_code}/rent-stats/latest")
    assert r.status_code == 404
    err = r.json()
    assert "detail" in err

def test_rent_official_availability(client):
    area_code = "E08000035"
    r = client.get(f"/rent_stats_official/areas/{area_code}/rent-stats/availability")
    assert r.status_code == 200
    data = r.json()
    assert data["min_time_period"] == "2017-02"
    assert data["max_time_period"] == "2017-06"
    assert data["count"] == 5

def test_rent_official_availability_area_not_found(client):
    area_code = "E0800003x"
    r = client.get(f"/rent_stats_official/areas/{area_code}/rent-stats/availability")
    assert r.status_code == 404
    err = r.json()
    assert "detail" in err

def test_rent_official_trend_area_code(client):
    area_code = "E08000035"
    metrics = ["rental_price", "index_value"]
    bedrooms = ["overall", 1, 2, 3]
    r = client.get(f"/rent_stats_official/areas/{area_code}/rent-trend.png",
                   params={"from": "2017-02", "to": "2017-06", "metric": "annual_change"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert len(r.content) > 0
    assert r.content.startswith(b"\x89PNG\r\n\x1a\n")

    for metric in metrics:
        for bedroom in bedrooms:
            r = client.get(f"/rent_stats_official/areas/{area_code}/rent-trend.png",
                   params={"from": "2017-02", "to": "2017-06", "metric": metric, "bedroom": bedroom})
            assert r.status_code == 200
            assert r.headers["content-type"] == "image/png"
            assert len(r.content) > 0
            assert r.content.startswith(b"\x89PNG\r\n\x1a\n")

def assert_error_json(response, code):
    assert response.status_code == code
    assert "application/json" in response.headers.get("content-type", "")
    err = response.json()
    assert "detail" in err

def test_rent_official_trend_area_code_failed(client):
    area_code_wrong = "E0800003x"
    area_code = "E08000035"
    r_wrong_ac = client.get(f"/rent_stats_official/areas/{area_code_wrong}/rent-trend.png",
                   params={"from": "2017-02", "to": "2017-06"})
    assert_error_json(r_wrong_ac, 404)

    r_wrong_period = client.get(f"/rent_stats_official/areas/{area_code}/rent-trend.png",
                   params={"from": "2017-06", "to": "2017-02"})
    assert_error_json(r_wrong_period, 400)

    r_invalid_input = client.get(f"/rent_stats_official/areas/{area_code}/rent-trend.png",
                   params={"from": "aaa", "to": "2017-02"})
    assert_error_json(r_invalid_input, 422)

    r_wrong_bed = client.get(f"/rent_stats_official/areas/{area_code}/rent-trend.png",
                   params={"from": "2017-02", "to": "2017-06", "bedrooms": 4})
    assert_error_json(r_wrong_bed, 422)

    r_wrong_parameter_matching = client.get(f"/rent_stats_official/areas/{area_code}/rent-trend.png",
                   params={"from": "2017-02", "to": "2017-06", "metric": "annual_year" , "bedrooms": 1})
    assert_error_json(r_wrong_parameter_matching, 422)


def test_rent_official_trend_area_name(client):
    area_name = "leeds"
    metrics = ["rental_price", "index_value"]
    bedrooms = ["overall", 1, 2, 3]
    r = client.get("/rent_stats_official/areas/rent-trend.png",
                   params={"area": area_name, "from": "2017-02", "to": "2017-06", "metric": "annual_change"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert len(r.content) > 0
    assert r.content.startswith(b"\x89PNG\r\n\x1a\n")

    for metric in metrics:
        for bedroom in bedrooms:
            r = client.get("/rent_stats_official/areas/rent-trend.png",
                   params={"area": area_name, "from": "2017-02", "to": "2017-06", "metric": metric, "bedroom": bedroom})
            assert r.status_code == 200
            assert r.headers["content-type"] == "image/png"
            assert len(r.content) > 0
            assert r.content.startswith(b"\x89PNG\r\n\x1a\n")

BASE_PARAMETERS_FOR_TREND_NAME = {
    "area": "leeds",
    "from": "2017-02",
    "to": "2017-06",
    "metric": "rental_price",
    "bedrooms": 1
}

def test_rent_official_trend_area_name_failed(client):
    BASE_PARAMETERS_FOR_TREND_NAME["area"] = "s"
    print(BASE_PARAMETERS_FOR_TREND_NAME)
    r_wrong_name = client.get("/rent_stats_official/areas/rent-trend.png",
                   params=BASE_PARAMETERS_FOR_TREND_NAME)
    assert_error_json(r_wrong_name, 400)

    BASE_PARAMETERS_FOR_TREND_NAME["area"] = "leeds"
    BASE_PARAMETERS_FOR_TREND_NAME["from"] = "2017-06"
    BASE_PARAMETERS_FOR_TREND_NAME["to"] = "2017-02"
    r_wrong_period = client.get("/rent_stats_official/areas/rent-trend.png",
                   params=BASE_PARAMETERS_FOR_TREND_NAME)
    assert_error_json(r_wrong_period, 400)

    BASE_PARAMETERS_FOR_TREND_NAME["from"] = "aaa"
    r_invalid_input = client.get("/rent_stats_official/areas/rent-trend.png",
                   params={"from": "aaa", "to": "2017-02"})
    assert_error_json(r_invalid_input, 422)

    BASE_PARAMETERS_FOR_TREND_NAME["from"] = "2017-02"
    BASE_PARAMETERS_FOR_TREND_NAME["to"] = "2017-06"
    BASE_PARAMETERS_FOR_TREND_NAME["bedrooms"] = 4
    r_wrong_bed = client.get("/rent_stats_official/areas/rent-trend.png",
                   params=BASE_PARAMETERS_FOR_TREND_NAME)
    assert_error_json(r_wrong_bed, 422)

    BASE_PARAMETERS_FOR_TREND_NAME["bedrooms"] = 1
    BASE_PARAMETERS_FOR_TREND_NAME["metric"] = "annual_year"
    r_wrong_parameter_matching = client.get("/rent_stats_official/areas/rent-trend.png",
                   params={"from": "2017-02", "to": "2017-06", "metric": "annual_year" , "bedrooms": 1})
    assert_error_json(r_wrong_parameter_matching, 422)