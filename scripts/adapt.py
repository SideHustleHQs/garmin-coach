#!/usr/bin/env python3
"""Draai de dagelijkse plan-aanpassing standalone tegen de DB (voor sync + CLI).
Zelfde logica als POST /athlete/{id}/adapt (api/routes.py), maar zonder FastAPI."""
import datetime as _dt
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import adapt_engine
import db as db_module
import plan_engine

ATHLETES = ["rowan", "vriendin"]


def _run_drift_and_replan(conn, athlete_id: str, today) -> None:
    """Controleer drift; herplan indien nodig."""
    import datetime as _dt2
    from adapt_engine import check_drift, replan as do_replan

    today_s = str(today)

    rows = [dict(r) for r in conn.execute(
        "SELECT planned_date, run_type, missed, linked_activity_id FROM planned_workout "
        "WHERE athlete_id=? ORDER BY planned_date", (athlete_id,)).fetchall()]
    if not rows:
        return

    # ACWR-historie laatste 14 dagen
    cutoff = str(today - _dt2.timedelta(days=14))
    try:
        acwr_rows = conn.execute(
            "SELECT acwr FROM training_load WHERE athlete_id=? AND date>=? ORDER BY date",
            (athlete_id, cutoff)).fetchall()
        acwr_hist = [r["acwr"] for r in acwr_rows if r["acwr"] is not None]
    except Exception:
        acwr_hist = []

    drift = check_drift(rows, today, {"acwr_history": acwr_hist})
    if not drift["drift"]:
        print(f"[adapt] {athlete_id}: geen drift.")
        return

    print(f"[adapt] {athlete_id}: drift — {drift['reason']}")

    plan_row = conn.execute(
        "SELECT * FROM training_plan WHERE athlete_id=? ORDER BY created_at DESC LIMIT 1",
        (athlete_id,)).fetchone()
    if not plan_row:
        print(f"[adapt] {athlete_id}: geen plan gevonden, overslaan.")
        return
    plan = dict(plan_row)

    fitness_row = conn.execute(
        "SELECT easy_pace_s, vo2max FROM athlete_metrics WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
        (athlete_id,)).fetchone()
    fitness = {"easy_pace_s": fitness_row["easy_pace_s"] if fitness_row else None,
               "vo2max": fitness_row["vo2max"] if fitness_row else None}

    run_days_raw = plan.get("run_days") or "mon,wed,fri,sat"
    prefs = {
        "run_days": run_days_raw.split(",") if isinstance(run_days_raw, str) else run_days_raw,
        "long_day": plan.get("long_day") or "sat",
        "hyrox_days": [],
        "strength_days": [],
    }

    new_rows = do_replan(plan, today, prefs, fitness)
    conn.execute("DELETE FROM planned_workout WHERE athlete_id=? AND planned_date>=?",
                 (athlete_id, today_s))
    for r in new_rows:
        conn.execute(
            """INSERT OR IGNORE INTO planned_workout
               (athlete_id, planned_date, week_num, run_type, title, distance_km,
                target_pace_s, segments, notes, run_day_of_week)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (athlete_id, r.get("planned_date"), r.get("week_num"), r.get("run_type"),
             r.get("title"), r.get("distance_km"), r.get("target_pace_s"),
             __import__("json").dumps(r["segments"]) if isinstance(r.get("segments"), list) else r.get("segments"),
             r.get("notes"), r.get("run_day_of_week")))
    try:
        conn.execute(
            "INSERT INTO plan_replan_log (athlete_id, replan_date, reason) VALUES (?,?,?)",
            (athlete_id, today_s, drift["reason"]))
    except Exception:
        pass  # tabel nog niet gemigreerd op oude DBs
    conn.commit()
    print(f"[adapt] {athlete_id}: replan gedaan, {len(new_rows)} rijen weggeschreven.")


def _fitness(conn, athlete_id: str) -> dict:
    rows = conn.execute(
        """SELECT distance_m, duration_s FROM activities
           WHERE athlete_id=? AND type_key='running' AND distance_m>0 ORDER BY date DESC LIMIT 20""",
        (athlete_id,)).fetchall()
    paces = [r["duration_s"] / (r["distance_m"] / 1000) for r in rows if (r["distance_m"] or 0) > 0]
    easy = round(sorted(paces)[len(paces) // 2]) if paces else None
    return {"current_easy_s": easy}


def adapt_athlete(conn, athlete_id: str) -> int:
    today = _dt.date.today().isoformat()
    window_end = (_dt.date.today() + _dt.timedelta(days=2)).isoformat()
    plan = conn.execute(
        "SELECT goal_time_s, race_distance_km FROM training_plan WHERE athlete_id=? ORDER BY id DESC LIMIT 1",
        (athlete_id,)).fetchone()
    if not plan:
        return 0
    paces = plan_engine.compute_paces(plan["goal_time_s"], plan["race_distance_km"], _fitness(conn, athlete_id).get("current_easy_s"))
    rd = conn.execute("SELECT score FROM training_readiness WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,)).fetchone()
    load = conn.execute("SELECT acwr FROM training_load_balance WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,)).fetchone()
    sl = conn.execute("SELECT duration_s, score FROM sleep WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,)).fetchone()
    signals = {"readiness": rd["score"] if rd else None, "acwr": load["acwr"] if load else None,
               "sleep_s": sl["duration_s"] if sl else None, "sleep_score": sl["score"] if sl else None,
               "recent_quality_hit": False, "downgrade_last_48h": False}
    # pas alleen het near-term venster (vandaag + 2 dagen) aan, niet-override run-dagen
    rows = conn.execute(
        "SELECT date, run_type, title, target_pace_s, distance_km, segments FROM planned_workout WHERE athlete_id=? AND date>=? AND date<=? AND user_override=0",
        (athlete_id, today, window_end)).fetchall()
    n = 0
    for r in rows:
        wo = {"run_type": r["run_type"], "title": r["title"], "target_pace_s": r["target_pace_s"],
              "distance_km": r["distance_km"], "segments": json.loads(r["segments"]) if r["segments"] else None}
        adj = adapt_engine.adjust_day(wo, signals, paces)
        if adj:
            conn.execute("""UPDATE planned_workout SET is_adjusted=1, adjusted_run_type=?, adjusted_title=?,
                   adjusted_target_pace_s=?, adjusted_segments=?, adjustment_reason=? WHERE athlete_id=? AND date=?""",
                  (adj["adjusted_run_type"], adj["adjusted_title"], adj.get("adjusted_target_pace_s"),
                   json.dumps(adj["adjusted_segments"]) if adj.get("adjusted_segments") else None,
                   adj["adjustment_reason"], athlete_id, r["date"]))
            n += 1
        else:
            conn.execute("UPDATE planned_workout SET is_adjusted=0 WHERE athlete_id=? AND date=?", (athlete_id, r["date"]))
    # markeer gemiste verleden runs
    conn.execute(
        """UPDATE planned_workout SET missed=1 WHERE athlete_id=? AND date<? AND day_type='run' AND linked_activity_id IS NULL""",
        (athlete_id, today))
    return n


def main():
    db_module.init_db()
    conn = db_module.get_conn(db_module.DB_PATH)
    for athlete_id in ATHLETES:
        n = adapt_athlete(conn, athlete_id)
        conn.commit()
        print(f"{athlete_id}: {n} dagen aangepast")
        _run_drift_and_replan(conn, athlete_id, _dt.date.today())


if __name__ == "__main__":
    main()
