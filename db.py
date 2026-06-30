import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "garmin_coach.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS athletes (
    id          TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    panels_config TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS activities (
    athlete_id   TEXT NOT NULL,
    activity_id  INTEGER NOT NULL,
    date         TEXT NOT NULL,
    name         TEXT,
    type_key     TEXT,
    distance_m   REAL,
    duration_s   REAL,
    avg_speed_mps REAL,
    avg_hr       REAL,
    max_hr       REAL,
    hr_zone_1_s  REAL,
    hr_zone_2_s  REAL,
    hr_zone_3_s  REAL,
    hr_zone_4_s  REAL,
    hr_zone_5_s  REAL,
    aerobic_effect   REAL,
    anaerobic_effect REAL,
    avg_cadence  REAL,
    training_load    REAL,
    bb_cost          INTEGER,
    avg_stride_cm    REAL,
    avg_gct_ms       REAL,
    avg_vert_osc_mm  REAL,
    avg_vert_ratio   REAL,
    aerobic_effect_msg   TEXT,
    training_effect_label TEXT,
    avg_power        REAL,
    PRIMARY KEY (athlete_id, activity_id),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);

CREATE TABLE IF NOT EXISTS daily_stats (
    athlete_id     TEXT NOT NULL,
    date           TEXT NOT NULL,
    steps          INTEGER,
    active_calories REAL,
    total_calories REAL,
    PRIMARY KEY (athlete_id, date),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);

CREATE TABLE IF NOT EXISTS daily_heart_rates (
    athlete_id  TEXT NOT NULL,
    date        TEXT NOT NULL,
    min_hr      INTEGER,
    max_hr      INTEGER,
    resting_hr  INTEGER,
    PRIMARY KEY (athlete_id, date),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);

CREATE TABLE IF NOT EXISTS body_battery (
    athlete_id TEXT NOT NULL,
    date       TEXT NOT NULL,
    charged    REAL,
    drained    REAL,
    PRIMARY KEY (athlete_id, date),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);

CREATE TABLE IF NOT EXISTS training_readiness (
    athlete_id     TEXT NOT NULL,
    date           TEXT NOT NULL,
    score          INTEGER,
    level          TEXT,
    feedback_short TEXT,
    PRIMARY KEY (athlete_id, date),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);

CREATE TABLE IF NOT EXISTS vo2max (
    athlete_id TEXT NOT NULL,
    date       TEXT NOT NULL,
    vo2max     REAL,
    PRIMARY KEY (athlete_id, date),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);

CREATE TABLE IF NOT EXISTS training_load_balance (
    athlete_id          TEXT NOT NULL,
    date                TEXT NOT NULL,
    acwr                REAL,
    acwr_percent        INTEGER,
    acwr_status         TEXT,
    acute_load          REAL,
    chronic_load        REAL,
    chronic_min         REAL,
    chronic_max         REAL,
    aerobic_low         REAL,
    aerobic_high        REAL,
    anaerobic           REAL,
    aerobic_low_target_min  REAL,
    aerobic_low_target_max  REAL,
    aerobic_high_target_min REAL,
    aerobic_high_target_max REAL,
    anaerobic_target_min    REAL,
    anaerobic_target_max    REAL,
    balance_feedback    TEXT,
    status_feedback     TEXT,
    PRIMARY KEY (athlete_id, date),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
);

CREATE TABLE IF NOT EXISTS activity_splits (
    athlete_id   TEXT NOT NULL,
    activity_id  INTEGER NOT NULL,
    split_num    INTEGER NOT NULL,
    distance_m   REAL,
    duration_s   REAL,
    avg_hr       REAL,
    avg_speed_mps REAL,
    PRIMARY KEY (athlete_id, activity_id, split_num),
    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
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


def get_conn(path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(path: Path = DB_PATH) -> None:
    with get_conn(path) as conn:
        conn.executescript(SCHEMA)
    _migrate_activities(path)


def _migrate_activities(path: Path) -> None:
    """Add new columns to activities for existing databases (idempotent)."""
    with get_conn(path) as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(activities)").fetchall()}
        for col, col_type in ACTIVITY_NEW_COLUMNS:
            if col not in existing:
                conn.execute(f"ALTER TABLE activities ADD COLUMN {col} {col_type}")
        conn.commit()
