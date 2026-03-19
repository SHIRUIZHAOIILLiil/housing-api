import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.main import create_app


def _extract_series_value(point: dict, metric: str, bedrooms: str):
    if bedrooms == "overall":
        if metric == "index_value":
            return point["overall"]["index"]
        return point["overall"][metric]

    bedroom_key = {
        "1": "one_bed",
        "2": "two_bed",
        "3": "three_bed",
    }[bedrooms]
    bedroom_point = point[bedroom_key]

    if metric == "index_value":
        return bedroom_point["index"]

    return bedroom_point["rental_price"]


def _init_minimal_map_db(db_path, area_code: str, area_name: str, region_name: str, rows: list[tuple[str, float, float, float]]):
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE areas (
            area_code TEXT PRIMARY KEY,
            area_name TEXT NOT NULL
        );

        CREATE TABLE rent_stats_official (
            time_period TEXT NOT NULL,
            area_code TEXT NOT NULL,
            region_or_country_name TEXT NOT NULL,
            index_value REAL,
            annual_change REAL,
            rental_price REAL,
            index_one_bed REAL,
            rental_price_one_bed REAL,
            index_two_bed REAL,
            rental_price_two_bed REAL,
            index_three_bed REAL,
            rental_price_three_bed REAL,
            rental_price_detached REAL,
            rental_price_semidetached REAL,
            rental_price_terraced REAL,
            rental_price_flat_maisonette REAL,
            PRIMARY KEY (time_period, area_code)
        );
        """
    )

    conn.execute(
        "INSERT INTO areas(area_code, area_name) VALUES (?, ?)",
        (area_code, area_name),
    )

    conn.executemany(
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
            (
                time_period,
                area_code,
                region_name,
                index_value,
                annual_change,
                rental_price,
                index_value + 0.5,
                rental_price - 120,
                index_value + 1.0,
                rental_price - 70,
                index_value + 1.5,
                rental_price - 20,
                rental_price + 240,
                rental_price + 110,
                rental_price + 40,
                rental_price - 160,
            )
            for time_period, rental_price, index_value, annual_change in rows
        ],
    )
    conn.commit()
    conn.close()


def test_map_page_exposes_optional_trend_filter_controls(client):
    resp = client.get("/map")
    assert resp.status_code == 200
    text = resp.text

    assert 'id="rentExplorerApplyTrendBtn"' in text
    assert "Update Trends" in text
    assert "Drag to pan and use the controls or mouse wheel to zoom" in text


def test_static_map_js_contains_click_and_optional_filter_contract(client):
    resp = client.get("/static/map.js")
    assert resp.status_code == 200
    text = resp.text

    assert "resolveTrendRangeInputs" in text
    assert "rentExplorerApplyTrendBtn" in text
    assert "mapDragActive" in text
    assert "full history from" in text


def test_map_summary_items_have_loadable_trend_series(client):
    summary_resp = client.get("/rent_stats_official/map/summary")
    assert summary_resp.status_code == 200, summary_resp.text
    summary = summary_resp.json()

    assert summary["item_count"] == len(summary["items"])
    assert summary["items"], "Map summary should contain at least one area."

    for item in summary["items"]:
        series_resp = client.get(f"/rent_stats_official/areas/{item['area_code']}/rent-stats")
        assert series_resp.status_code == 200, series_resp.text
        series = series_resp.json()

        assert series, f"Area {item['area_code']} is visible on the map but has no trend series."
        assert series[0]["time_period"] == summary["min_time_period"]
        assert series[-1]["time_period"] == summary["max_time_period"]


@pytest.mark.parametrize(
    ("metric", "bedrooms"),
    [
        ("rental_price", "overall"),
        ("index_value", "2"),
        ("annual_change", "overall"),
    ],
)
def test_map_summary_values_match_series_snapshot(client, metric: str, bedrooms: str):
    summary_resp = client.get(
        "/rent_stats_official/map/summary",
        params={"metric": metric, "bedrooms": bedrooms},
    )
    assert summary_resp.status_code == 200, summary_resp.text
    summary = summary_resp.json()

    resolved_time_period = summary["resolved_time_period"]

    for item in summary["items"]:
        series_resp = client.get(f"/rent_stats_official/areas/{item['area_code']}/rent-stats")
        assert series_resp.status_code == 200, series_resp.text
        series = series_resp.json()

        point = next(row for row in series if row["time_period"] == resolved_time_period)
        expected_value = _extract_series_value(point, metric, bedrooms)

        assert expected_value is not None
        assert item["value"] == pytest.approx(float(expected_value))


def test_switching_between_compatible_database_files_keeps_map_endpoints_working(tmp_path, monkeypatch):
    db_one = tmp_path / "map_one.db"
    db_two = tmp_path / "map_two.db"

    _init_minimal_map_db(
        db_one,
        area_code="E08000035",
        area_name="Leeds",
        region_name="Yorkshire and The Humber",
        rows=[
            ("2021-01", 920.0, 101.0, 3.2),
            ("2021-02", 935.0, 102.4, 3.5),
        ],
    )
    _init_minimal_map_db(
        db_two,
        area_code="E07000240",
        area_name="St Albans",
        region_name="East of England",
        rows=[
            ("2024-05", 1510.0, 118.2, 4.1),
            ("2024-06", 1525.0, 119.7, 4.4),
        ],
    )

    monkeypatch.setattr(deps.settings, "DATABASE_DEMO", str(db_one))
    with TestClient(create_app()) as first_client:
        summary_resp = first_client.get("/rent_stats_official/map/summary")
        assert summary_resp.status_code == 200, summary_resp.text
        summary = summary_resp.json()

        assert summary["resolved_time_period"] == "2021-02"
        assert summary["min_time_period"] == "2021-01"
        assert summary["items"][0]["area_code"] == "E08000035"

        series_resp = first_client.get("/rent_stats_official/areas/E08000035/rent-stats")
        assert series_resp.status_code == 200, series_resp.text
        assert len(series_resp.json()) == 2

    monkeypatch.setattr(deps.settings, "DATABASE_DEMO", str(db_two))
    with TestClient(create_app()) as second_client:
        summary_resp = second_client.get("/rent_stats_official/map/summary")
        assert summary_resp.status_code == 200, summary_resp.text
        summary = summary_resp.json()

        assert summary["resolved_time_period"] == "2024-06"
        assert summary["min_time_period"] == "2024-05"
        assert summary["items"][0]["area_code"] == "E07000240"

        series_resp = second_client.get("/rent_stats_official/areas/E07000240/rent-stats")
        assert series_resp.status_code == 200, series_resp.text
        assert len(series_resp.json()) == 2
