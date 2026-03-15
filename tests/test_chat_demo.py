
def test_chat_ask_latest_rent_stats_smoke(client):
    resp = client.post(
        "/chat/ask",
        json={"message": "show me the latest rent stats for E08000035"},
    )

    assert resp.status_code == 200
    data = resp.json()

    assert data["tool_used"] == "get_latest_rent_stats"
    assert "E08000035" in data["reply"]
    assert data["data"] is not None
    assert data["data"]["area_code"] == "E08000035"


def test_chat_ask_latest_sales_stats_smoke(client):
    resp = client.post(
        "/chat/ask",
        json={"message": "show me latest sales stats for E08000035"},
    )

    assert resp.status_code == 200
    data = resp.json()

    assert data["tool_used"] == "get_latest_sales_stats"
    assert "E08000035" in data["reply"]
    assert data["data"] is not None
    assert data["data"]["area_code"] == "E08000035"


def test_chat_ask_unrecognized_input_returns_help(client):
    resp = client.post(
        "/chat/ask",
        json={"message": "hello can you do something interesting for me"},
    )

    assert resp.status_code == 200
    data = resp.json()

    assert data["tool_used"] is None
    assert data["data"] is None
    assert "I can help with" in data["reply"]