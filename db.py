import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")  # Supabase postgres:// URL
DB_PATH = Path(__file__).parent / "garmin_coach.db"  # local fallback

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS athletes (
    id          TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    panels_config TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS activities (
    athlete_id TEXT NOT NULL, activity_id INTEGER NOT NULL, date TEXT NOT NULL,
    name TEXT, type_key TEXT, distance_m REAL, duration_s REAL, avg_speed_mps REAL,
    avg_hr REAL, max_hr REAL, hr_zone_1_s REAL, hr_zone_2_s REAL, hr_zone_3_s REAL,
    hr_zone_4_s REAL, hr_zone_5_s REAL, aerobic_effect REAL, anaerobic_effect REAL,
    avg_cadence REAL, training_load REAL, bb_cost INTEGER, avg_stride_cm REAL,
    avg_gct_ms REAL, avg_vert_osc_mm REAL, avg_vert_ratio REAL,
    aerobic_effect_msg TEXT, training_effect_label TEXT, avg_power REAL,
    PRIMARY KEY (athlete_id, activity_id),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);
CREATE TABLE IF NOT EXISTS daily_stats (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL, steps INTEGER,
    active_calories REAL, total_calories REAL,
    PRIMARY KEY (athlete_id, date), FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);
CREATE TABLE IF NOT EXISTS daily_heart_rates (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL,
    min_hr INTEGER, max_hr INTEGER, resting_hr INTEGER,
    PRIMARY KEY (athlete_id, date), FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);
CREATE TABLE IF NOT EXISTS body_battery (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL, charged REAL, drained REAL,
    level_current INTEGER, level_high INTEGER, level_low INTEGER,
    PRIMARY KEY (athlete_id, date), FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);
CREATE TABLE IF NOT EXISTS training_readiness (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL, score INTEGER, level TEXT, feedback_short TEXT,
    PRIMARY KEY (athlete_id, date), FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);
CREATE TABLE IF NOT EXISTS vo2max (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL, vo2max REAL,
    PRIMARY KEY (athlete_id, date), FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);
CREATE TABLE IF NOT EXISTS hrv (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL,
    last_night_avg INTEGER, last_night_high INTEGER, status TEXT,
    PRIMARY KEY (athlete_id, date),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);
CREATE TABLE IF NOT EXISTS sleep (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL,
    duration_s INTEGER, deep_s INTEGER, light_s INTEGER, rem_s INTEGER, awake_s INTEGER,
    score INTEGER,
    PRIMARY KEY (athlete_id, date),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);
CREATE TABLE IF NOT EXISTS training_load_balance (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL,
    acwr REAL, acwr_percent INTEGER, acwr_status TEXT, acute_load REAL, chronic_load REAL,
    chronic_min REAL, chronic_max REAL, aerobic_low REAL, aerobic_high REAL, anaerobic REAL,
    aerobic_low_target_min REAL, aerobic_low_target_max REAL,
    aerobic_high_target_min REAL, aerobic_high_target_max REAL,
    anaerobic_target_min REAL, anaerobic_target_max REAL,
    balance_feedback TEXT, status_feedback TEXT,
    PRIMARY KEY (athlete_id, date), FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);
CREATE TABLE IF NOT EXISTS activity_splits (
    athlete_id TEXT NOT NULL, activity_id INTEGER NOT NULL, split_num INTEGER NOT NULL,
    distance_m REAL, duration_s REAL, avg_hr REAL, avg_speed_mps REAL,
    PRIMARY KEY (athlete_id, activity_id, split_num),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);
CREATE TABLE IF NOT EXISTS athlete_training_prefs (
    athlete_id TEXT PRIMARY KEY,
    runs_per_week INTEGER, run_days TEXT, fixed_days TEXT,
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);
CREATE TABLE IF NOT EXISTS training_plan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id TEXT NOT NULL, race_name TEXT, race_date TEXT,
    race_distance_km REAL, goal_time_s INTEGER, start_date TEXT,
    weeks INTEGER, methodology TEXT DEFAULT 'periodized-v1', created_at TEXT,
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);
CREATE TABLE IF NOT EXISTS planned_workout (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL, plan_id INTEGER,
    week_num INTEGER, phase TEXT, day_type TEXT, run_type TEXT,
    title TEXT, distance_km REAL, segments TEXT, target_pace_s INTEGER,
    coach_note TEXT, status TEXT DEFAULT 'planned', linked_activity_id INTEGER,
    PRIMARY KEY (athlete_id, date),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);
