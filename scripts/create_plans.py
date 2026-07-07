#!/usr/bin/env python3
"""Genereer de trainingsplannen voor Rowan (marathon) en vriendin (16 km)."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import db as db_module
import plan_engine

PLANS = [
    {"athlete_id": "rowan", "race_name": "Marathon van Amsterdam", "race_date": "2026-10-18",
     "race_distance_km": 42.195, "goal_time_s": 14400, "start_date": "2026-07-13", "weeks": 14,
     "run_days": ["mon", "thu", "sat"],
     "fixed_days": {"tue": "strength", "wed": "hyrox", "fri": "strength"}},
    {"athlete_id": "vriendin", "race_name": "NN Dam tot Damloop", "race_date": "2026-09-20",
     "race_distance_km": 16.1, "goal_time_s": None, "start_date": "2026-07-13", "weeks": 10,
     "run_days": ["wed", "sun"], "fixed_days": {}},
]


def _fitness(conn, athlete_id):
    rows = conn.execute(
        "SELECT distance_m, duration_s FROM activities WHERE athlete_id=? AND type_key='running' AND distance_m>0 ORDER BY date DESC LIMIT 20",
        (athlete_id,)).fetchall() if not db_module.use_postgres() else None
    # eenvoudig: gebruik SQLite-pad lokaal; voor Supabase draai dit script lokaal met SQLite-DB
    paces = [r["duration_s"] / (r["distance_m"] / 1000) for r in rows if (r["distance_m"] or 0) > 0] if rows else []
    longest = max([(r["distance_m"] or 0) / 1000 for r in rows], default=0) if rows else 0
    return {"current_easy_s": round(sorted(paces)[len(paces)//2]) if paces else None,
            "longest_km": round(longest) or None}


def main():
    db_module.init_db()
    conn = db_module.get_conn(db_module.DB_PATH)
    for p in PLANS:
        prefs = {"run_days": p["run_days"], "fixed_days": p["fixed_days"]}
        rows = plan_engine.generate_plan(p, prefs, _fitness(conn, p["athlete_id"]))
        conn.execute("DELETE FROM planned_workout WHERE athlete_id=?", (p["athlete_id"],))
        conn.execute("DELETE FROM training_plan WHERE athlete_id=?", (p["athlete_id"],))
        conn.execute(
            "INSERT INTO training_plan (athlete_id, race_name, race_date, race_distance_km, goal_time_s, start_date, weeks, methodology, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (p["athlete_id"], p["race_name"], p["race_date"], p["race_distance_km"], p["goal_time_s"], p["start_date"], p["weeks"], "periodized-v1", p["start_date"]))
        conn.execute(
            "INSERT INTO athlete_training_prefs (athlete_id, runs_per_week, run_days, fixed_days) VALUES (?,?,?,?) ON CONFLICT(athlete_id) DO UPDATE SET runs_per_week=excluded.runs_per_week, run_days=excluded.run_days, fixed_days=excluded.fixed_days",
            (p["athlete_id"], len(p["run_days"]), json.dumps(p["run_days"]), json.dumps(p["fixed_days"])))
        for r in rows:
            conn.execute(
                "INSERT INTO planned_workout (athlete_id, date, week_num, phase, day_type, run_type, title, distance_km, segments, target_pace_s, coach_note, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,'planned')",
                (p["athlete_id"], r["date"], r["week_num"], r["phase"], r["day_type"], r["run_type"], r["title"], r["distance_km"], json.dumps(r["segments"]) if r["segments"] else None, r["target_pace_s"], r["coach_note"]))
        conn.commit()
        print(f"{p['athlete_id']}: {len(rows)} dagen gepland")


if __name__ == "__main__":
    main()
