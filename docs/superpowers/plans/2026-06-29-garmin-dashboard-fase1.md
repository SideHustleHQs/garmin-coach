# Garmin Coach Dashboard — Fase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lokaal hardloop-dashboard met echte Garmin-data voor atleet "vriendin" (Dam tot Damloop 20 sep 2026), klaar voor fase-2 AI-coach.

**Architecture:** JSON-bestanden uit `output/<athlete>/` worden via `ingest.py` geüpsert naar SQLite. Een FastAPI-server serveert de data via `/api/*`. Een Vite+React dashboard haalt die data op en toont donkere thema-panels op basis van het ontwerp `design/dam-tot-dam-dashboard-v2.jsx`.

**Tech Stack:** Python 3.9+, FastAPI, uvicorn, sqlite3 (stdlib), Vite 5, React 18, recharts 2, lucide-react, Tailwind CSS (via CDN-free inline theme vars)

---

## Mapstructuur na implementatie

```
~/Documents/garmin-coach/
├── garmin_test_pull.py          ← ongewijzigd
├── db.py                        ← schema init + connectie helper
├── ingest.py                    ← JSON → SQLite upsert per atleet
├── api/
│   ├── __init__.py
│   ├── main.py                  ← FastAPI app
│   └── routes.py                ← alle /api/* endpoints
├── dashboard/                   ← Vite project
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx              ← tab-routing per atleet
│       ├── api.js               ← fetch-wrapper
│       ├── theme.css            ← CSS vars donker thema
│       └── components/
│           ├── GoalBanner.jsx
│           ├── HeroRow.jsx
│           ├── WeekVolume.jsx
│           ├── TempoTrend.jsx
│           ├── ZoneDistribution.jsx
│           ├── VO2MaxTrend.jsx
│           ├── RecentRuns.jsx
│           ├── DailyStats.jsx
│           ├── RecoveryStrip.jsx
│           └── CoachCard.jsx
├── tests/
│   ├── test_ingest.py
│   └── test_api.py
├── design/
│   └── dam-tot-dam-dashboard-v2.jsx   ← visuele blauwdruk (user plaatst dit)
├── requirements.txt
└── start.sh
```

**Data-flow:**
```
output/vriendin/*.json
      ↓ ingest.py
garmin_coach.db (SQLite)
      ↓ FastAPI :8000
dashboard React :5173
```

---

## Task 1: requirements.txt + db.py (schema + connectie)

**Files:**
- Create: `requirements.txt`
- Create: `db.py`
- Create: `tests/test_ingest.py` (initieel alleen schema-test)

- [ ] **Stap 1: Schrijf requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-garminconnect==0.2.22
```

- [ ] **Stap 2: Schrijf db.py**

```python
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "garmin_coach.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS athletes (
    id          TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    panels_config TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS activities (
    athlete_id   TEXT NOT NULL,
    activity_id  INTEGER NOT NULL,
    date         TEXT NOT NULL,
    name         TEXT,
    type_key     TEXT,
    distance_m   REAL,
    duration_s   REAL,
    avg_speed_mps REAL,
    avg_hr       REAL,
    max_hr       REAL,
    hr_zone_1_s  REAL,
    hr_zone_2_s  REAL,
    hr_zone_3_s  REAL,
    hr_zone_4_s  REAL,
    hr_zone_5_s  REAL,
    aerobic_effect  REAL,
    anaerobic_effect REAL,
    avg_cadence  REAL,
    PRIMARY KEY (athlete_id, activity_id),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);

CREATE TABLE IF NOT EXISTS daily_stats (
    athlete_id     TEXT NOT NULL,
    date           TEXT NOT NULL,
    steps          INTEGER,
    active_calories REAL,
    total_calories REAL,
    PRIMARY KEY (athlete_id, date),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);

CREATE TABLE IF NOT EXISTS daily_heart_rates (
    athlete_id  TEXT NOT NULL,
    date        TEXT NOT NULL,
    min_hr      INTEGER,
    max_hr      INTEGER,
    resting_hr  INTEGER,
    PRIMARY KEY (athlete_id, date),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);

CREATE TABLE IF NOT EXISTS body_battery (
    athlete_id TEXT NOT NULL,
    date       TEXT NOT NULL,
    charged    REAL,
    drained    REAL,
    PRIMARY KEY (athlete_id, date),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);

CREATE TABLE IF NOT EXISTS training_readiness (
    athlete_id     TEXT NOT NULL,
    date           TEXT NOT NULL,
    score          INTEGER,
    level          TEXT,
    feedback_short TEXT,
    PRIMARY KEY (athlete_id, date),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);

CREATE TABLE IF NOT EXISTS vo2max (
    athlete_id TEXT NOT NULL,
    date       TEXT NOT NULL,
    vo2max     REAL,
    PRIMARY KEY (athlete_id, date),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);
