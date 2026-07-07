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


if __name__ == "__main__":
    main()
