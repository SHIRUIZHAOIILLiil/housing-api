from app.api import deps


def test_get_conn_disables_sqlite_same_thread(monkeypatch):
    captured = {}

    class DummyConnection:
        def __init__(self):
            self.row_factory = None
            self.closed = False

        def close(self):
            self.closed = True

    def fake_connect(database_path, **kwargs):
        captured["database_path"] = database_path
        captured["kwargs"] = kwargs
        conn = DummyConnection()
        captured["conn"] = conn
        return conn

    monkeypatch.setattr(deps.sqlite3, "connect", fake_connect)

    conn_generator = deps.get_conn()
    conn = next(conn_generator)

    assert captured["database_path"] == deps.settings.DATABASE_DEMO
    assert captured["kwargs"]["check_same_thread"] is False
    assert conn.row_factory is deps.sqlite3.Row

    try:
        next(conn_generator)
    except StopIteration:
        pass

    assert captured["conn"].closed is True
