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
        "training_load_balance", "activity_splits",
    }
    p.unlink()


def test_activities_has_new_columns():
    p = make_tmp_db()
    conn = get_conn(p)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(activities)").fetchall()}
    for col in ["training_load", "bb_cost", "avg_stride_cm", "avg_gct_ms",
                "avg_vert_osc_mm", "avg_vert_ratio", "aerobic_effect_msg",
                "training_effect_label", "avg_power"]:
        assert col in cols, f"Missing column: {col}"
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
    ingest_training_load_balance,
    ingest_activity_splits,
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


SAMPLE_TRAINING_STATUS_FULL = {
    "2026-06-01": {
        "mostRecentVO2Max": {
            "generic": {"calendarDate": "2026-05-28", "vo2MaxValue": 48.0}
        },
        "mostRecentTrainingStatus": {
            "latestTrainingStatusData": {
                "dev1": {
                    "primaryTrainingDevice": True,
                    "trainingStatusFeedbackPhrase": "MAINTAINING_2",
                    "acuteTrainingLoadDTO": {
                        "acwrPercent": 38,
                        "acwrStatus": "OPTIMAL",
                        "dailyTrainingLoadAcute": 212.0,
                        "maxTrainingLoadChronic": 328.5,
                        "minTrainingLoadChronic": 175.2,
                        "dailyTrainingLoadChronic": 219.0,
                        "dailyAcuteChronicWorkloadRatio": 0.9,
                    },
                }
            }
        },
        "mostRecentTrainingLoadBalance": {
            "metricsTrainingLoadBalanceDTOMap": {
                "dev1": {
                    "primaryTrainingDevice": True,
                    "monthlyLoadAerobicLow": 19.4,
                    "monthlyLoadAerobicHigh": 745.2,
                    "monthlyLoadAnaerobic": 16.6,
                    "monthlyLoadAerobicLowTargetMin": 219,
                    "monthlyLoadAerobicLowTargetMax": 481,
                    "monthlyLoadAerobicHighTargetMin": 262,
                    "monthlyLoadAerobicHighTargetMax": 525,
                    "monthlyLoadAnaerobicTargetMin": 0,
                    "monthlyLoadAnaerobicTargetMax": 262,
                    "trainingBalanceFeedbackPhrase": "AEROBIC_LOW_SHORTAGE",
                }
            }
        },
    }
}

SAMPLE_SPLITS = {
    "lapDTOs": [
        {"lapIndex": 0, "distance": 1000.0, "duration": 325.0, "averageHR": 158.0, "averageSpeed": 3.08},
        {"lapIndex": 1, "distance": 1000.0, "duration": 330.0, "averageHR": 162.0, "averageSpeed": 3.03},
    ]
}


def test_ingest_training_load_balance():
    p = make_tmp_db()
    conn = get_conn(p)
    upsert_athlete(conn, "vriendin", "Vriendin", [])
    count = ingest_training_load_balance(conn, "vriendin", SAMPLE_TRAINING_STATUS_FULL)
    assert count == 1
    row = conn.execute(
        "SELECT acwr, acwr_status, balance_feedback FROM training_load_balance WHERE date='2026-06-01'"
    ).fetchone()
    assert row is not None
    assert abs(row["acwr"] - 0.9) < 0.01
    assert row["acwr_status"] == "OPTIMAL"
    assert row["balance_feedback"] == "AEROBIC_LOW_SHORTAGE"
    p.unlink()


def test_ingest_activity_splits():
    p = make_tmp_db()
    conn = get_conn(p)
    upsert_athlete(conn, "vriendin", "Vriendin", [])
    count = ingest_activity_splits(conn, "vriendin", 99001, SAMPLE_SPLITS)
    assert count == 2
    rows = conn.execute(
        "SELECT split_num, duration_s FROM activity_splits WHERE activity_id=99001 ORDER BY split_num"
    ).fetchall()
    assert rows[0]["split_num"] == 1
    assert rows[0]["duration_s"] == 325.0
    assert rows[1]["split_num"] == 2
    p.unlink()


def test_ingest_activities_stores_new_fields():
    p = make_tmp_db()
    conn = get_conn(p)
    upsert_athlete(conn, "vriendin", "Vriendin", [])
    activities_with_new = [
        {
            **SAMPLE_ACTIVITIES[0],
            "activityTrainingLoad": 149.8,
            "differenceBodyBattery": -9,
            "avgStrideLength": 112.2,
            "avgGroundContactTime": 264.6,
            "avgVerticalOscillation": 10.1,
            "avgVerticalRatio": 9.0,
            "aerobicTrainingEffectMessage": "HIGHLY_IMPROVING_LACTATE_THRESHOLD_13",
            "trainingEffectLabel": "LACTATE_THRESHOLD",
            "avgPower": 248.0,
        }
    ]
    ingest_activities(conn, "vriendin", activities_with_new)
    row = conn.execute("SELECT training_load, bb_cost, avg_power FROM activities").fetchone()
    assert abs(row["training_load"] - 149.8) < 0.1
    assert row["bb_cost"] == -9
    assert row["avg_power"] == 248.0
    p.unlink()
