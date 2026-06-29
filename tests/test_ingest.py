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
