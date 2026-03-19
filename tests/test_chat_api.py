import app.api.routers.router_chat as router_chat
import app.services.service_chat as service_chat


class ModelDumpResult:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self):
        return self.payload


class DictResult:
    def __init__(self, payload):
        self.payload = payload

    def dict(self):
        return self.payload


def test_chat_ask_postcode_lookup_branch(client, monkeypatch):
    monkeypatch.setattr(
        service_chat,
        "get_postcode_info",
        lambda postcode: ModelDumpResult(
            {"postcode": postcode, "area_code": "E08000035", "area_name": "Leeds"}
        ),
    )

    resp = client.post(
        "/chat/ask",
        json={"message": "Please check postcode LS2 9JT postcode"},
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["tool_used"] == "get_postcode_info"
    assert data["data"]["postcode"] == "LS2 9JT"
    assert data["data"]["area_code"] == "E08000035"


def test_chat_ask_rent_series_branch(client, monkeypatch):
    monkeypatch.setattr(
        service_chat,
        "get_rent_stats_series",
        lambda area_code: {
            "area_code": area_code,
            "count": 2,
            "items": [{"time_period": "2017-02"}, {"time_period": "2017-03"}],
        },
    )

    resp = client.post(
        "/chat/ask",
        json={"message": "Show me the rent trend for E08000035"},
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["tool_used"] == "get_rent_stats_series"
    assert data["data"]["area_code"] == "E08000035"
    assert data["data"]["count"] == 2


def test_chat_ask_area_lookup_branch(client, monkeypatch):
    monkeypatch.setattr(
        service_chat,
        "get_area_by_code",
        lambda area_code: DictResult({"area_code": area_code, "area_name": "Leeds"}),
    )

    resp = client.post(
        "/chat/ask",
        json={"message": "Can you check area code E08000035 area"},
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["tool_used"] == "get_area_by_code"
    assert data["data"]["area_code"] == "E08000035"
    assert data["data"]["area_name"] == "Leeds"


def test_chat_ask_invalid_payload_returns_422(client):
    resp = client.post("/chat/ask", json={})
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_chat_ask_value_error_returns_400(client, monkeypatch):
    def raise_value_error(_message):
        raise ValueError("bad chat input")

    monkeypatch.setattr(router_chat, "handle_chat_message", raise_value_error)

    resp = client.post("/chat/ask", json={"message": "broken input"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "bad chat input"


def test_chat_ask_unexpected_error_returns_500(client, monkeypatch):
    def raise_runtime_error(_message):
        raise RuntimeError("boom")

    monkeypatch.setattr(router_chat, "handle_chat_message", raise_runtime_error)

    resp = client.post("/chat/ask", json={"message": "trigger failure"})
    assert resp.status_code == 500
    assert resp.json()["detail"] == "chat error: boom"
