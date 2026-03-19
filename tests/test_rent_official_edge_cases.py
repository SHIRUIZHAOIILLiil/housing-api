def test_rent_official_latest_area_exists_but_has_no_stats(client, db_conn):
    db_conn.execute(
        "INSERT INTO areas(area_code, area_name) VALUES (?, ?)",
        ("E09000999", "Empty Area"),
    )
    db_conn.commit()

    resp = client.get("/rent_stats_official/areas/E09000999/rent-stats/latest")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No rent stats available"


def test_rent_map_summary_returns_404_when_dataset_is_empty(client, db_conn):
    db_conn.execute("DELETE FROM rent_stats_official")
    db_conn.commit()

    resp = client.get("/rent_stats_official/map/summary")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No official rent data available"


def test_rent_map_summary_returns_404_for_missing_snapshot_month(client):
    resp = client.get(
        "/rent_stats_official/map/summary",
        params={"time_period": "2016-01"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No rent map data available for the given inputs"


def test_rent_trend_by_name_returns_404_for_unknown_area(client):
    resp = client.get(
        "/rent_stats_official/areas/rent-trend.png",
        params={"area": "not-a-real-area", "from": "2017-02", "to": "2017-06"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Area not found"


def test_rent_trend_png_returns_404_when_metric_has_no_usable_points(client, db_conn):
    db_conn.execute(
        "INSERT INTO areas(area_code, area_name) VALUES (?, ?)",
        ("E09000998", "Null Annual Change Area"),
    )
    db_conn.executemany(
        """
        INSERT INTO rent_stats_official(
            time_period,
            area_code,
            region_or_country_name,
            index_value,
            annual_change,
            rental_price,
            index_one_bed,
            rental_price_one_bed,
            index_two_bed,
            rental_price_two_bed,
            index_three_bed,
            rental_price_three_bed,
            rental_price_detached,
            rental_price_semidetached,
            rental_price_terraced,
            rental_price_flat_maisonette
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("2019-01", "E09000998", "London", 105.0, None, 1200.0, 106.0, 980.0, 107.0, 1080.0, 108.0, 1180.0, 1600.0, 1450.0, 1300.0, 950.0),
            ("2019-02", "E09000998", "London", 106.0, None, 1210.0, 107.0, 990.0, 108.0, 1090.0, 109.0, 1190.0, 1610.0, 1460.0, 1310.0, 960.0),
        ],
    )
    db_conn.commit()

    resp = client.get(
        "/rent_stats_official/areas/E09000998/rent-trend.png",
        params={"from": "2019-01", "to": "2019-02", "metric": "annual_change"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "No usable data in range"
