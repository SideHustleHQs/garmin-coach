import sqlite3
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_conn, init_db


def make_tmp_db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    p = Path(tmp.name)
    tmp.close()
    init_db(p)
    return p


def test_schema_creates_all_tables():
    p = make_tmp_db()
    conn = get_conn(p)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert tables == {
        "athletes", "activities", "daily_stats",
        "daily_heart_rates", "body_battery",
        "training_readiness", "vo2max",
    }
    p.unlink()
