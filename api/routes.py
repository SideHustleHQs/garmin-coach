from __future__ import annotations
import json
import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException

import db as db_module

router = APIRouter(prefix="/api")

_BALANCE_MSGS: dict[str, tuple[str, str]] = {
    "AEROBIC_LOW_SHORTAGE":  ("warning", "Te weinig rustige training. Voeg Z1/Z2 duurlopen toe."),
    "AEROBIC_HIGH_SHORTAGE": ("info",    "Minder intensieve training dan aanbevolen. Overweeg een tempoloop."),
    "ANAEROBIC_SHORTAGE":    ("info",    "Weinig anaëroob werk. Korte sprints kunnen helpen."),
    "ANAEROBIC_EXCESS":      ("warning", "Te veel intensief werk. Plan een rustdag of herstelloop."),
    "AEROBIC_HIGH_EXCESS":   ("warning", "Veel intensieve training. Bouw af voor blessurepreventie."),
    "BALANCED":              ("info",    "Training is goed in balans."),
}


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
        """SELECT date, name, activity_id, distance_m, duration_s, avg_hr, max_hr,
                  hr_zone_1_s, hr_zone_2_s, hr_zone_3_s, hr_zone_4_s, hr_zone_5_s,
                  avg_cadence, aerobic_effect,
                  training_load, bb_cost, aerobic_effect_msg, training_effect_label
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
            "activity_id": r["activity_id"],
            "name": r["name"],
            "distance_km": round(dist_km, 2),
            "duration_s": dur_s,
            "avg_pace_s_per_km": round(pace, 1) if pace else None,
            "avg_hr": r["avg_hr"],
            "max_hr": r["max_hr"],
            "avg_cadence": r["avg_cadence"],
            "aerobic_effect": r["aerobic_effect"],
            "training_load": r["training_load"],
            "bb_cost": r["bb_cost"],
            "aerobic_effect_msg": r["aerobic_effect_msg"],
            "training_effect_label": r["training_effect_label"],
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


@router.get("/athlete/{athlete_id}/training_load")
def get_training_load(athlete_id: str) -> dict[str, Any]:
    conn = _conn()
    _athlete_or_404(conn, athlete_id)
    row = conn.execute(
        """SELECT date, acwr, acwr_status, acute_load, chronic_load, chronic_min, chronic_max,
                  aerobic_low, aerobic_high, anaerobic,
                  aerobic_low_target_min, aerobic_low_target_max,
                  aerobic_high_target_min, aerobic_high_target_max,
                  anaerobic_target_min, anaerobic_target_max,
                  balance_feedback, status_feedback
           FROM training_load_balance WHERE athlete_id=? ORDER BY date DESC LIMIT 1""",
        (athlete_id,),
    ).fetchone()
    if not row:
        return {"latest": None, "balance": None}
    return {
        "latest": {
            "date": row["date"],
            "acwr": row["acwr"],
            "acwr_status": row["acwr_status"],
            "acute_load": row["acute_load"],
            "chronic_load": row["chronic_load"],
            "chronic_min": row["chronic_min"],
            "chronic_max": row["chronic_max"],
            "status_feedback": row["status_feedback"],
        },
        "balance": {
            "aerobic_low":  {"actual": row["aerobic_low"],  "target_min": row["aerobic_low_target_min"],  "target_max": row["aerobic_low_target_max"]},
            "aerobic_high": {"actual": row["aerobic_high"], "target_min": row["aerobic_high_target_min"], "target_max": row["aerobic_high_target_max"]},
            "anaerobic":    {"actual": row["anaerobic"],    "target_min": row["anaerobic_target_min"],    "target_max": row["anaerobic_target_max"]},
            "feedback": row["balance_feedback"],
        },
    }


@router.get("/athlete/{athlete_id}/run_efficiency")
def get_run_efficiency(athlete_id: str, limit: int = 20) -> list[dict[str, Any]]:
    conn = _conn()
    _athlete_or_404(conn, athlete_id)
    rows = conn.execute(
        """SELECT date, activity_id, avg_cadence, avg_gct_ms, avg_vert_osc_mm, avg_vert_ratio
           FROM activities
           WHERE athlete_id=? AND type_key='running'
             AND (avg_cadence IS NOT NULL OR avg_gct_ms IS NOT NULL)
           ORDER BY date DESC LIMIT ?""",
        (athlete_id, limit),
    ).fetchall()
    return [
        {
            "date": r["date"],
            "activity_id": r["activity_id"],
            "cadence_spm": r["avg_cadence"],
            "gct_ms": r["avg_gct_ms"],
            "vert_osc_mm": r["avg_vert_osc_mm"],
            "vert_ratio_pct": r["avg_vert_ratio"],
        }
        for r in rows
    ]


@router.get("/athlete/{athlete_id}/attention_points")
def get_attention_points(athlete_id: str) -> list[dict[str, Any]]:
    conn = _conn()
    _athlete_or_404(conn, athlete_id)
    row = conn.execute(
        """SELECT acwr, acwr_status, balance_feedback
           FROM training_load_balance WHERE athlete_id=? ORDER BY date DESC LIMIT 1""",
        (athlete_id,),
    ).fetchone()
    if not row:
        return []

    points: list[dict[str, Any]] = []

    feedback = row["balance_feedback"] or ""
    if feedback in _BALANCE_MSGS:
        level, msg = _BALANCE_MSGS[feedback]
        points.append({"level": level, "message": msg})

    acwr = row["acwr"]
    if acwr is not None:
        if acwr > 1.5:
            points.append({"level": "warning", "message": f"Zeer hoge trainingsbelasting (ratio {acwr:.2f}). Risico op blessure — neem rust."})
        elif acwr > 1.3:
            points.append({"level": "warning", "message": f"Hoge trainingsbelasting (ratio {acwr:.2f}). Let op herstel."})
        elif acwr < 0.8:
            points.append({"level": "info", "message": f"Trainingsbelasting laag (ratio {acwr:.2f}). Bouw volume langzaam op."})
        else:
            points.append({"level": "info", "message": f"Trainingsbelasting optimaal (ratio {acwr:.2f})."})

    return points


@router.get("/athlete/{athlete_id}/activity/{activity_id}/splits")
def get_activity_splits(athlete_id: str, activity_id: int) -> list[dict[str, Any]]:
    conn = _conn()
    _athlete_or_404(conn, athlete_id)
    rows = conn.execute(
        """SELECT split_num, distance_m, duration_s, avg_hr, avg_speed_mps
           FROM activity_splits
           WHERE athlete_id=? AND activity_id=?
           ORDER BY split_num""",
        (athlete_id, activity_id),
    ).fetchall()
    result = []
    for r in rows:
        dist_km = (r["distance_m"] or 0) / 1000
        pace = r["duration_s"] / dist_km if dist_km > 0 else None
        result.append({
            "split_num": r["split_num"],
            "distance_m": r["distance_m"],
            "duration_s": r["duration_s"],
            "avg_hr": r["avg_hr"],
            "pace_s_per_km": round(pace, 1) if pace else None,
        })
    return result


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