"""


def get_conn(path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(path: Path = DB_PATH) -> None:
    with get_conn(path) as conn:
        conn.executescript(SCHEMA)
```

- [ ] **Stap 3: Schrijf schema-test**

```python
# tests/test_ingest.py
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
```

- [ ] **Stap 4: Draai test — verwacht PASS**

```bash
cd ~/Documents/garmin-coach
source .venv/bin/activate
pip install fastapi uvicorn
python -m pytest tests/test_ingest.py::test_schema_creates_all_tables -v
```

Verwacht: `PASSED`

- [ ] **Stap 5: Commit**

```bash
git add requirements.txt db.py tests/test_ingest.py
git commit -m "feat: SQLite schema + connection helper"
```

---

## Task 2: ingest.py — JSON → DB upsert

**Files:**
- Create: `ingest.py`
- Modify: `tests/test_ingest.py` (voeg ingest-tests toe)

- [ ] **Stap 1: Schrijf ingest-tests (failing)**

Voeg toe aan `tests/test_ingest.py`:

```python
import json

# import ingest functions — defined in next step
from ingest import (
    upsert_athlete,
    ingest_activities,
    ingest_daily_stats,
    ingest_daily_heart_rates,
    ingest_body_battery,
    ingest_training_readiness,
    ingest_vo2max_from_training_status,
)

SAMPLE_ACTIVITIES = [
    {
        "activityId": 99001,
        "activityName": "Test Run",
        "startTimeLocal": "2026-06-20 08:00:00",
        "activityType": {"typeKey": "running"},
        "distance": 5000.0,
        "duration": 1500.0,
        "averageSpeed": 3.33,
        "averageHR": 155.0,
        "maxHR": 170.0,
        "hrTimeInZone_1": 60.0,
        "hrTimeInZone_2": 300.0,
        "hrTimeInZone_3": 600.0,
        "hrTimeInZone_4": 420.0,
        "hrTimeInZone_5": 120.0,
        "aerobicTrainingEffect": 3.5,
        "anaerobicTrainingEffect": 0.5,
        "averageRunningCadenceInStepsPerMinute": 168.0,
    }
]

SAMPLE_STATS = {
    "2026-06-20": {
        "totalSteps": 8000,
        "activeKilocalories": 400.0,
        "totalKilocalories": 2000.0,
    }
}

SAMPLE_HEART_RATES = {
    "2026-06-20": {
        "minHeartRate": 48,
        "maxHeartRate": 170,
        "restingHeartRate": 52,
    }
}

SAMPLE_BODY_BATTERY = [
    {"date": "2026-06-20", "charged": 80.0, "drained": 40.0}
]

SAMPLE_TRAINING_READINESS = {
    "2026-06-20": [
        {
            "calendarDate": "2026-06-20",
            "score": 78,
            "level": "HIGH",
            "feedbackShort": "WELL_RECOVERED",
        }
    ]
}

SAMPLE_TRAINING_STATUS = {
    "2026-06-20": {
        "mostRecentVO2Max": {
            "generic": {
                "calendarDate": "2026-06-16",
                "vo2MaxValue": 49.0,
            }
        }
    }
}


def test_upsert_athlete_idempotent():
    p = make_tmp_db()
    conn = get_conn(p)
    upsert_athlete(conn, "vriendin", "Vriendin", ["GoalBanner", "HeroRow"])
    upsert_athlete(conn, "vriendin", "Vriendin Updated", ["GoalBanner"])
    row = conn.execute("SELECT display_name FROM athletes WHERE id='vriendin'").fetchone()
    assert row["display_name"] == "Vriendin Updated"
    p.unlink()


def test_ingest_activities_upsert():
    p = make_tmp_db()
    conn = get_conn(p)
    upsert_athlete(conn, "vriendin", "Vriendin", [])
    ingest_activities(conn, "vriendin", SAMPLE_ACTIVITIES)
    ingest_activities(conn, "vriendin", SAMPLE_ACTIVITIES)  # second run = no duplicate
    count = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    assert count == 1
    row = conn.execute("SELECT distance_m FROM activities").fetchone()
    assert row["distance_m"] == 5000.0
    p.unlink()


def test_ingest_daily_stats():
    p = make_tmp_db()
    conn = get_conn(p)
    upsert_athlete(conn, "vriendin", "Vriendin", [])
    ingest_daily_stats(conn, "vriendin", SAMPLE_STATS)
    row = conn.execute("SELECT steps FROM daily_stats WHERE date='2026-06-20'").fetchone()
    assert row["steps"] == 8000
    p.unlink()


def test_ingest_body_battery_null_ok():
    p = make_tmp_db()
    conn = get_conn(p)
    upsert_athlete(conn, "vriendin", "Vriendin", [])
    ingest_body_battery(conn, "vriendin", [{"date": "2026-06-20", "charged": None, "drained": None}])
    row = conn.execute("SELECT charged FROM body_battery WHERE date='2026-06-20'").fetchone()
    assert row is not None  # row exists, value is null — that's fine
    p.unlink()


def test_ingest_training_readiness():
    p = make_tmp_db()
    conn = get_conn(p)
    upsert_athlete(conn, "vriendin", "Vriendin", [])
    ingest_training_readiness(conn, "vriendin", SAMPLE_TRAINING_READINESS)
    row = conn.execute("SELECT score FROM training_readiness WHERE date='2026-06-20'").fetchone()
    assert row["score"] == 78
    p.unlink()


def test_ingest_vo2max():
    p = make_tmp_db()
    conn = get_conn(p)
    upsert_athlete(conn, "vriendin", "Vriendin", [])
    ingest_vo2max_from_training_status(conn, "vriendin", SAMPLE_TRAINING_STATUS)
    row = conn.execute("SELECT vo2max FROM vo2max WHERE date='2026-06-16'").fetchone()
    assert row["vo2max"] == 49.0
    p.unlink()
```

- [ ] **Stap 2: Draai tests — verwacht FAIL (importfout)**

```bash
python -m pytest tests/test_ingest.py -v 2>&1 | head -20
```

- [ ] **Stap 3: Schrijf ingest.py**

```python
#!/usr/bin/env python3
"""Ingest JSON-bestanden uit output/<athlete>/ naar SQLite."""

import json
import sqlite3
import sys
from pathlib import Path

from db import DB_PATH, get_conn, init_db


def upsert_athlete(conn: sqlite3.Connection, athlete_id: str, display_name: str, panels: list) -> None:
    conn.execute(
        """
        INSERT INTO athletes (id, display_name, panels_config)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            display_name  = excluded.display_name,
            panels_config = excluded.panels_config
        """,
        (athlete_id, display_name, json.dumps(panels)),
    )
    conn.commit()


def ingest_activities(conn: sqlite3.Connection, athlete_id: str, data: list) -> int:
    count = 0
    for a in data:
        date = (a.get("startTimeLocal") or "")[:10]
        conn.execute(
            """
            INSERT INTO activities (
                athlete_id, activity_id, date, name, type_key,
                distance_m, duration_s, avg_speed_mps, avg_hr, max_hr,
                hr_zone_1_s, hr_zone_2_s, hr_zone_3_s, hr_zone_4_s, hr_zone_5_s,
                aerobic_effect, anaerobic_effect, avg_cadence
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(athlete_id, activity_id) DO UPDATE SET
                date=excluded.date, name=excluded.name, type_key=excluded.type_key,
                distance_m=excluded.distance_m, duration_s=excluded.duration_s,
                avg_speed_mps=excluded.avg_speed_mps, avg_hr=excluded.avg_hr,
                max_hr=excluded.max_hr,
                hr_zone_1_s=excluded.hr_zone_1_s, hr_zone_2_s=excluded.hr_zone_2_s,
                hr_zone_3_s=excluded.hr_zone_3_s, hr_zone_4_s=excluded.hr_zone_4_s,
                hr_zone_5_s=excluded.hr_zone_5_s,
                aerobic_effect=excluded.aerobic_effect,
                anaerobic_effect=excluded.anaerobic_effect,
                avg_cadence=excluded.avg_cadence
            """,
            (
                athlete_id,
                a.get("activityId"),
                date,
                a.get("activityName"),
                (a.get("activityType") or {}).get("typeKey"),
                a.get("distance"),
                a.get("duration"),
                a.get("averageSpeed"),
                a.get("averageHR"),
                a.get("maxHR"),
                a.get("hrTimeInZone_1"),
                a.get("hrTimeInZone_2"),
                a.get("hrTimeInZone_3"),
                a.get("hrTimeInZone_4"),
                a.get("hrTimeInZone_5"),
                a.get("aerobicTrainingEffect"),
                a.get("anaerobicTrainingEffect"),
                a.get("averageRunningCadenceInStepsPerMinute"),
            ),
        )
        count += 1
    conn.commit()
    return count


def ingest_daily_stats(conn: sqlite3.Connection, athlete_id: str, data: dict) -> int:
    count = 0
    for date, row in data.items():
        if row is None:
            continue
        conn.execute(
            """
            INSERT INTO daily_stats (athlete_id, date, steps, active_calories, total_calories)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
                steps=excluded.steps,
                active_calories=excluded.active_calories,
                total_calories=excluded.total_calories
            """,
            (athlete_id, date, row.get("totalSteps"), row.get("activeKilocalories"), row.get("totalKilocalories")),
        )
        count += 1
    conn.commit()
    return count


def ingest_daily_heart_rates(conn: sqlite3.Connection, athlete_id: str, data: dict) -> int:
    count = 0
    for date, row in data.items():
        if row is None:
            continue
        conn.execute(
            """
            INSERT INTO daily_heart_rates (athlete_id, date, min_hr, max_hr, resting_hr)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
                min_hr=excluded.min_hr, max_hr=excluded.max_hr, resting_hr=excluded.resting_hr
            """,
            (athlete_id, date, row.get("minHeartRate"), row.get("maxHeartRate"), row.get("restingHeartRate")),
        )
        count += 1
    conn.commit()
    return count


def ingest_body_battery(conn: sqlite3.Connection, athlete_id: str, data: list) -> int:
    count = 0
    for row in data:
        if row is None:
            continue
        conn.execute(
            """
            INSERT INTO body_battery (athlete_id, date, charged, drained)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
                charged=excluded.charged, drained=excluded.drained
            """,
            (athlete_id, row.get("date"), row.get("charged"), row.get("drained")),
        )
        count += 1
    conn.commit()
    return count


def ingest_training_readiness(conn: sqlite3.Connection, athlete_id: str, data: dict) -> int:
    count = 0
    for date, entries in data.items():
        if not entries:
            continue
        entry = entries[0] if isinstance(entries, list) else entries
        conn.execute(
            """
            INSERT INTO training_readiness (athlete_id, date, score, level, feedback_short)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
                score=excluded.score, level=excluded.level, feedback_short=excluded.feedback_short
            """,
            (
                athlete_id,
                entry.get("calendarDate", date),
                entry.get("score"),
                entry.get("level"),
                entry.get("feedbackShort"),
            ),
        )
        count += 1
    conn.commit()
    return count


def ingest_vo2max_from_training_status(conn: sqlite3.Connection, athlete_id: str, data: dict) -> int:
    seen = set()
    count = 0
    for _, row in data.items():
        if not row:
            continue
        generic = (row.get("mostRecentVO2Max") or {}).get("generic") or {}
        date = generic.get("calendarDate")
        value = generic.get("vo2MaxValue")
        if date and value and date not in seen:
            seen.add(date)
            conn.execute(
                """
                INSERT INTO vo2max (athlete_id, date, vo2max)
                VALUES (?, ?, ?)
                ON CONFLICT(athlete_id, date) DO UPDATE SET vo2max=excluded.vo2max
                """,
                (athlete_id, date, value),
            )
            count += 1
    conn.commit()
    return count


def run_ingest(athlete_id: str, display_name: str, output_dir: Path) -> None:
    init_db()
    conn = get_conn()

    default_panels = [
        "GoalBanner", "HeroRow", "WeekVolume", "TempoTrend",
        "ZoneDistribution", "VO2MaxTrend", "RecentRuns",
        "DailyStats", "RecoveryStrip", "CoachCard",
    ]
    upsert_athlete(conn, athlete_id, display_name, default_panels)

    def load(fname):
        p = output_dir / fname
        return json.loads(p.read_text()) if p.exists() else None

    activities = load("activities.json") or []
    n_act = ingest_activities(conn, athlete_id, [a for a in activities if (a.get("activityType") or {}).get("typeKey") == "running"])
    print(f"  activities (runs): {n_act}")

    stats = load("stats.json") or {}
    print(f"  daily_stats: {ingest_daily_stats(conn, athlete_id, stats)}")

    heart_rates = load("heart_rates.json") or {}
    print(f"  daily_heart_rates: {ingest_daily_heart_rates(conn, athlete_id, heart_rates)}")

    body_battery = load("body_battery.json") or []
    print(f"  body_battery: {ingest_body_battery(conn, athlete_id, body_battery)}")

    tr = load("training_readiness.json") or {}
    print(f"  training_readiness: {ingest_training_readiness(conn, athlete_id, tr)}")

    ts = load("training_status.json") or {}
    print(f"  vo2max: {ingest_vo2max_from_training_status(conn, athlete_id, ts)}")

    print(f"\nDone → {DB_PATH}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--athlete", default="vriendin")
    parser.add_argument("--name", default="Vriendin")
    args = parser.parse_args()

    output_dir = Path("output") / args.athlete
    if not output_dir.exists():
        print(f"ERROR: {output_dir} niet gevonden")
        sys.exit(1)

    print(f"Ingesting {args.athlete}...")
    run_ingest(args.athlete, args.name, output_dir)
```

- [ ] **Stap 4: Draai alle ingest-tests — verwacht alle PASS**

```bash
python -m pytest tests/test_ingest.py -v
```

Verwacht: 7× PASSED

- [ ] **Stap 5: Draai echte ingest**

```bash
cd ~/Documents/garmin-coach
source .venv/bin/activate
python ingest.py --athlete vriendin --name "Vriendin"
```

Verwacht output (aantallen afhankelijk van data):
```
Ingesting vriendin...
  activities (runs): 2
  daily_stats: 7
  daily_heart_rates: 7
  body_battery: 7
  training_readiness: 5
  vo2max: 1

Done → .../garmin_coach.db
```

- [ ] **Stap 6: Commit**

```bash
git add ingest.py tests/test_ingest.py
git commit -m "feat: ingest JSON → SQLite with upsert per athlete"
```

---

## Task 3: FastAPI — api/main.py + api/routes.py

**Files:**
- Create: `api/__init__.py`
- Create: `api/main.py`
- Create: `api/routes.py`
- Create: `tests/test_api.py`

- [ ] **Stap 1: Schrijf API-tests (failing)**

```python
# tests/test_api.py
import json
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

from db import get_conn, init_db
from ingest import (
    ingest_activities, ingest_training_readiness,
    ingest_vo2max_from_training_status, ingest_daily_stats,
    ingest_body_battery, upsert_athlete,
)

# Patch DB_PATH before importing app
import db as db_module
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DB = Path(_tmp.name)
_tmp.close()
db_module.DB_PATH = TEST_DB

from api.main import app  # import AFTER patching

@pytest.fixture(autouse=True)
def setup_db():
    init_db(TEST_DB)
    conn = get_conn(TEST_DB)
    upsert_athlete(conn, "vriendin", "Vriendin", ["GoalBanner", "HeroRow"])
    ingest_activities(conn, "vriendin", [
        {
            "activityId": 1001,
            "activityName": "Run A",
            "startTimeLocal": "2026-06-20 08:00:00",
            "activityType": {"typeKey": "running"},
            "distance": 8000.0,
            "duration": 2400.0,
            "averageSpeed": 3.33,
            "averageHR": 155.0,
            "maxHR": 170.0,
            "hrTimeInZone_1": 120.0, "hrTimeInZone_2": 600.0,
            "hrTimeInZone_3": 1200.0, "hrTimeInZone_4": 400.0, "hrTimeInZone_5": 80.0,
            "aerobicTrainingEffect": 3.5, "anaerobicTrainingEffect": 0.2,
            "averageRunningCadenceInStepsPerMinute": 168.0,
        }
    ])
    ingest_training_readiness(conn, "vriendin", {
        "2026-06-20": [{"calendarDate": "2026-06-20", "score": 78, "level": "HIGH", "feedbackShort": "WELL_RECOVERED"}]
    })
    ingest_vo2max_from_training_status(conn, "vriendin", {
        "2026-06-20": {"mostRecentVO2Max": {"generic": {"calendarDate": "2026-06-16", "vo2MaxValue": 49.0}}}
    })
    ingest_daily_stats(conn, "vriendin", {
        "2026-06-20": {"totalSteps": 9000, "activeKilocalories": 500.0, "totalKilocalories": 2100.0}
    })
    ingest_body_battery(conn, "vriendin", [
        {"date": "2026-06-20", "charged": 70.0, "drained": 35.0}
    ])
    yield
    # cleanup between tests via truncate
    conn.executescript("""
        DELETE FROM activities; DELETE FROM training_readiness;
        DELETE FROM vo2max; DELETE FROM daily_stats; DELETE FROM body_battery;
        DELETE FROM athletes;
    """)
    conn.commit()


client = TestClient(app)


def test_get_athletes():
    r = client.get("/api/athletes")
    assert r.status_code == 200
    data = r.json()
    assert any(a["id"] == "vriendin" for a in data)


def test_get_hero():
    r = client.get("/api/athlete/vriendin/hero")
    assert r.status_code == 200
    d = r.json()
    assert d["latest_vo2max"]["value"] == 49.0
    assert d["latest_readiness"]["score"] == 78


def test_get_runs():
    r = client.get("/api/athlete/vriendin/runs")
    assert r.status_code == 200
    runs = r.json()
    assert len(runs) == 1
    assert runs[0]["distance_km"] == pytest.approx(8.0)


def test_get_weekly_volume():
    r = client.get("/api/athlete/vriendin/weekly_volume")
    assert r.status_code == 200
    weeks = r.json()
    assert len(weeks) >= 1
    assert weeks[0]["km"] == pytest.approx(8.0)


def test_get_zone_distribution():
    r = client.get("/api/athlete/vriendin/zone_distribution")
    assert r.status_code == 200
    z = r.json()
    assert z["z3"] == pytest.approx(1200.0)


def test_get_vo2max_trend():
    r = client.get("/api/athlete/vriendin/vo2max_trend")
    assert r.status_code == 200
    trend = r.json()
    assert trend[0]["vo2max"] == 49.0


def test_get_daily_stats():
    r = client.get("/api/athlete/vriendin/daily_stats")
    assert r.status_code == 200
    rows = r.json()
    assert rows[0]["steps"] == 9000


def test_athlete_not_found():
    r = client.get("/api/athlete/nonexistent/hero")
    assert r.status_code == 404
```

- [ ] **Stap 2: Draai — verwacht FAIL (importfout)**

```bash
python -m pytest tests/test_api.py -v 2>&1 | head -10
```

- [ ] **Stap 3: Schrijf api/__init__.py**

```python
# leeg
```

- [ ] **Stap 4: Schrijf api/routes.py**

```python
from __future__ import annotations
import json
import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException

import db as db_module

router = APIRouter(prefix="/api")


def _conn() -> sqlite3.Connection:
    return db_module.get_conn(db_module.DB_PATH)


def _athlete_or_404(conn: sqlite3.Connection, athlete_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM athletes WHERE id=?", (athlete_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Atleet '{athlete_id}' niet gevonden")
    return row


# ── Athletes ──────────────────────────────────────────────────────────────────

@router.get("/athletes")
def get_athletes() -> list[dict[str, Any]]:
    conn = _conn()
    rows = conn.execute("SELECT id, display_name, panels_config FROM athletes ORDER BY id").fetchall()
    return [
        {"id": r["id"], "display_name": r["display_name"], "panels": json.loads(r["panels_config"])}
        for r in rows
    ]


# ── Hero ──────────────────────────────────────────────────────────────────────

@router.get("/athlete/{athlete_id}/hero")
def get_hero(athlete_id: str) -> dict[str, Any]:
    conn = _conn()
    _athlete_or_404(conn, athlete_id)

    readiness = conn.execute(
        "SELECT score, level, feedback_short FROM training_readiness WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
        (athlete_id,),
    ).fetchone()

    vo2 = conn.execute(
        "SELECT date, vo2max FROM vo2max WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
        (athlete_id,),
    ).fetchone()

    # Predicted 16.1 km pace: avg of last 3 runs (seconds per km)
    runs = conn.execute(
        """SELECT duration_s, distance_m FROM activities
           WHERE athlete_id=? AND type_key='running' AND distance_m > 0
           ORDER BY date DESC LIMIT 3""",
        (athlete_id,),
    ).fetchall()

    predicted_time_s = None
    if runs:
        pace_list = [r["duration_s"] / (r["distance_m"] / 1000) for r in runs]
        avg_pace = sum(pace_list) / len(pace_list)
        predicted_time_s = avg_pace * 16.1

    return {
        "latest_readiness": (
            {"score": readiness["score"], "level": readiness["level"], "feedback": readiness["feedback_short"]}
            if readiness else None
        ),
        "latest_vo2max": (
            {"date": vo2["date"], "value": vo2["vo2max"]}
            if vo2 else None
        ),
        "predicted_16k_pace_s_per_km": (sum(p for p in [r["duration_s"]/(r["distance_m"]/1000) for r in runs])/len(runs)) if runs else None,
        "predicted_16k_time_s": predicted_time_s,
    }


# ── Runs ─────────────────────────────────────────────────────────────────────

@router.get("/athlete/{athlete_id}/runs")
def get_runs(athlete_id: str, limit: int = 20) -> list[dict[str, Any]]:
    conn = _conn()
    _athlete_or_404(conn, athlete_id)
    rows = conn.execute(
        """SELECT date, name, distance_m, duration_s, avg_hr, max_hr,
                  hr_zone_1_s, hr_zone_2_s, hr_zone_3_s, hr_zone_4_s, hr_zone_5_s,
                  avg_cadence, aerobic_effect
           FROM activities
           WHERE athlete_id=? AND type_key='running'
           ORDER BY date DESC LIMIT ?""",
        (athlete_id, limit),
    ).fetchall()
    result = []
    for r in rows:
        dist_km = (r["distance_m"] or 0) / 1000
        dur_s = r["duration_s"] or 0
        pace = dur_s / dist_km if dist_km > 0 else None
        result.append({
            "date": r["date"],
            "name": r["name"],
            "distance_km": round(dist_km, 2),
            "duration_s": dur_s,
            "avg_pace_s_per_km": round(pace, 1) if pace else None,
            "avg_hr": r["avg_hr"],
            "max_hr": r["max_hr"],
            "avg_cadence": r["avg_cadence"],
            "aerobic_effect": r["aerobic_effect"],
            "zones": {
                "z1": r["hr_zone_1_s"], "z2": r["hr_zone_2_s"],
                "z3": r["hr_zone_3_s"], "z4": r["hr_zone_4_s"], "z5": r["hr_zone_5_s"],
            },
        })
    return result


# ── Weekly Volume ─────────────────────────────────────────────────────────────

@router.get("/athlete/{athlete_id}/weekly_volume")
def get_weekly_volume(athlete_id: str) -> list[dict[str, Any]]:
    conn = _conn()
    _athlete_or_404(conn, athlete_id)
    rows = conn.execute(
        """SELECT strftime('%Y-W%W', date) AS week, SUM(distance_m)/1000.0 AS km
           FROM activities WHERE athlete_id=? AND type_key='running'
           GROUP BY week ORDER BY week""",
        (athlete_id,),
    ).fetchall()
    return [{"week": r["week"], "km": round(r["km"], 2)} for r in rows]


# ── Tempo Trend ───────────────────────────────────────────────────────────────

@router.get("/athlete/{athlete_id}/tempo_trend")
def get_tempo_trend(athlete_id: str) -> list[dict[str, Any]]:
    conn = _conn()
    _athlete_or_404(conn, athlete_id)
    rows = conn.execute(
        """SELECT date, duration_s, distance_m FROM activities
           WHERE athlete_id=? AND type_key='running' AND distance_m > 0
           ORDER BY date""",
        (athlete_id,),
    ).fetchall()
    result = []
    for r in rows:
        dist_km = r["distance_m"] / 1000
        pace = r["duration_s"] / dist_km
        result.append({"date": r["date"], "avg_pace_s_per_km": round(pace, 1)})
    return result


# ── Zone Distribution ─────────────────────────────────────────────────────────

@router.get("/athlete/{athlete_id}/zone_distribution")
def get_zone_distribution(athlete_id: str) -> dict[str, Any]:
    conn = _conn()
    _athlete_or_404(conn, athlete_id)
    row = conn.execute(
        """SELECT SUM(hr_zone_1_s) z1, SUM(hr_zone_2_s) z2, SUM(hr_zone_3_s) z3,
                  SUM(hr_zone_4_s) z4, SUM(hr_zone_5_s) z5
           FROM activities WHERE athlete_id=? AND type_key='running'""",
        (athlete_id,),
    ).fetchone()
    return {
        "z1": row["z1"] or 0, "z2": row["z2"] or 0, "z3": row["z3"] or 0,
        "z4": row["z4"] or 0, "z5": row["z5"] or 0,
    }


# ── VO2max Trend ──────────────────────────────────────────────────────────────

@router.get("/athlete/{athlete_id}/vo2max_trend")
def get_vo2max_trend(athlete_id: str) -> list[dict[str, Any]]:
    conn = _conn()
    _athlete_or_404(conn, athlete_id)
    rows = conn.execute(
        "SELECT date, vo2max FROM vo2max WHERE athlete_id=? ORDER BY date",
        (athlete_id,),
    ).fetchall()
    return [{"date": r["date"], "vo2max": r["vo2max"]} for r in rows]


# ── Daily Stats ───────────────────────────────────────────────────────────────

@router.get("/athlete/{athlete_id}/daily_stats")
def get_daily_stats(athlete_id: str, days: int = 14) -> list[dict[str, Any]]:
    conn = _conn()
    _athlete_or_404(conn, athlete_id)
    rows = conn.execute(
        """SELECT date, steps, active_calories FROM daily_stats
           WHERE athlete_id=? ORDER BY date DESC LIMIT ?""",
        (athlete_id, days),
    ).fetchall()
    return [{"date": r["date"], "steps": r["steps"], "active_calories": r["active_calories"]} for r in rows]


# ── Recovery ──────────────────────────────────────────────────────────────────

@router.get("/athlete/{athlete_id}/recovery")
def get_recovery(athlete_id: str, days: int = 7) -> list[dict[str, Any]]:
    conn = _conn()
    _athlete_or_404(conn, athlete_id)
    rows = conn.execute(
        """SELECT bb.date, bb.charged, bb.drained, hr.min_hr, hr.max_hr
           FROM body_battery bb
           LEFT JOIN daily_heart_rates hr ON hr.athlete_id=bb.athlete_id AND hr.date=bb.date
           WHERE bb.athlete_id=? ORDER BY bb.date DESC LIMIT ?""",
        (athlete_id, days),
    ).fetchall()
    return [
        {
            "date": r["date"],
            "body_battery_charged": r["charged"],
            "body_battery_drained": r["drained"],
            "hr_min": r["min_hr"],
            "hr_max": r["max_hr"],
        }
        for r in rows
    ]
```

- [ ] **Stap 5: Schrijf api/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import DB_PATH, init_db
from api.routes import router

app = FastAPI(title="Garmin Coach API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db(DB_PATH)


app.include_router(router)
```

- [ ] **Stap 6: Draai alle tests — verwacht alle PASS**

```bash
pip install fastapi uvicorn httpx
python -m pytest tests/ -v
```

Verwacht: 13+ × PASSED

- [ ] **Stap 7: Handmatig verifiëren**

```bash
uvicorn api.main:app --reload --port 8000
# In ander terminal:
curl http://localhost:8000/api/athletes | python3 -m json.tool
curl http://localhost:8000/api/athlete/vriendin/hero | python3 -m json.tool
```

Ctrl-C om uvicorn te stoppen.

- [ ] **Stap 8: Commit**

```bash
git add api/ tests/test_api.py
git commit -m "feat: FastAPI with all dashboard endpoints"
```

---

## Task 4: Vite + React scaffold + dark thema

**Files:**
- Create: `dashboard/package.json`
- Create: `dashboard/vite.config.js`
- Create: `dashboard/index.html`
- Create: `dashboard/src/main.jsx`
- Create: `dashboard/src/theme.css`
- Create: `dashboard/src/api.js`
- Create: `dashboard/src/App.jsx`

- [ ] **Stap 1: Init Vite project**

```bash
cd ~/Documents/garmin-coach
npm create vite@latest dashboard -- --template react
cd dashboard
npm install recharts lucide-react
```

- [ ] **Stap 2: Overschrijf vite.config.js (proxy naar API)**

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

- [ ] **Stap 3: Schrijf dashboard/src/theme.css**

```css
:root {
  --bg-base:    #0f1117;
  --bg-card:    #1a1f2e;
  --bg-card2:   #242938;
  --border:     #2d3348;
  --accent:     #6366f1;
  --accent2:    #22d3ee;
  --green:      #22c55e;
  --orange:     #f97316;
  --red:        #ef4444;
  --text-1:     #f1f5f9;
  --text-2:     #94a3b8;
  --text-3:     #64748b;

  /* Zone kleuren */
  --z1: #3b82f6;
  --z2: #22c55e;
  --z3: #f59e0b;
  --z4: #f97316;
  --z5: #ef4444;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg-base);
  color: var(--text-1);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 14px;
  line-height: 1.5;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
}

.label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: var(--text-3);
  margin-bottom: 4px;
}

.no-data {
  color: var(--text-3);
  font-style: italic;
  font-size: 13px;
}
```

- [ ] **Stap 4: Schrijf dashboard/src/api.js**

```js
const BASE = '/api'

async function get(path) {
  const r = await fetch(BASE + path)
  if (!r.ok) throw new Error(`${r.status} ${path}`)
  return r.json()
}

export const api = {
  athletes:       () => get('/athletes'),
  hero:           (id) => get(`/athlete/${id}/hero`),
  runs:           (id) => get(`/athlete/${id}/runs`),
  weeklyVolume:   (id) => get(`/athlete/${id}/weekly_volume`),
  tempoTrend:     (id) => get(`/athlete/${id}/tempo_trend`),
  zoneDist:       (id) => get(`/athlete/${id}/zone_distribution`),
  vo2maxTrend:    (id) => get(`/athlete/${id}/vo2max_trend`),
  dailyStats:     (id) => get(`/athlete/${id}/daily_stats?days=14`),
  recovery:       (id) => get(`/athlete/${id}/recovery?days=7`),
}
```

- [ ] **Stap 5: Schrijf dashboard/src/App.jsx**

```jsx
import { useState, useEffect } from 'react'
import '../src/theme.css'
import { api } from './api'
import GoalBanner from './components/GoalBanner'
import HeroRow from './components/HeroRow'
import WeekVolume from './components/WeekVolume'
import TempoTrend from './components/TempoTrend'
import ZoneDistribution from './components/ZoneDistribution'
import VO2MaxTrend from './components/VO2MaxTrend'
import RecentRuns from './components/RecentRuns'
import DailyStats from './components/DailyStats'
import RecoveryStrip from './components/RecoveryStrip'
import CoachCard from './components/CoachCard'

const PANEL_COMPONENTS = {
  GoalBanner, HeroRow, WeekVolume, TempoTrend, ZoneDistribution,
  VO2MaxTrend, RecentRuns, DailyStats, RecoveryStrip, CoachCard,
}

function AthleteTab({ athleteId }) {
  const [data, setData] = useState({})
  const [panels, setPanels] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [athletes, hero, runs, weekVol, tempo, zones, vo2, daily, recovery] = await Promise.all([
          api.athletes(),
          api.hero(athleteId),
          api.runs(athleteId),
          api.weeklyVolume(athleteId),
          api.tempoTrend(athleteId),
          api.zoneDist(athleteId),
          api.vo2maxTrend(athleteId),
          api.dailyStats(athleteId),
          api.recovery(athleteId),
        ])
        const athlete = athletes.find(a => a.id === athleteId) || {}
        setPanels(athlete.panels || Object.keys(PANEL_COMPONENTS))
        setData({ hero, runs, weekVol, tempo, zones, vo2, daily, recovery })
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [athleteId])

  if (loading) return <div style={{ padding: 40, color: 'var(--text-2)' }}>Laden...</div>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {panels.map(name => {
        const Comp = PANEL_COMPONENTS[name]
        if (!Comp) return null
        return <Comp key={name} athleteId={athleteId} data={data} />
      })}
    </div>
  )
}

export default function App() {
  const [athletes, setAthletes] = useState([])
  const [activeId, setActiveId] = useState(null)

  useEffect(() => {
    api.athletes().then(list => {
      setAthletes(list)
      if (list.length > 0) setActiveId(list[0].id)
    })
  }, [])

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      {/* Header */}
      <div style={{
        background: 'var(--bg-card)', borderBottom: '1px solid var(--border)',
        padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 24,
      }}>
        <span style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-1)' }}>
          🏃 Garmin Coach
        </span>
        <div style={{ display: 'flex', gap: 8 }}>
          {athletes.map(a => (
            <button
              key={a.id}
              onClick={() => setActiveId(a.id)}
              style={{
                padding: '6px 14px', borderRadius: 8, border: 'none', cursor: 'pointer',
                background: activeId === a.id ? 'var(--accent)' : 'var(--bg-card2)',
                color: 'var(--text-1)', fontSize: 13, fontWeight: 600,
              }}
            >
              {a.display_name}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '24px 16px' }}>
        {activeId && <AthleteTab athleteId={activeId} />}
      </div>
    </div>
  )
}
```

- [ ] **Stap 6: Schrijf dashboard/src/main.jsx**

```jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './theme.css'
import App from './App'

createRoot(document.getElementById('root')).render(
  <StrictMode><App /></StrictMode>
)
```

- [ ] **Stap 7: Update dashboard/index.html (title)**

In `dashboard/index.html`, verander de `<title>` regel naar:
```html
<title>Garmin Coach</title>
```

- [ ] **Stap 8: Commit**

```bash
cd ~/Documents/garmin-coach
git add dashboard/
git commit -m "feat: Vite+React scaffold with dark theme and tab routing"
```

---

## Task 5: GoalBanner component

**Files:**
- Create: `dashboard/src/components/GoalBanner.jsx`

Het component toont: aftelling tot Dam tot Damloop (20 sep 2026), huidige trainingsfase, en fase-tijdlijn.

Fasen:
- **Basis**: t/m 10 aug 2026
- **Opbouw**: 11 aug – 7 sep 2026
- **Piek**: 8 sep – 13 sep 2026
- **Taper**: 14 sep – 19 sep 2026
- **Race**: 20 sep 2026

- [ ] **Stap 1: Schrijf GoalBanner.jsx**

```jsx
const RACE_DATE = new Date('2026-09-20T00:00:00')

const PHASES = [
  { name: 'Basis',  start: new Date('2026-06-30'), end: new Date('2026-08-10'), color: '#3b82f6' },
  { name: 'Opbouw', start: new Date('2026-08-11'), end: new Date('2026-09-07'), color: '#22c55e' },
  { name: 'Piek',   start: new Date('2026-09-08'), end: new Date('2026-09-13'), color: '#f97316' },
  { name: 'Taper',  start: new Date('2026-09-14'), end: new Date('2026-09-19'), color: '#a78bfa' },
  { name: 'Race',   start: new Date('2026-09-20'), end: new Date('2026-09-20'), color: '#ef4444' },
]

function getCurrentPhase() {
  const now = new Date()
  return PHASES.find(p => now >= p.start && now <= p.end) || PHASES[0]
}

function daysUntilRace() {
  const now = new Date()
  const diff = RACE_DATE - now
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)))
}

export default function GoalBanner() {
  const days = daysUntilRace()
  const currentPhase = getCurrentPhase()
  const totalDays = (RACE_DATE - PHASES[0].start) / (1000 * 60 * 60 * 24)
  const elapsed = (new Date() - PHASES[0].start) / (1000 * 60 * 60 * 24)
  const progress = Math.min(100, Math.max(0, (elapsed / totalDays) * 100))

  return (
    <div className="card" style={{ borderLeft: `4px solid ${currentPhase.color}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div className="label">Doel</div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>Dam tot Damloop — 20 sep 2026 · 16,1 km</div>
          <div style={{ marginTop: 4, color: 'var(--text-2)' }}>
            Fase: <span style={{ color: currentPhase.color, fontWeight: 600 }}>{currentPhase.name}</span>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 40, fontWeight: 800, color: currentPhase.color, lineHeight: 1 }}>{days}</div>
          <div className="label">dagen te gaan</div>
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ marginTop: 16 }}>
        <div style={{ height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${progress}%`, background: currentPhase.color, borderRadius: 3, transition: 'width .3s' }} />
        </div>
      </div>

      {/* Phase timeline */}
      <div style={{ display: 'flex', gap: 4, marginTop: 12 }}>
        {PHASES.map(p => (
          <div key={p.name} style={{
            flex: p.name === 'Race' ? '0 0 auto' : 1,
            padding: '4px 8px', borderRadius: 6, textAlign: 'center', fontSize: 11,
            background: p.name === currentPhase.name ? p.color : 'var(--bg-card2)',
            color: p.name === currentPhase.name ? '#fff' : 'var(--text-3)',
            fontWeight: p.name === currentPhase.name ? 700 : 400,
          }}>
            {p.name}
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Stap 2: Commit**

```bash
git add dashboard/src/components/GoalBanner.jsx
git commit -m "feat: GoalBanner with countdown and phase timeline"
```

---

## Task 6: HeroRow component

**Files:**
- Create: `dashboard/src/components/HeroRow.jsx`

Toont: voorspelde 16,1 km tijd (hh:mm:ss), training readiness ring (SVG), VO2max.

- [ ] **Stap 1: Schrijf HeroRow.jsx**

```jsx
function formatTime(seconds) {
  if (!seconds) return '--:--:--'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  return h > 0
    ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    : `${m}:${String(s).padStart(2, '0')}`
}

function formatPace(secsPerKm) {
  if (!secsPerKm) return '--'
  const m = Math.floor(secsPerKm / 60)
  const s = Math.floor(secsPerKm % 60)
  return `${m}:${String(s).padStart(2, '0')} /km`
}

function ReadinessRing({ score }) {
  const pct = (score || 0) / 100
  const r = 40
  const circ = 2 * Math.PI * r
  const dash = circ * pct
  const color = score >= 70 ? '#22c55e' : score >= 40 ? '#f97316' : '#ef4444'

  return (
    <svg width={100} height={100} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={50} cy={50} r={r} fill="none" stroke="var(--border)" strokeWidth={8} />
      <circle
        cx={50} cy={50} r={r} fill="none"
        stroke={color} strokeWidth={8}
        strokeDasharray={`${dash} ${circ}`}
        strokeLinecap="round"
      />
      <text
        x={50} y={55} textAnchor="middle"
        style={{ fontSize: 20, fontWeight: 700, fill: color, transform: 'rotate(90deg)', transformOrigin: '50px 50px' }}
      >
        {score ?? '--'}
      </text>
    </svg>
  )
}

export default function HeroRow({ data }) {
  const { hero } = data
  if (!hero) return null

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
      {/* Voorspelde tijd */}
      <div className="card" style={{ textAlign: 'center' }}>
        <div className="label">Voorspelde 16,1 km tijd</div>
        <div style={{ fontSize: 36, fontWeight: 800, color: 'var(--accent)', lineHeight: 1.1, marginTop: 8 }}>
          {formatTime(hero.predicted_16k_time_s)}
        </div>
        <div style={{ color: 'var(--text-2)', marginTop: 4, fontSize: 13 }}>
          {formatPace(hero.predicted_16k_pace_s_per_km)}
        </div>
        {!hero.predicted_16k_time_s && (
          <div className="no-data" style={{ marginTop: 8 }}>Meer runs nodig</div>
        )}
      </div>

      {/* Training Readiness */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <div className="label">Training Readiness</div>
        <ReadinessRing score={hero.latest_readiness?.score} />
        <div style={{ color: 'var(--text-2)', fontSize: 12, marginTop: 4 }}>
          {hero.latest_readiness?.level?.replace(/_/g, ' ') ?? 'Geen data'}
        </div>
      </div>

      {/* VO2max */}
      <div className="card" style={{ textAlign: 'center' }}>
        <div className="label">VO₂max</div>
        <div style={{ fontSize: 48, fontWeight: 800, color: 'var(--accent2)', lineHeight: 1, marginTop: 8 }}>
          {hero.latest_vo2max?.value ?? '--'}
        </div>
        <div style={{ color: 'var(--text-2)', fontSize: 12, marginTop: 4 }}>
          {hero.latest_vo2max?.date ? `Gemeten ${hero.latest_vo2max.date}` : 'Geen data'}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Stap 2: Commit**

```bash
git add dashboard/src/components/HeroRow.jsx
git commit -m "feat: HeroRow with predicted time, readiness ring, VO2max"
```

---

## Task 7: WeekVolume + TempoTrend charts

**Files:**
- Create: `dashboard/src/components/WeekVolume.jsx`
- Create: `dashboard/src/components/TempoTrend.jsx`

- [ ] **Stap 1: Schrijf WeekVolume.jsx**

```jsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

export default function WeekVolume({ data }) {
  const rows = data.weekVol || []
  if (rows.length === 0) return (
    <div className="card"><div className="label">Weekvolume (km)</div><div className="no-data">Geen data</div></div>
  )
  const max = Math.max(...rows.map(r => r.km))

  return (
    <div className="card">
      <div className="label" style={{ marginBottom: 12 }}>Weekvolume (km)</div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={rows} margin={{ top: 4, right: 8, bottom: 4, left: -16 }}>
          <XAxis dataKey="week" tick={{ fill: 'var(--text-3)', fontSize: 11 }} />
          <YAxis tick={{ fill: 'var(--text-3)', fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: 'var(--bg-card2)', border: '1px solid var(--border)', borderRadius: 8 }}
            labelStyle={{ color: 'var(--text-2)' }}
            formatter={v => [`${v.toFixed(1)} km`]}
          />
          <Bar dataKey="km" radius={[4, 4, 0, 0]}>
            {rows.map((r, i) => (
              <Cell key={i} fill={r.km === max ? 'var(--accent)' : 'var(--bg-card2)'} stroke="var(--border)" />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Stap 2: Schrijf TempoTrend.jsx**

```jsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

function paceLabel(secsPerKm) {
  if (!secsPerKm) return '--'
  const m = Math.floor(secsPerKm / 60)
  const s = Math.floor(secsPerKm % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

export default function TempoTrend({ data }) {
  const rows = data.tempo || []
  if (rows.length === 0) return (
    <div className="card"><div className="label">Tempo-trend</div><div className="no-data">Geen data</div></div>
  )
  // Invert Y axis: lower pace = faster = better (show at top)
  const avg = rows.reduce((a, r) => a + r.avg_pace_s_per_km, 0) / rows.length

  return (
    <div className="card">
      <div className="label" style={{ marginBottom: 12 }}>Tempo-trend (min/km)</div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={rows} margin={{ top: 4, right: 8, bottom: 4, left: -16 }}>
          <XAxis dataKey="date" tick={{ fill: 'var(--text-3)', fontSize: 11 }} />
          <YAxis
            reversed
            tickFormatter={paceLabel}
            tick={{ fill: 'var(--text-3)', fontSize: 11 }}
            domain={['dataMin - 10', 'dataMax + 10']}
          />
          <Tooltip
            contentStyle={{ background: 'var(--bg-card2)', border: '1px solid var(--border)', borderRadius: 8 }}
            formatter={(v) => [paceLabel(v) + ' /km', 'Tempo']}
          />
          <ReferenceLine y={avg} stroke="var(--text-3)" strokeDasharray="4 2" />
          <Line
            type="monotone" dataKey="avg_pace_s_per_km"
            stroke="var(--accent)" strokeWidth={2} dot={{ fill: 'var(--accent)', r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Stap 3: Commit**

```bash
git add dashboard/src/components/WeekVolume.jsx dashboard/src/components/TempoTrend.jsx
git commit -m "feat: WeekVolume and TempoTrend charts"
```

---

## Task 8: ZoneDistribution + VO2MaxTrend

**Files:**
- Create: `dashboard/src/components/ZoneDistribution.jsx`
- Create: `dashboard/src/components/VO2MaxTrend.jsx`

- [ ] **Stap 1: Schrijf ZoneDistribution.jsx**

80/20-doel: z1+z2 ≥ 80%, z3-z5 ≤ 20%.

```jsx
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const ZONE_LABELS = ['Z1 Herstel', 'Z2 Aerob', 'Z3 Tempo', 'Z4 Drempel', 'Z5 Max']
const ZONE_COLORS = ['var(--z1)', 'var(--z2)', 'var(--z3)', 'var(--z4)', 'var(--z5)']

function toMinutes(s) { return Math.round((s || 0) / 60) }

export default function ZoneDistribution({ data }) {
  const z = data.zones || {}
  const entries = [
    { name: ZONE_LABELS[0], value: toMinutes(z.z1) },
    { name: ZONE_LABELS[1], value: toMinutes(z.z2) },
    { name: ZONE_LABELS[2], value: toMinutes(z.z3) },
    { name: ZONE_LABELS[3], value: toMinutes(z.z4) },
    { name: ZONE_LABELS[4], value: toMinutes(z.z5) },
  ].filter(e => e.value > 0)

  const total = entries.reduce((a, e) => a + e.value, 0)
  const easyPct = total > 0 ? Math.round(((toMinutes(z.z1) + toMinutes(z.z2)) / total) * 100) : 0

  if (total === 0) return (
    <div className="card"><div className="label">Intensiteitsverdeling (hartslagzones)</div><div className="no-data">Geen data</div></div>
  )

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div className="label">Intensiteitsverdeling (hartslagzones)</div>
        <div style={{ fontSize: 12, color: easyPct >= 80 ? 'var(--green)' : 'var(--orange)' }}>
          {easyPct}% laag · doel: 80%
        </div>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie data={entries} cx="50%" cy="50%" outerRadius={80} dataKey="value">
            {entries.map((_, i) => <Cell key={i} fill={ZONE_COLORS[i]} />)}
          </Pie>
          <Tooltip
            contentStyle={{ background: 'var(--bg-card2)', border: '1px solid var(--border)', borderRadius: 8 }}
            formatter={(v, name) => [`${v} min`, name]}
          />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12, color: 'var(--text-2)' }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Stap 2: Schrijf VO2MaxTrend.jsx**

```jsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

export default function VO2MaxTrend({ data }) {
  const rows = data.vo2 || []
  if (rows.length === 0) return (
    <div className="card"><div className="label">VO₂max trend</div><div className="no-data">Geen data</div></div>
  )
  const latest = rows[rows.length - 1]?.vo2max

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <div className="label">VO₂max trend</div>
        <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--accent2)' }}>{latest}</div>
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={rows} margin={{ top: 4, right: 8, bottom: 4, left: -16 }}>
          <XAxis dataKey="date" tick={{ fill: 'var(--text-3)', fontSize: 11 }} />
          <YAxis domain={['dataMin - 2', 'dataMax + 2']} tick={{ fill: 'var(--text-3)', fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: 'var(--bg-card2)', border: '1px solid var(--border)', borderRadius: 8 }}
            formatter={(v) => [v, 'VO₂max']}
          />
          <Line type="monotone" dataKey="vo2max" stroke="var(--accent2)" strokeWidth={2} dot={{ fill: 'var(--accent2)', r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Stap 3: Commit**

```bash
git add dashboard/src/components/ZoneDistribution.jsx dashboard/src/components/VO2MaxTrend.jsx
git commit -m "feat: ZoneDistribution (80/20) and VO2MaxTrend charts"
```

---

## Task 9: RecentRuns tabel

**Files:**
- Create: `dashboard/src/components/RecentRuns.jsx`

- [ ] **Stap 1: Schrijf RecentRuns.jsx**

```jsx
function pace(secsPerKm) {
  if (!secsPerKm) return '--'
  const m = Math.floor(secsPerKm / 60)
  const s = Math.floor(secsPerKm % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function duration(s) {
  if (!s) return '--'
  const m = Math.floor(s / 60)
  return `${m} min`
}

export default function RecentRuns({ data }) {
  const runs = (data.runs || []).slice(0, 10)
  if (runs.length === 0) return (
    <div className="card"><div className="label">Recente runs</div><div className="no-data">Geen runs gevonden</div></div>
  )

  return (
    <div className="card">
      <div className="label" style={{ marginBottom: 12 }}>Recente runs</div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ color: 'var(--text-3)', borderBottom: '1px solid var(--border)' }}>
              {['Datum', 'Naam', 'Afstand', 'Duur', 'Tempo', 'Gem HR', 'Aerob.'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 500 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {runs.map((r, i) => (
              <tr key={i} style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-1)' }}>
                <td style={{ padding: '8px 8px', color: 'var(--text-2)' }}>{r.date}</td>
                <td style={{ padding: '8px 8px' }}>{r.name || '—'}</td>
                <td style={{ padding: '8px 8px' }}>{r.distance_km?.toFixed(1)} km</td>
                <td style={{ padding: '8px 8px' }}>{duration(r.duration_s)}</td>
                <td style={{ padding: '8px 8px', color: 'var(--accent)' }}>{pace(r.avg_pace_s_per_km)}</td>
                <td style={{ padding: '8px 8px' }}>{r.avg_hr ? `${Math.round(r.avg_hr)} bpm` : '—'}</td>
                <td style={{ padding: '8px 8px' }}>
                  {r.aerobic_effect != null
                    ? <span style={{ color: r.aerobic_effect >= 3 ? 'var(--green)' : 'var(--text-2)' }}>{r.aerobic_effect.toFixed(1)}</span>
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

- [ ] **Stap 2: Commit**

```bash
git add dashboard/src/components/RecentRuns.jsx
git commit -m "feat: RecentRuns table"
```

---

## Task 10: DailyStats + RecoveryStrip + CoachCard

**Files:**
- Create: `dashboard/src/components/DailyStats.jsx`
- Create: `dashboard/src/components/RecoveryStrip.jsx`
- Create: `dashboard/src/components/CoachCard.jsx`

- [ ] **Stap 1: Schrijf DailyStats.jsx**

```jsx
import { ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'

export default function DailyStats({ data }) {
  const rows = [...(data.daily || [])].reverse()
  if (rows.length === 0) return (
    <div className="card"><div className="label">Stappen & calorieën</div><div className="no-data">Geen data</div></div>
  )

  return (
    <div className="card">
      <div className="label" style={{ marginBottom: 12 }}>Dagelijkse stappen & actieve calorieën</div>
      <ResponsiveContainer width="100%" height={200}>
        <ComposedChart data={rows} margin={{ top: 4, right: 8, bottom: 4, left: -16 }}>
          <XAxis dataKey="date" tick={{ fill: 'var(--text-3)', fontSize: 11 }} />
          <YAxis yAxisId="steps" tick={{ fill: 'var(--text-3)', fontSize: 11 }} />
          <YAxis yAxisId="cal" orientation="right" tick={{ fill: 'var(--text-3)', fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: 'var(--bg-card2)', border: '1px solid var(--border)', borderRadius: 8 }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-2)' }} />
          <Bar yAxisId="steps" dataKey="steps" name="Stappen" fill="var(--accent)" opacity={0.7} radius={[3,3,0,0]} />
          <Line yAxisId="cal" type="monotone" dataKey="active_calories" name="Act. kcal"
            stroke="var(--orange)" strokeWidth={2} dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Stap 2: Schrijf RecoveryStrip.jsx**

Body battery alleen beschikbaar op run-dagen (horloge alleen tijdens runs). Toont "geen data" netjes.

```jsx
export default function RecoveryStrip({ data }) {
  const rows = [...(data.recovery || [])].reverse()

  return (
    <div className="card">
      <div className="label" style={{ marginBottom: 12 }}>Herstel (body battery)</div>
      {rows.length === 0 ? (
        <div className="no-data">Geen hersteldata — horloge draagt ze alleen tijdens runs</div>
      ) : (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {rows.map(r => {
            const hasData = r.body_battery_charged != null || r.body_battery_drained != null
            return (
              <div key={r.date} className="card" style={{
                flex: '1 1 120px', minWidth: 100, background: 'var(--bg-card2)',
                textAlign: 'center', padding: 12,
              }}>
                <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 4 }}>{r.date}</div>
                {hasData ? (
                  <>
                    <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--green)' }}>
                      +{r.body_battery_charged?.toFixed(0) ?? '?'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--red)' }}>
                      −{r.body_battery_drained?.toFixed(0) ?? '?'}
                    </div>
                    {r.hr_min && (
                      <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 4 }}>
                        HR {r.hr_min}–{r.hr_max}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="no-data" style={{ fontSize: 12 }}>geen data</div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Stap 3: Schrijf CoachCard.jsx**

Statische tekst, duidelijk gemarkeerd als fase-2 placeholder.

```jsx
export default function CoachCard() {
  return (
    <div className="card" style={{ borderLeft: '4px solid var(--accent)', opacity: 0.85 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div className="label">AI Coach</div>
        <span style={{
          fontSize: 10, padding: '2px 8px', borderRadius: 12,
          background: 'var(--bg-card2)', color: 'var(--text-3)',
          border: '1px solid var(--border)',
        }}>
          Automatisch in fase 2
        </span>
      </div>
      <div style={{ color: 'var(--text-2)', fontSize: 14, lineHeight: 1.6 }}>
        <p>
          Je bouwt nu een solide base op voor de Dam tot Damloop. Focus op zone 2-runs
          en houd het weekvolume rustig oplopend.
        </p>
        <p style={{ marginTop: 8, color: 'var(--text-3)', fontSize: 13 }}>
          In fase 2 analyseert de coach automatisch je data en schrijft hier elke week
          een persoonlijk trainingsadvies.
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Stap 4: Commit**

```bash
git add dashboard/src/components/DailyStats.jsx dashboard/src/components/RecoveryStrip.jsx dashboard/src/components/CoachCard.jsx
git commit -m "feat: DailyStats, RecoveryStrip, CoachCard panels"
```

---

## Task 11: start.sh + App.jsx data-koppeling fix

**Files:**
- Create: `start.sh`
- Modify: `dashboard/src/App.jsx` (verifieer correcte data-sleutels)

- [ ] **Stap 1: Schrijf start.sh**

```bash
#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Activeer venv
source .venv/bin/activate

# Ingest meest recente data
echo "=== Ingest ==="
python ingest.py --athlete vriendin --name "Vriendin"

# Start API in background
echo "=== API starten op :8000 ==="
uvicorn api.main:app --port 8000 &
API_PID=$!

# Wacht tot API up is
for i in $(seq 1 20); do
  curl -s http://localhost:8000/api/athletes >/dev/null 2>&1 && break
  sleep 0.3
done

# Start dashboard
echo "=== Dashboard starten op :5173 ==="
cd dashboard
npm run dev &
DASH_PID=$!

echo ""
echo "✓ Dashboard: http://localhost:5173"
echo "✓ API:       http://localhost:8000"
echo ""
echo "Ctrl-C om te stoppen."

cleanup() {
  kill "$API_PID" "$DASH_PID" 2>/dev/null
}
trap cleanup EXIT INT TERM
wait
```

- [ ] **Stap 2: Maak executable**

```bash
chmod +x start.sh
```

- [ ] **Stap 3: Verifieer data-sleutels in App.jsx**

In `dashboard/src/App.jsx` worden de API-responses als props doorgegeven als:
```js
setData({ hero, runs, weekVol, tempo, zones, vo2, daily, recovery })
```

Elk component ontvangt `data` en leest:
- GoalBanner: geen data nodig (berekend)
- HeroRow: `data.hero`
- WeekVolume: `data.weekVol`
- TempoTrend: `data.tempo`
- ZoneDistribution: `data.zones`
- VO2MaxTrend: `data.vo2`
- RecentRuns: `data.runs`
- DailyStats: `data.daily`
- RecoveryStrip: `data.recovery`
- CoachCard: geen data nodig

Controleer of alle sleutels kloppen. Zo niet, pas aan.

- [ ] **Stap 4: Commit**

```bash
cd ~/Documents/garmin-coach
git add start.sh
git commit -m "feat: start.sh — one command to ingest + launch API + dashboard"
```

---

## Task 12: End-to-end smoke test

- [ ] **Stap 1: Draai alle tests**

```bash
cd ~/Documents/garmin-coach
source .venv/bin/activate
python -m pytest tests/ -v
```

Verwacht: alle PASSED

- [ ] **Stap 2: Start de applicatie**

```bash
./start.sh
```

- [ ] **Stap 3: Open dashboard**

Open browser: http://localhost:5173

Controleer:
- [ ] Tab "Vriendin" zichtbaar
- [ ] GoalBanner toont aftelling + juiste fase
- [ ] HeroRow toont VO2max 49, readiness score, voorspelde tijd
- [ ] WeekVolume toont bars
- [ ] TempoTrend toont lijn per run
- [ ] ZoneDistribution toont taart
- [ ] VO2MaxTrend toont lijn
- [ ] RecentRuns toont 2 runs
- [ ] DailyStats toont stappen/calorieën
- [ ] RecoveryStrip toont "geen data" of waarden
- [ ] CoachCard toont statische tekst + "fase 2" badge

- [ ] **Stap 4: Final commit**

```bash
git add -A
git commit -m "chore: fase 1 dashboard complete — klaar voor fase 2 AI coach"
```

---

## Notities voor fase 2

- `CoachCard` heeft een duidelijke "fase 2" marker; vervang door `async` coach-call
- `athlete.panels` (JSON in DB) bepaalt welke panels per atleet zichtbaar zijn — atleet "jij" kan andere panels krijgen
- SQLite → Postgres/Supabase: vervang `sqlite3.connect()` in `db.py` met `psycopg2` + zelfde SQL
- `garmin_test_pull.py` is ongewijzigd; `ingest.py` leest zijn output
- Slaap/HRV: kolommen in schema bestaan al; alleen ingest + panels missen nog (ready voor schema-uitbreiding zonder migratie)
