from __future__ import annotations
import datetime as _dt
import json
import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException

import adapt_engine
import coach_rules
import db as db_module
import metrics
import plan_engine

router = APIRouter(prefix="/api")

_BALANCE_MSGS: dict[str, tuple[str, str]] = {
    "AEROBIC_LOW_SHORTAGE":  ("warning", "Te weinig rustige training. Voeg Z1/Z2 duurlopen toe."),
    "AEROBIC_HIGH_SHORTAGE": ("info",    "Minder intensieve training dan aanbevolen. Overweeg een tempoloop."),
    "ANAEROBIC_SHORTAGE":    ("info",    "Weinig anaëroob werk. Korte sprints kunnen helpen."),
    "ANAEROBIC_EXCESS":      ("warning", "Te veel intensief werk. Plan een rustdag of herstelloop."),
    "AEROBIC_HIGH_EXCESS":   ("warning", "Veel intensieve training. Bouw af voor blessurepreventie."),
    "BALANCED":              ("info",    "Training is goed in balans."),
}


def _conn():
    if db_module.use_postgres():
        import psycopg2.extras
        conn = db_module.get_pg_conn()
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn
    return db_module.get_conn(db_module.DB_PATH)


def _exec(conn, sql: str, params=()):
    if db_module.use_postgres():
        sql = sql.replace("?", "%s")
        cur = conn.cursor()
        cur.execute(sql, params or None)
        return cur
    return conn.execute(sql, params)


