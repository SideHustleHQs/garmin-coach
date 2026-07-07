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
    ingest_training_load_balance, ingest_activity_splits,
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
    ingest_training_load_balance(conn, "vriendin", {
        "2026-06-20": {
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
    })
    ingest_activity_splits(conn, "vriendin", 1001, {
        "lapDTOs": [
            {"lapIndex": 0, "distance": 1000.0, "duration": 325.0, "averageHR": 158.0, "averageSpeed": 3.08},
            {"lapIndex": 1, "distance": 1000.0, "duration": 330.0, "averageHR": 162.0, "averageSpeed": 3.03},
        ]
    })
    yield
    conn.executescript("""
        DELETE FROM activities; DELETE FROM training_readiness;
        DELETE FROM vo2max; DELETE FROM daily_stats; DELETE FROM body_battery;
        DELETE FROM training_load_balance; DELETE FROM activity_splits;
        DELETE FROM planned_workout; DELETE FROM training_plan;
        DELETE FROM athlete_training_prefs;
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


def test_get_training_load():
    r = client.get("/api/athlete/vriendin/training_load")
    assert r.status_code == 200
    d = r.json()
    assert d["latest"] is not None
    assert abs(d["latest"]["acwr"] - 0.9) < 0.01
    assert d["latest"]["acwr_status"] == "OPTIMAL"
    assert d["balance"]["feedback"] == "AEROBIC_LOW_SHORTAGE"


def test_get_attention_points():
    r = client.get("/api/athlete/vriendin/attention_points")
    assert r.status_code == 200
    points = r.json()
    assert len(points) >= 1
    messages = [p["message"] for p in points]
    assert any("Z1" in m or "duurlopen" in m for m in messages)


def test_get_run_efficiency():
    r = client.get("/api/athlete/vriendin/run_efficiency")
    assert r.status_code == 200
    # may be empty if activity has no gct data — just verify no 500


def test_get_activity_splits():
    r = client.get("/api/athlete/vriendin/activity/1001/splits")
    assert r.status_code == 200
    splits = r.json()
    assert len(splits) == 2
    assert splits[0]["split_num"] == 1
    assert splits[0]["pace_s_per_km"] is not None


def test_runs_include_training_load():
    r = client.get("/api/athlete/vriendin/runs")
    assert r.status_code == 200
    runs = r.json()
    assert "training_load" in runs[0]
    assert "activity_id" in runs[0]


def test_home_endpoint_shape():
    client = TestClient(app)
    r = client.get("/api/athlete/vriendin/home")
    assert r.status_code == 200
    body = r.json()
    assert set(["readiness", "fitness", "load", "last_run"]).issubset(body.keys())
    assert "duiding" in body["readiness"]
    assert "duiding" in body["load"]


def test_home_endpoint_404_unknown_athlete():
    client = TestClient(app)
    assert client.get("/api/athlete/nobody/home").status_code == 404


def test_fitness_endpoint_shape():
    client = TestClient(app)
    r = client.get("/api/athlete/vriendin/fitness")
    assert r.status_code == 200
    body = r.json()
    assert set(["vo2max_trend", "resting_hr_trend", "pace_at_hr", "duiding"]).issubset(body.keys())
    assert isinstance(body["pace_at_hr"], list)


def test_create_and_get_plan():
    client = TestClient(app)
    body = {"race_name": "Test Marathon", "race_date": "2026-10-18",
            "race_distance_km": 42.195, "goal_time_s": 14400,
            "start_date": "2026-07-13", "weeks": 14,
            "run_days": ["mon", "thu", "sat"],
            "fixed_days": {"tue": "strength", "wed": "hyrox", "fri": "strength"}}
    r = client.post("/api/athlete/vriendin/plan", json=body)
    assert r.status_code == 200
    g = client.get("/api/athlete/vriendin/plan").json()
    assert g["race_name"] == "Test Marathon"
    assert g["weeks"] == 14
    assert "estimated_time_s" in g and len(g["estimated_time_s"]) == 2
    assert g["total_planned_km"] > 0


def test_plan_week_and_workout_and_register():
    client = TestClient(app)
    body = {"race_name": "M", "race_date": "2026-10-18", "race_distance_km": 42.195,
            "goal_time_s": 14400, "start_date": "2026-07-13", "weeks": 14,
            "run_days": ["mon", "thu", "sat"],
            "fixed_days": {"tue": "strength", "wed": "hyrox", "fri": "strength"}}
    client.post("/api/athlete/vriendin/plan", json=body)
    wk = client.get("/api/athlete/vriendin/plan/week?week=1").json()
    assert len(wk) == 7
    run_day = next(d for d in wk if d["day_type"] == "run")
    w = client.get(f"/api/athlete/vriendin/workout/{run_day['date']}").json()
    assert w["title"] and "segments" in w
    reg = client.post(f"/api/athlete/vriendin/workout/{run_day['date']}/register")
    assert reg.status_code == 200
    wk2 = client.get("/api/athlete/vriendin/plan/week?week=1").json()
    assert any(d["date"] == run_day["date"] and d["status"] == "done" for d in wk2)
