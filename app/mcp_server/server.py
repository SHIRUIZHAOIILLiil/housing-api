from mcp.server.fastmcp import FastMCP
import sqlite3
from typing import Literal

from app.core.config import Settings
from app.services import get_area, get_postcode_map, get_rent_stats_official_latest, get_official_sales_stats_latest, get_rent_stats_official_series
from app.schemas import SalesStatsLatestQuery

mcp = FastMCP("housing-api", host="127.0.0.1", port=8888,)

settings = Settings()


def get_db_conn():
    conn = sqlite3.connect(settings.DATABASE_DEMO)
    conn.row_factory = sqlite3.Row
    return conn


@mcp.tool()
def get_area_by_code(area_code: str) -> dict:
    conn = get_db_conn()
    try:
        result = get_area(conn, area_code)
        return dict(result)
    finally:
        conn.close()


@mcp.tool()
def get_postcode_info(postcode: str) -> dict:
    conn = get_db_conn()
    try:
        result = get_postcode_map(conn, postcode)
        return dict(result)
    finally:
        conn.close()


@mcp.tool()
def get_latest_rent_stats(area_code: str) -> dict:
    conn = get_db_conn()
    try:
        result = get_rent_stats_official_latest(conn, area_code)
        if result is None:
            return {"error": f"No rental data found for area_code={area_code}"}
        return result.model_dump()
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

@mcp.tool()
def get_rent_stats_series(area_code: str, from_: str | None = None, to: str | None = None) -> dict:
    conn = get_db_conn()
    try:
        result = get_rent_stats_official_series(conn, area_code, from_, to)
        return {
            "area_code": area_code,
            "count": len(result),
            "items": [item.model_dump() for item in result]
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

@mcp.tool()
def get_latest_sales_stats(
    area_code: str,
    min_price: float | None = None,
    max_price: float | None = None,
    property_type: Literal["D", "S", "T", "F", "O"] | None = None,
    new_build: bool | None = None,
    tenure: Literal["F", "L", "U"] | None = None,
) -> dict:
    conn = get_db_conn()
    try:
        filters = SalesStatsLatestQuery(
            min_price=min_price,
            max_price=max_price,
            property_type=property_type,
            new_build=new_build,
            tenure=tenure,
        )
        result = get_official_sales_stats_latest(conn, area_code, filters)

        if result is None:
            return {"error": f"No sales stats found for area_code={area_code}"}

        return result.model_dump() if hasattr(result, "model_dump") else result
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

if __name__ == "__main__":
    mcp.run(transport="streamable-http")