import tempfile, pathlib


def test_replan_log_table_exists():
    """plan_replan_log tabel moet na migrate_db bestaan."""
    from db import get_conn, migrate_db
    with tempfile.TemporaryDirectory() as tmp:
        db_path = pathlib.Path(tmp) / "test.db"
        migrate_db(db_path)
        with get_conn(db_path) as conn:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            assert "plan_replan_log" in tables, f"Tabellen: {tables}"


def test_coach_chat_table_exists():
    """coach_chat tabel moet na init_db/migrate_db bestaan."""
    from db import get_conn, migrate_db
    import tempfile, pathlib
    with tempfile.TemporaryDirectory() as tmp:
        db_path = pathlib.Path(tmp) / "test.db"
        migrate_db(db_path)
        with get_conn(db_path) as conn:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            assert "coach_chat" in tables, f"Tabellen: {tables}"
