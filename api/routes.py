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


@router.get("/athletes")
def get_athletes() -> list[dict[str, Any]]:
    conn = _conn()
    rows = conn.execute("SELECT id, display_name, panels_config FROM athletes ORDER BY id").fetchall()
    return [
        {"id": r["id"], "display_name": r["display_name"], "panels": json.loads(r["panels_config"])}
        for r in rows
    ]


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

    runs = conn.execute(
        """SELECT duration_s, distance_m FROM activities
           WHERE athlete_id=? AND type_key='running' AND distance_m > 0
           ORDER BY date DESC LIMIT 3""",
        (athlete_id,),
    ).fetchall()

    predicted_time_s = None
    predicted_pace = None
    if runs:
        pace_list = [r["duration_s"] / (r["distance_m"] / 1000) for r in runs]
        predicted_pace = sum(pace_list) / len(pace_list)
        predicted_time_s = predicted_pace * 16.1

    return {
        "latest_readiness": (
            {"score": readiness["score"], "level": readiness["level"], "feedback": readiness["feedback_short"]}
            if readiness else None
        ),
        "latest_vo2max": (
            {"date": vo2["date"], "value": vo2["vo2max"]}
            if vo2 else None
        ),
        "predicted_16k_pace_s_per_km": predicted_pace,
        "predicted_16k_time_s": predicted_time_s,
    }


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


@router.get("/athlete/{athlete_id}/vo2max_trend")
def get_vo2max_trend(athlete_id: str) -> list[dict[str, Any]]:
    conn = _conn()
    _athlete_or_404(conn, athlete_id)
    rows = conn.execute(
        "SELECT date, vo2max FROM vo2max WHERE athlete_id=? ORDER BY date",
        (athlete_id,),
    ).fetchall()
    return [{"date": r["date"], "vo2max": r["vo2max"]} for r in rows]


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