def _athlete_or_404(conn, athlete_id: str):
    row = _exec(conn, "SELECT * FROM athletes WHERE id=?", (athlete_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Atleet '{athlete_id}' niet gevonden")
    return row


@router.get("/athletes")
def get_athletes() -> list[dict[str, Any]]:
    conn = _conn()
    try:
        rows = _exec(conn, "SELECT id, display_name, panels_config FROM athletes ORDER BY id").fetchall()
        return [
            {"id": r["id"], "display_name": r["display_name"], "panels": json.loads(r["panels_config"])}
            for r in rows
        ]
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/hero")
def get_hero(athlete_id: str) -> dict[str, Any]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)

        readiness = _exec(
            conn,
            "SELECT score, level, feedback_short FROM training_readiness WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
            (athlete_id,),
        ).fetchone()

        vo2 = _exec(
            conn,
            "SELECT date, vo2max FROM vo2max WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
            (athlete_id,),
        ).fetchone()

        runs = _exec(
            conn,
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
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/home")
def get_home(athlete_id: str) -> dict[str, Any]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)

        readiness = _exec(conn,
            "SELECT score, level FROM training_readiness WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
            (athlete_id,)).fetchone()
        hrv = _exec(conn,
            "SELECT last_night_avg FROM hrv WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
            (athlete_id,)).fetchone()
        sleep = _exec(conn,
            "SELECT duration_s FROM sleep WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
            (athlete_id,)).fetchone()
        bb = _exec(conn,
            "SELECT level_current FROM body_battery WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
            (athlete_id,)).fetchone()
        vo2 = _exec(conn,
            "SELECT vo2max FROM vo2max WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
            (athlete_id,)).fetchone()
        rest = _exec(conn,
            "SELECT resting_hr FROM daily_heart_rates WHERE athlete_id=? AND resting_hr IS NOT NULL ORDER BY date DESC LIMIT 1",
            (athlete_id,)).fetchone()
        load = _exec(conn,
            "SELECT acwr, acwr_status FROM training_load_balance WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
            (athlete_id,)).fetchone()
        last = _exec(conn,
            """SELECT date, name, activity_id, distance_m, duration_s, avg_hr,
                      hr_zone_1_s, hr_zone_2_s, hr_zone_3_s, hr_zone_4_s, hr_zone_5_s
               FROM activities WHERE athlete_id=? AND type_key='running' AND distance_m > 0
               ORDER BY date DESC LIMIT 1""",
            (athlete_id,)).fetchone()

        readiness_score = readiness["score"] if readiness else None
        last_run = None
        if last:
            dist_km = (last["distance_m"] or 0) / 1000
            dur_s = last["duration_s"] or 0
            splits = _exec(conn,
                """SELECT distance_m, duration_s FROM activity_splits
                   WHERE athlete_id=? AND activity_id=? ORDER BY split_num""",
                (athlete_id, last["activity_id"])).fetchall()
            splits_pace = [
                round(s["duration_s"] / (s["distance_m"] / 1000), 1)
                for s in splits if (s["distance_m"] or 0) > 0 and (s["duration_s"] or 0) > 0
            ]
            last_run = {
                "date": last["date"], "activity_id": last["activity_id"], "name": last["name"],
                "distance_km": round(dist_km, 2),
                "avg_pace_s_per_km": round(dur_s / dist_km, 1) if dist_km > 0 else None,
                "avg_hr": last["avg_hr"],
                "zones": {"z1": last["hr_zone_1_s"], "z2": last["hr_zone_2_s"], "z3": last["hr_zone_3_s"],
                          "z4": last["hr_zone_4_s"], "z5": last["hr_zone_5_s"]},
                "duiding": coach_rules.duiding_run({"splits_pace": splits_pace, "avg_hr": last["avg_hr"]}),
            }

        return {
            "readiness": {
                "score": readiness_score,
                "level": readiness["level"] if readiness else None,
                "hrv": hrv["last_night_avg"] if hrv else None,
                "sleep_s": sleep["duration_s"] if sleep else None,
                "body_battery": bb["level_current"] if bb else None,
                "duiding": coach_rules.duiding_readiness({"score": readiness_score}),
            },
            "fitness": {
                "vo2max": vo2["vo2max"] if vo2 else None,
                "resting_hr": rest["resting_hr"] if rest else None,
            },
            "load": {
                "acwr": load["acwr"] if load else None,
                "acwr_status": load["acwr_status"] if load else None,
                "duiding": coach_rules.duiding_load({"acwr": load["acwr"] if load else None}),
            },
            "last_run": last_run,
        }
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/dashboard")
def get_dashboard(athlete_id: str) -> dict[str, Any]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        today = _dt.date.today().isoformat()

        def one(sql, params):
            return _exec(conn, sql, params).fetchone()
        def many(sql, params):
            return _exec(conn, sql, params).fetchall()

        tw = one("""SELECT title, run_type, day_type, week_num, target_pace_s
                    FROM planned_workout WHERE athlete_id=? AND date=?""", (athlete_id, today))
        today_workout = ({"title": tw["title"], "run_type": tw["run_type"], "day_type": tw["day_type"],
                          "week_num": tw["week_num"], "target_pace_s": tw["target_pace_s"]} if tw else None)

        rd = one("SELECT score, level FROM training_readiness WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,))
        hrv_l = one("SELECT last_night_avg FROM hrv WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,))
        sleep_l = one("SELECT duration_s, score FROM sleep WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,))
        bb = one("SELECT level_current FROM body_battery WHERE athlete_id=? AND level_current IS NOT NULL ORDER BY date DESC LIMIT 1", (athlete_id,))
        readiness_score = rd["score"] if rd else None

        vo2_rows = many("SELECT date, vo2max FROM vo2max WHERE athlete_id=? ORDER BY date", (athlete_id,))
        vo2_trend = [{"date": r["date"], "vo2max": r["vo2max"]} for r in vo2_rows]
        vo2_latest = vo2_trend[-1]["vo2max"] if vo2_trend else None

        load = one("SELECT acwr, acwr_status FROM training_load_balance WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,))

        runs = many("""SELECT date, distance_m, duration_s, avg_hr FROM activities
                       WHERE athlete_id=? AND type_key='running' AND distance_m>0 ORDER BY date""", (athlete_id,))
        pace_trend = metrics.pace_at_hr([dict(r) for r in runs])

        if db_module.use_postgres():
            week_expr = "to_char(date::date, 'IYYY-\"W\"IW')"
        else:
            week_expr = "strftime('%Y-W%W', date)"
        wv = many(f"""SELECT {week_expr} AS week, SUM(distance_m)/1000.0 AS km
                      FROM activities WHERE athlete_id=? AND type_key='running'
                      GROUP BY week ORDER BY week DESC LIMIT 6""", (athlete_id,))
        weekly_volume = [{"week": r["week"], "km": round(r["km"], 1)} for r in reversed(wv)]

        rest_rows = many("""SELECT date, resting_hr FROM daily_heart_rates
                            WHERE athlete_id=? AND resting_hr IS NOT NULL ORDER BY date""", (athlete_id,))
        rest_trend = [{"date": r["date"], "resting_hr": r["resting_hr"]} for r in rest_rows]
        hrv_rows = many("SELECT date, last_night_avg FROM hrv WHERE athlete_id=? AND last_night_avg IS NOT NULL ORDER BY date", (athlete_id,))
        hrv_trend = [{"date": r["date"], "hrv": r["last_night_avg"]} for r in hrv_rows]
        ds = one("SELECT steps, active_calories FROM daily_stats WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,))

        last = one("""SELECT date, name, activity_id, distance_m, duration_s, avg_hr,
                             hr_zone_1_s, hr_zone_2_s, hr_zone_3_s, hr_zone_4_s, hr_zone_5_s
                      FROM activities WHERE athlete_id=? AND type_key='running' AND distance_m>0
                      ORDER BY date DESC LIMIT 1""", (athlete_id,))
        last_run = None
        if last:
            dist_km = (last["distance_m"] or 0) / 1000
            dur_s = last["duration_s"] or 0
            splits = many("""SELECT distance_m, duration_s FROM activity_splits
                             WHERE athlete_id=? AND activity_id=? ORDER BY split_num""", (athlete_id, last["activity_id"]))
            sp = [round(s["duration_s"] / (s["distance_m"] / 1000), 1) for s in splits if (s["distance_m"] or 0) > 0 and (s["duration_s"] or 0) > 0]
            last_run = {
                "date": last["date"], "activity_id": last["activity_id"], "name": last["name"],
                "distance_km": round(dist_km, 2),
                "avg_pace_s_per_km": round(dur_s / dist_km, 1) if dist_km > 0 else None,
                "avg_hr": last["avg_hr"],
                "zones": {"z1": last["hr_zone_1_s"], "z2": last["hr_zone_2_s"], "z3": last["hr_zone_3_s"],
                          "z4": last["hr_zone_4_s"], "z5": last["hr_zone_5_s"]},
                "duiding": coach_rules.duiding_run({"splits_pace": sp, "avg_hr": last["avg_hr"]}),
            }

        return {
            "today_workout": today_workout,
            "readiness": {
                "score": readiness_score, "level": rd["level"] if rd else None,
                "hrv": hrv_l["last_night_avg"] if hrv_l else None,
                "sleep_s": sleep_l["duration_s"] if sleep_l else None,
                "body_battery": bb["level_current"] if bb else None,
                "duiding": coach_rules.duiding_readiness({"score": readiness_score}),
            },
            "running": {
                "vo2max": vo2_latest, "vo2max_trend": vo2_trend,
                "weekly_volume": weekly_volume,
                "acwr": load["acwr"] if load else None,
                "acwr_status": load["acwr_status"] if load else None,
                "pace_at_hr": pace_trend[-1]["pace_s_per_km"] if pace_trend else None,
                "pace_at_hr_trend": pace_trend,
            },
            "last_run": last_run,
            "health": {
                "hrv": hrv_l["last_night_avg"] if hrv_l else None, "hrv_trend": hrv_trend,
                "sleep": {"duration_s": sleep_l["duration_s"] if sleep_l else None,
                          "score": sleep_l["score"] if sleep_l else None},
                "body_battery": bb["level_current"] if bb else None,
                "resting_hr": rest_trend[-1]["resting_hr"] if rest_trend else None,
                "resting_hr_trend": rest_trend,
                "steps": ds["steps"] if ds else None,
                "active_calories": ds["active_calories"] if ds else None,
            },
        }
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/fitness")
def get_fitness(athlete_id: str) -> dict[str, Any]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        vo2 = _exec(conn, "SELECT date, vo2max FROM vo2max WHERE athlete_id=? ORDER BY date", (athlete_id,)).fetchall()
        rest = _exec(conn,
            """SELECT date, resting_hr FROM daily_heart_rates
               WHERE athlete_id=? AND resting_hr IS NOT NULL ORDER BY date""",
            (athlete_id,)).fetchall()
        runs = _exec(conn,
            """SELECT date, distance_m, duration_s, avg_hr FROM activities
               WHERE athlete_id=? AND type_key='running' AND distance_m > 0 ORDER BY date""",
            (athlete_id,)).fetchall()
        pace_trend = metrics.pace_at_hr([dict(r) for r in runs])
        vo2_vals = [r["vo2max"] for r in vo2 if r["vo2max"] is not None]
        if len(vo2_vals) < 2:
            duiding = "Nog te weinig data voor een fitheidstrend."
        elif vo2_vals[-1] > vo2_vals[0]:
            duiding = "Je VO₂max stijgt — je aerobe motor wordt sterker."
        else:
            duiding = "Je fitheid is stabiel."
        return {
            "vo2max_trend": [{"date": r["date"], "vo2max": r["vo2max"]} for r in vo2],
            "resting_hr_trend": [{"date": r["date"], "resting_hr": r["resting_hr"]} for r in rest],
            "pace_at_hr": pace_trend,
            "duiding": duiding,
        }
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/runs")
def get_runs(athlete_id: str, limit: int = 20) -> list[dict[str, Any]]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        rows = _exec(
            conn,
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
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/weekly_volume")
def get_weekly_volume(athlete_id: str) -> list[dict]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        if db_module.use_postgres():
            week_expr = "to_char(date::date, 'IYYY-\"W\"IW')"
        else:
            week_expr = "strftime('%Y-W%W', date)"
        sql = f"""
            SELECT {week_expr} AS week,
                   SUM(distance_m) / 1000.0 AS km,
                   COUNT(*) AS run_count
            FROM activities
            WHERE athlete_id=? AND type_key='running'
            GROUP BY week
            ORDER BY week DESC
            LIMIT 16
        """
        rows = _exec(conn, sql, (athlete_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/tempo_trend")
def get_tempo_trend(athlete_id: str) -> list[dict[str, Any]]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        rows = _exec(
            conn,
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
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/zone_distribution")
def get_zone_distribution(athlete_id: str) -> dict[str, Any]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        row = _exec(
            conn,
            """SELECT SUM(hr_zone_1_s) z1, SUM(hr_zone_2_s) z2, SUM(hr_zone_3_s) z3,
                      SUM(hr_zone_4_s) z4, SUM(hr_zone_5_s) z5
               FROM activities WHERE athlete_id=? AND type_key='running'""",
            (athlete_id,),
        ).fetchone()
        return {
            "z1": row["z1"] or 0, "z2": row["z2"] or 0, "z3": row["z3"] or 0,
            "z4": row["z4"] or 0, "z5": row["z5"] or 0,
        }
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/vo2max_trend")
def get_vo2max_trend(athlete_id: str) -> list[dict[str, Any]]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        rows = _exec(
            conn,
            "SELECT date, vo2max FROM vo2max WHERE athlete_id=? ORDER BY date",
            (athlete_id,),
        ).fetchall()
        return [{"date": r["date"], "vo2max": r["vo2max"]} for r in rows]
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/training_load")
def get_training_load(athlete_id: str) -> dict[str, Any]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        row = _exec(
            conn,
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
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/run_efficiency")
def get_run_efficiency(athlete_id: str, limit: int = 20) -> list[dict[str, Any]]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        rows = _exec(
            conn,
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
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/attention_points")
def get_attention_points(athlete_id: str) -> list[dict[str, Any]]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        row = _exec(
            conn,
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
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/activity/{activity_id}/splits")
def get_activity_splits(athlete_id: str, activity_id: int) -> list[dict[str, Any]]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        rows = _exec(
            conn,
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
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/daily_stats")
def get_daily_stats(athlete_id: str, days: int = 14) -> list[dict[str, Any]]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        rows = _exec(
            conn,
            """SELECT date, steps, active_calories FROM daily_stats
               WHERE athlete_id=? ORDER BY date DESC LIMIT ?""",
            (athlete_id, days),
        ).fetchall()
        return [{"date": r["date"], "steps": r["steps"], "active_calories": r["active_calories"]} for r in rows]
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/recovery")
def get_recovery(athlete_id: str, days: int = 7) -> list[dict[str, Any]]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        rows = _exec(
            conn,
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
    finally:
        if db_module.use_postgres():
            conn.close()


def _fitness(conn, athlete_id: str) -> dict:
    rows = _exec(conn,
        """SELECT distance_m, duration_s, avg_hr FROM activities
           WHERE athlete_id=? AND type_key='running' AND distance_m>0 ORDER BY date DESC LIMIT 20""",
        (athlete_id,)).fetchall()
    paces = [r["duration_s"] / (r["distance_m"] / 1000) for r in rows if (r["distance_m"] or 0) > 0]
    longest = max([(r["distance_m"] or 0) / 1000 for r in rows], default=0)
    easy = round(sorted(paces)[len(paces) // 2]) if paces else None
    return {"current_easy_s": easy, "longest_km": round(longest) or None}


@router.post("/athlete/{athlete_id}/plan")
def create_plan(athlete_id: str, body: dict) -> dict[str, Any]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        _exec(conn, "DELETE FROM planned_workout WHERE athlete_id=?", (athlete_id,))
        _exec(conn, "DELETE FROM training_plan WHERE athlete_id=?", (athlete_id,))
        _exec(conn,
            """INSERT INTO training_plan (athlete_id, race_name, race_date, race_distance_km,
               goal_time_s, start_date, weeks, methodology, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (athlete_id, body["race_name"], body["race_date"], body["race_distance_km"],
             body.get("goal_time_s"), body["start_date"], body["weeks"], "periodized-v1", body["start_date"]))
        prefs = {"run_days": body["run_days"], "fixed_days": body["fixed_days"]}
        _exec(conn,
            """INSERT INTO athlete_training_prefs (athlete_id, runs_per_week, run_days, fixed_days)
               VALUES (?,?,?,?)
               ON CONFLICT(athlete_id) DO UPDATE SET runs_per_week=excluded.runs_per_week,
                 run_days=excluded.run_days, fixed_days=excluded.fixed_days""",
            (athlete_id, len(body["run_days"]), json.dumps(body["run_days"]), json.dumps(body["fixed_days"])))
        rows = plan_engine.generate_plan(body, prefs, _fitness(conn, athlete_id))
        for r in rows:
            _exec(conn,
                """INSERT INTO planned_workout (athlete_id, date, week_num, phase, day_type,
                   run_type, title, distance_km, segments, target_pace_s, coach_note, status)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,'planned')""",
                (athlete_id, r["date"], r["week_num"], r["phase"], r["day_type"], r["run_type"],
                 r["title"], r["distance_km"], json.dumps(r["segments"]) if r["segments"] else None,
                 r["target_pace_s"], r["coach_note"]))
        conn.commit()
        return {"ok": True, "days": len(rows)}
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/plan")
def get_plan(athlete_id: str) -> dict[str, Any]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        p = _exec(conn, "SELECT * FROM training_plan WHERE athlete_id=? ORDER BY id DESC LIMIT 1",
                  (athlete_id,)).fetchone()
        if not p:
            return {"plan": None}
        agg = _exec(conn,
            """SELECT COUNT(*) n, COALESCE(SUM(distance_km),0) km,
                      COALESCE(SUM(CASE WHEN status='done' THEN distance_km ELSE 0 END),0) done_km
               FROM planned_workout WHERE athlete_id=? AND day_type='run'""",
            (athlete_id,)).fetchone()
        lo, hi = plan_engine.estimate_finish(p["race_distance_km"], p["goal_time_s"], _fitness(conn, athlete_id))
        return {
            "race_name": p["race_name"], "race_date": p["race_date"],
            "race_distance_km": p["race_distance_km"], "goal_time_s": p["goal_time_s"],
            "weeks": p["weeks"], "start_date": p["start_date"],
            "total_planned_km": round(agg["km"], 1), "done_km": round(agg["done_km"], 1),
            "estimated_time_s": [lo, hi],
        }
    finally:
        if db_module.use_postgres():
            conn.close()


def _wo_dict(r) -> dict:
    override = bool(r["user_override"])
    use_adj = bool(r["is_adjusted"]) and not override
    run_type = r["adjusted_run_type"] if use_adj and r["adjusted_run_type"] is not None else r["run_type"]
    title = r["adjusted_title"] if use_adj and r["adjusted_title"] else r["title"]
    target = r["adjusted_target_pace_s"] if use_adj and r["adjusted_target_pace_s"] is not None else r["target_pace_s"]
    seg_src = r["adjusted_segments"] if use_adj and r["adjusted_segments"] else r["segments"]
    return {"date": r["date"], "week_num": r["week_num"], "phase": r["phase"],
            "day_type": r["day_type"], "run_type": run_type, "title": title,
            "distance_km": r["distance_km"], "target_pace_s": target,
            "coach_note": r["coach_note"], "status": r["status"],
            "segments": json.loads(seg_src) if seg_src else None,
            "is_adjusted": use_adj, "adjustment_reason": r["adjustment_reason"] if use_adj else None,
            "user_override": override, "missed": bool(r["missed"])}


@router.get("/athlete/{athlete_id}/plan/week")
def get_plan_week(athlete_id: str, week: int = 1) -> list[dict[str, Any]]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        rows = _exec(conn,
            "SELECT * FROM planned_workout WHERE athlete_id=? AND week_num=? ORDER BY date",
            (athlete_id, week)).fetchall()
        return [_wo_dict(r) for r in rows]
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/workout/{wdate}")
def get_workout(athlete_id: str, wdate: str) -> dict[str, Any]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        r = _exec(conn, "SELECT * FROM planned_workout WHERE athlete_id=? AND date=?",
                  (athlete_id, wdate)).fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Geen workout op deze datum")
        return _wo_dict(r)
    finally:
        if db_module.use_postgres():
            conn.close()


@router.post("/athlete/{athlete_id}/workout/{wdate}/register")
def register_workout(athlete_id: str, wdate: str) -> dict[str, Any]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        act = _exec(conn,
            "SELECT activity_id FROM activities WHERE athlete_id=? AND date=? AND type_key='running' LIMIT 1",
            (athlete_id, wdate)).fetchone()
        _exec(conn,
            "UPDATE planned_workout SET status='done', linked_activity_id=? WHERE athlete_id=? AND date=?",
            (act["activity_id"] if act else None, athlete_id, wdate))
        conn.commit()
        return {"ok": True, "linked_activity_id": act["activity_id"] if act else None}
    finally:
        if db_module.use_postgres():
            conn.close()


@router.post("/athlete/{athlete_id}/adapt")
def adapt_plan(athlete_id: str) -> dict[str, Any]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        today = _dt.date.today().isoformat()
        window_end = (_dt.date.today() + _dt.timedelta(days=2)).isoformat()
        plan = _exec(conn, "SELECT goal_time_s, race_distance_km FROM training_plan WHERE athlete_id=? ORDER BY id DESC LIMIT 1", (athlete_id,)).fetchone()
        if not plan:
            return {"ok": True, "adjusted": 0}
        paces = plan_engine.compute_paces(plan["goal_time_s"], plan["race_distance_km"], _fitness(conn, athlete_id).get("current_easy_s"))
        rd = _exec(conn, "SELECT score FROM training_readiness WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,)).fetchone()
        load = _exec(conn, "SELECT acwr FROM training_load_balance WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,)).fetchone()
        sl = _exec(conn, "SELECT duration_s, score FROM sleep WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,)).fetchone()
        signals = {"readiness": rd["score"] if rd else None, "acwr": load["acwr"] if load else None,
                   "sleep_s": sl["duration_s"] if sl else None, "sleep_score": sl["score"] if sl else None,
                   "recent_quality_hit": False, "downgrade_last_48h": False}
        # pas alleen het near-term venster (vandaag + 2 dagen) aan, niet-override run-dagen
        rows = _exec(conn, "SELECT date, run_type, title, target_pace_s, distance_km, segments FROM planned_workout WHERE athlete_id=? AND date>=? AND date<=? AND user_override=0", (athlete_id, today, window_end)).fetchall()
        n = 0
        for r in rows:
            wo = {"run_type": r["run_type"], "title": r["title"], "target_pace_s": r["target_pace_s"],
                  "distance_km": r["distance_km"], "segments": json.loads(r["segments"]) if r["segments"] else None}
            adj = adapt_engine.adjust_day(wo, signals, paces)
            if adj:
                _exec(conn, """UPDATE planned_workout SET is_adjusted=1, adjusted_run_type=?, adjusted_title=?,
                       adjusted_target_pace_s=?, adjusted_segments=?, adjustment_reason=? WHERE athlete_id=? AND date=?""",
                      (adj["adjusted_run_type"], adj["adjusted_title"], adj.get("adjusted_target_pace_s"),
                       json.dumps(adj["adjusted_segments"]) if adj.get("adjusted_segments") else None,
                       adj["adjustment_reason"], athlete_id, r["date"]))
                n += 1
            else:
                _exec(conn, "UPDATE planned_workout SET is_adjusted=0 WHERE athlete_id=? AND date=?", (athlete_id, r["date"]))
        # markeer gemiste verleden runs
        _exec(conn, """UPDATE planned_workout SET missed=1 WHERE athlete_id=? AND date<? AND day_type='run' AND linked_activity_id IS NULL""", (athlete_id, today))
        conn.commit()
        return {"ok": True, "adjusted": n}
    finally:
        if db_module.use_postgres():
            conn.close()


@router.post("/athlete/{athlete_id}/workout/{wdate}/override")
def override_workout(athlete_id: str, wdate: str) -> dict[str, Any]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        _exec(conn, "UPDATE planned_workout SET user_override=1 WHERE athlete_id=? AND date=?", (athlete_id, wdate))
        conn.commit()
        return {"ok": True}
    finally:
        if db_module.use_postgres():
            conn.close()


@router.post("/athlete/{athlete_id}/replan")
def trigger_replan(athlete_id: str) -> dict:
    """On-demand drift-check + replan."""
    today = _dt.date.today()
    today_s = str(today)
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        rows = [dict(r) for r in _exec(conn,
            "SELECT date AS planned_date, run_type, missed, linked_activity_id FROM planned_workout "
            "WHERE athlete_id=? ORDER BY date", (athlete_id,)).fetchall()]
        cutoff = str(today - _dt.timedelta(days=14))
        try:
            acwr_rows = _exec(conn,
                "SELECT acwr FROM training_load_balance WHERE athlete_id=? AND date>=?",
                (athlete_id, cutoff)).fetchall()
            acwr_hist = [r["acwr"] for r in acwr_rows if r.get("acwr") is not None]
        except Exception:
            acwr_hist = []
        drift = adapt_engine.check_drift(rows, today, {"acwr_history": acwr_hist})
        if not drift["drift"]:
            return {"replanned": False, "reason": "Geen drift gedetecteerd."}
        plan_row = _exec(conn,
            "SELECT * FROM training_plan WHERE athlete_id=? ORDER BY created_at DESC LIMIT 1",
            (athlete_id,)).fetchone()
        if not plan_row:
            return {"replanned": False, "reason": "Geen plan gevonden."}
        plan = dict(plan_row)
        fitness_row = _exec(conn,
            "SELECT easy_pace_s, vo2max FROM athlete_metrics WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
            (athlete_id,)).fetchone() if False else None  # table may not exist
        try:
            fitness_row = _exec(conn,
                "SELECT easy_pace_s, vo2max FROM athlete_metrics WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
                (athlete_id,)).fetchone()
        except Exception:
            fitness_row = None
        fitness = {
            "easy_pace_s": fitness_row["easy_pace_s"] if fitness_row else None,
            "vo2max": fitness_row["vo2max"] if fitness_row else None,
        }
        run_days_raw = plan.get("run_days") or "mon,wed,fri,sat"
        prefs = {
            "run_days": run_days_raw.split(",") if isinstance(run_days_raw, str) else run_days_raw,
            "long_day": plan.get("long_day") or "sat",
            "hyrox_days": [], "strength_days": [],
        }
        new_rows = adapt_engine.replan(plan, today, prefs, fitness)
        _exec(conn, "DELETE FROM planned_workout WHERE athlete_id=? AND date>=?", (athlete_id, today_s))
        for r in new_rows:
            _exec(conn,
                """INSERT OR IGNORE INTO planned_workout
                   (athlete_id, date, week_num, run_type, title, distance_km,
                    target_pace_s, segments, coach_note, day_type)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (athlete_id, r.get("planned_date") or r.get("date"), r.get("week_num"),
                 r.get("run_type"), r.get("title"), r.get("distance_km"),
                 r.get("target_pace_s"),
                 json.dumps(r["segments"]) if isinstance(r.get("segments"), list) else r.get("segments"),
                 r.get("notes"), r.get("day_type", "run")))
        try:
            _exec(conn,
                "INSERT INTO plan_replan_log (athlete_id, replan_date, reason) VALUES (?,?,?)",
                (athlete_id, today_s, drift["reason"]))
        except Exception:
            pass
        conn.commit()
        return {"replanned": True, "reason": drift["reason"], "new_rows": len(new_rows)}
    finally:
        if db_module.use_postgres():
            conn.close()


@router.get("/athlete/{athlete_id}/plan/meta")
def get_plan_meta(athlete_id: str) -> dict:
    """Plan-metadata inclusief laatste replan."""
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        try:
            last = _exec(conn,
                "SELECT replan_date, reason FROM plan_replan_log WHERE athlete_id=? ORDER BY id DESC LIMIT 1",
                (athlete_id,)).fetchone()
        except Exception:
            last = None
        plan_row = _exec(conn,
            "SELECT race_date FROM training_plan WHERE athlete_id=? ORDER BY created_at DESC LIMIT 1",
            (athlete_id,)).fetchone()
        return {
            "last_replan": dict(last) if last else None,
            "race_date": plan_row["race_date"] if plan_row else None,
        }
    finally:
        if db_module.use_postgres():
            conn.close()