"""

SCHEMA_PG = """
-- NOTE: keep in sync with SCHEMA_SQLITE (same tables, BIGINT activity_id, no FK constraints)
CREATE TABLE IF NOT EXISTS athletes (
    id          TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    panels_config TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS activities (
    athlete_id TEXT NOT NULL, activity_id BIGINT NOT NULL, date TEXT NOT NULL,
    name TEXT, type_key TEXT, distance_m REAL, duration_s REAL, avg_speed_mps REAL,
    avg_hr REAL, max_hr REAL, hr_zone_1_s REAL, hr_zone_2_s REAL, hr_zone_3_s REAL,
    hr_zone_4_s REAL, hr_zone_5_s REAL, aerobic_effect REAL, anaerobic_effect REAL,
    avg_cadence REAL, training_load REAL, bb_cost INTEGER, avg_stride_cm REAL,
    avg_gct_ms REAL, avg_vert_osc_mm REAL, avg_vert_ratio REAL,
    aerobic_effect_msg TEXT, training_effect_label TEXT, avg_power REAL,
    PRIMARY KEY (athlete_id, activity_id)
);
CREATE TABLE IF NOT EXISTS daily_stats (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL, steps INTEGER,
    active_calories REAL, total_calories REAL, PRIMARY KEY (athlete_id, date)
);
CREATE TABLE IF NOT EXISTS daily_heart_rates (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL,
    min_hr INTEGER, max_hr INTEGER, resting_hr INTEGER, PRIMARY KEY (athlete_id, date)
);
CREATE TABLE IF NOT EXISTS body_battery (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL, charged REAL, drained REAL,
    level_current INTEGER, level_high INTEGER, level_low INTEGER,
    PRIMARY KEY (athlete_id, date)
);
CREATE TABLE IF NOT EXISTS training_readiness (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL, score INTEGER, level TEXT, feedback_short TEXT,
    PRIMARY KEY (athlete_id, date)
);
CREATE TABLE IF NOT EXISTS vo2max (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL, vo2max REAL,
    PRIMARY KEY (athlete_id, date)
);
CREATE TABLE IF NOT EXISTS hrv (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL,
    last_night_avg INTEGER, last_night_high INTEGER, status TEXT,
    PRIMARY KEY (athlete_id, date)
);
CREATE TABLE IF NOT EXISTS sleep (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL,
    duration_s INTEGER, deep_s INTEGER, light_s INTEGER, rem_s INTEGER, awake_s INTEGER,
    score INTEGER,
    PRIMARY KEY (athlete_id, date)
);
CREATE TABLE IF NOT EXISTS training_load_balance (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL,
    acwr REAL, acwr_percent INTEGER, acwr_status TEXT, acute_load REAL, chronic_load REAL,
    chronic_min REAL, chronic_max REAL, aerobic_low REAL, aerobic_high REAL, anaerobic REAL,
    aerobic_low_target_min REAL, aerobic_low_target_max REAL,
    aerobic_high_target_min REAL, aerobic_high_target_max REAL,
    anaerobic_target_min REAL, anaerobic_target_max REAL,
    balance_feedback TEXT, status_feedback TEXT,
    PRIMARY KEY (athlete_id, date)
);
CREATE TABLE IF NOT EXISTS activity_splits (
    athlete_id TEXT NOT NULL, activity_id BIGINT NOT NULL, split_num INTEGER NOT NULL,
    distance_m REAL, duration_s REAL, avg_hr REAL, avg_speed_mps REAL,
    PRIMARY KEY (athlete_id, activity_id, split_num)
);
CREATE TABLE IF NOT EXISTS athlete_training_prefs (
    athlete_id TEXT PRIMARY KEY,
    runs_per_week INTEGER, run_days TEXT, fixed_days TEXT
);
CREATE TABLE IF NOT EXISTS training_plan (
    id SERIAL PRIMARY KEY,
    athlete_id TEXT NOT NULL, race_name TEXT, race_date TEXT,
    race_distance_km REAL, goal_time_s INTEGER, start_date TEXT,
    weeks INTEGER, methodology TEXT DEFAULT 'periodized-v1', created_at TEXT
);
CREATE TABLE IF NOT EXISTS planned_workout (
    athlete_id TEXT NOT NULL, date TEXT NOT NULL, plan_id INTEGER,
    week_num INTEGER, phase TEXT, day_type TEXT, run_type TEXT,
    title TEXT, distance_km REAL, segments TEXT, target_pace_s INTEGER,
    coach_note TEXT, status TEXT DEFAULT 'planned', linked_activity_id INTEGER,
    PRIMARY KEY (athlete_id, date)
);
"""

ACTIVITY_NEW_COLUMNS = [
    ("training_load",         "REAL"),
    ("bb_cost",               "INTEGER"),
    ("avg_stride_cm",         "REAL"),
    ("avg_gct_ms",            "REAL"),
    ("avg_vert_osc_mm",       "REAL"),
    ("avg_vert_ratio",        "REAL"),
    ("aerobic_effect_msg",    "TEXT"),
    ("training_effect_label", "TEXT"),
    ("avg_power",             "REAL"),
]

BODY_BATTERY_NEW_COLUMNS = [
    ("level_current", "INTEGER"),
    ("level_high", "INTEGER"),
    ("level_low", "INTEGER"),
]


def use_postgres() -> bool:
    return bool(DATABASE_URL)


def get_pg_conn():
    import psycopg2
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def get_conn(path: Path = DB_PATH) -> sqlite3.Connection:
    """Return SQLite connection (local dev only)."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(path: Path = DB_PATH) -> None:
    if use_postgres():
        _init_pg()
    else:
        _init_sqlite(path)


def _init_pg() -> None:
    conn = get_pg_conn()
    try:
        with conn.cursor() as cur:
            for stmt in SCHEMA_PG.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
        conn.commit()
    finally:
        conn.close()


def _init_sqlite(path: Path) -> None:
    with get_conn(path) as conn:
        conn.executescript(SCHEMA_SQLITE)
    _migrate_activities(path)
    _migrate_body_battery(path)


def _migrate_activities(path: Path) -> None:
    with get_conn(path) as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(activities)").fetchall()}
        for col, col_type in ACTIVITY_NEW_COLUMNS:
            if col not in existing:
                conn.execute(f"ALTER TABLE activities ADD COLUMN {col} {col_type}")
        conn.commit()


def _migrate_body_battery(path: Path) -> None:
    with get_conn(path) as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(body_battery)").fetchall()}
        for col, col_type in BODY_BATTERY_NEW_COLUMNS:
            if col not in existing:
                conn.execute(f"ALTER TABLE body_battery ADD COLUMN {col} {col_type}")
        conn.commit()
