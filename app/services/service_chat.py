import re
from typing import Any

from app.mcp_server import (
    get_area_by_code,
    get_postcode_info,
    get_latest_rent_stats,
    get_rent_stats_series,
    get_latest_sales_stats,
)


AREA_CODE_PATTERN = r"\b[EWSN]\d{8}\b"
POSTCODE_PATTERN = r"\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b"


def _extract_area_code(text: str) -> str | None:
    match = re.search(AREA_CODE_PATTERN, text.upper())
    return match.group(0) if match else None


def _extract_postcode(text: str) -> str | None:
    match = re.search(POSTCODE_PATTERN, text.upper())
    if not match:
        return None
    return match.group(0).strip()


def _normalize_result(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj


def handle_chat_message(message: str) -> dict[str, Any]:
    text = message.strip()
    lower = text.lower()

    area_code = _extract_area_code(text)
    postcode = _extract_postcode(text)

    if postcode and ("postcode" in lower or "邮编" in lower):
        result = _normalize_result(get_postcode_info(postcode))
        return {
            "tool_used": "get_postcode_info",
            "reply": f"I checked postcode {postcode}.",
            "data": result,
        }

    if area_code and ("series" in lower or "trend" in lower or "时间序列" in lower or "趋势" in lower):
        result = _normalize_result(get_rent_stats_series(area_code))
        return {
            "tool_used": "get_rent_stats_series",
            "reply": f"I found the rent time series for {area_code}.",
            "data": result,
        }

    if area_code and ("rent" in lower or "租金" in lower):
        result = _normalize_result(get_latest_rent_stats(area_code))
        return {
            "tool_used": "get_latest_rent_stats",
            "reply": f"I found the latest rent stats for {area_code}.",
            "data": result,
        }

    if area_code and ("sales" in lower or "sale" in lower or "房价" in lower or "成交" in lower):
        result = _normalize_result(get_latest_sales_stats(area_code))
        return {
            "tool_used": "get_latest_sales_stats",
            "reply": f"I found the latest sales stats for {area_code}.",
            "data": result,
        }

    if area_code and ("area" in lower or "地区" in lower or "区域" in lower or "code" in lower):
        result = _normalize_result(get_area_by_code(area_code))
        return {
            "tool_used": "get_area_by_code",
            "reply": f"I checked area code {area_code}.",
            "data": result,
        }

    return {
        "tool_used": None,
        "reply": (
            "I can help with:\n"
            "- area lookup by area code\n"
            "- postcode info lookup\n"
            "- latest rent stats by area code\n"
            "- rent time series by area code\n"
            "- latest sales stats by area code"
        ),
        "data": None,
    }