# Garmin Dashboard Fase 2: Runna-stijl Extension

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Breid het Garmin dashboard uit met aandachtspunten, training load analyse, loopefficiëntie trends, per-km splits en uitgebreide runs tabel.

**Architecture:** Voeg 2 nieuwe SQLite tabellen toe + 9 nieuwe columns op activities via ALTER TABLE migration. Vier nieuwe FastAPI endpoints. Vier nieuwe React componenten. RecentRuns uitgebreid. CoachCard vervangen door echte data.

**Tech Stack:** Python 3.11+, SQLite, FastAPI, React 18, recharts, lucide-react

---

## File Structure

**Modify (backend):**
- `db.py` — `migrate_db()` functie, `training_load_balance` + `activity_splits` tabellen
- `ingest.py` — nieuwe velden in `ingest_activities`, plus `ingest_training_load_balance`, `ingest_activity_splits`
- `api/routes.py` — 4 nieuwe endpoints + /runs uitbreiden
- `garmin_test_pull.py` — splits fetch per run activity

**Modify (frontend):**
- `dashboard/src/api.js` — 4 nieuwe api calls
- `dashboard/src/App.jsx` — nieuwe Promise.all calls, nieuwe panelen, panels_config update
- `dashboard/src/components/RecentRuns.jsx` — 3 nieuwe kolommen

**Create (frontend):**
- `dashboard/src/components/AttentionPoints.jsx`
- `dashboard/src/components/TrainingLoad.jsx`
- `dashboard/src/components/RunEfficiency.jsx`
- `dashboard/src/components/SplitsPanel.jsx`

**Modify (tests):**
- `tests/test_ingest.py` — tests voor 2 nieuwe ingest functies
- `tests/test_api.py` — tests voor 4 nieuwe endpoints

---

## Task 1: DB schema migration

**Files:**
- Modify: `db.py`

Voeg `migrate_db()` toe die ontbrekende columns toevoegt aan `activities` en 2 nieuwe tabellen aanmaakt.

- [ ] **Step 1: Open en lees het huidige db.py**

Check dat je de volledige SCHEMA string + get_conn + init_db ziet.

- [ ] **Step 2: Voeg MIGRATION_SQL en migrate_db() toe**

Vervang de inhoud van `db.py` met:

```python
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
```

- [ ] **Step 3: Schrijf de failing test**

In `tests/test_ingest.py`, update `test_schema_creates_all_tables`:

```python
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
```

En voeg een nieuwe test toe:

```python
def test_activities_has_new_columns():
    p = make_tmp_db()
    conn = get_conn(p)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(activities)").fetchall()}
    for col in ["training_load", "bb_cost", "avg_stride_cm", "avg_gct_ms",
                "avg_vert_osc_mm", "avg_vert_ratio", "aerobic_effect_msg",
                "training_effect_label", "avg_power"]:
        assert col in cols, f"Missing column: {col}"
    p.unlink()
```

- [ ] **Step 4: Run tests**

```bash
cd ~/Documents/garmin-coach && source .venv/bin/activate
pytest tests/test_ingest.py::test_schema_creates_all_tables tests/test_ingest.py::test_activities_has_new_columns -v
```

Expected: beide PASS

- [ ] **Step 5: Test bestaande DB migration**

```bash
python3 -c "from db import init_db; init_db(); print('migration OK')"
```

Expected: `migration OK` zonder errors

- [ ] **Step 6: Commit**

```bash
git add db.py tests/test_ingest.py
git commit -m "feat: fase2 — DB migration, training_load_balance + activity_splits tables + 9 new activity columns"
```

---

## Task 2: garmin_test_pull.py — splits fetch

**Files:**
- Modify: `garmin_test_pull.py`

Voeg splits fetch toe voor alle hardloopactiviteiten.

- [ ] **Step 1: Voeg splits fetch toe na de activiteiten fetch**

Zoek de sectie `# --- Write JSON ---` in `garmin_test_pull.py`. Voeg ná de activities fetch en vóór de per-day endpoints dit toe:

```python
    # --- Splits per hardloopactiviteit ---
    running_ids = [
        a["activityId"]
        for a in (activities or [])
        if (a.get("activityType") or {}).get("typeKey") == "running"
    ]
    print(f"\nFetching splits for {len(running_ids)} runs...")
    for act_id in running_ids:
        splits = fetch(f"splits {act_id}", client.get_activity_splits, act_id)
        if splits is not None:
            (out / f"splits_{act_id}.json").write_text(
                json.dumps(splits, indent=2, ensure_ascii=False)
            )
```

Zet dit direct ná de `body_battery = fetch(...)` regel, vóór de `# --- Per-day endpoints ---` sectie.

- [ ] **Step 2: Voeg splits bestanden toe aan de write-sectie**

In het `files = {...}` blok, NIET wijzigen — splits worden al per loop geschreven. Check dat het blok er zo uitziet (geen wijziging nodig):

```python
    files = {
        "activities.json":          activities,
        "body_battery.json":        body_battery,
        "stats.json":               stats,
        "heart_rates.json":         heart_rates,
        "sleep.json":               sleep,
        "hrv.json":                 hrv,
        "training_readiness.json":  training_readiness,
        "training_status.json":     training_status,
    }
```

- [ ] **Step 3: Verify syntaxis**

```bash
cd ~/Documents/garmin-coach && python3 -c "import garmin_test_pull; print('syntax OK')"
```

Expected: `syntax OK`

- [ ] **Step 4: Commit**

```bash
git add garmin_test_pull.py
git commit -m "feat: fase2 — fetch splits per run activity in garmin_test_pull"
```

---

## Task 3: ingest.py — nieuwe velden + training_load_balance + activity_splits

**Files:**
- Modify: `ingest.py`

Drie uitbreidingen: (1) nieuwe activity fields, (2) training_load_balance ingest, (3) activity_splits ingest.

- [ ] **Step 1: Update ingest_activities — nieuwe fields opslaan**

Vervang de complete `ingest_activities` functie:

```python
def ingest_activities(conn: sqlite3.Connection, athlete_id: str, data: list) -> int:
    count = 0
    for a in data:
        date = (a.get("startTimeLocal") or "")[:10]
        conn.execute(
            """
            INSERT INTO activities (
                athlete_id, activity_id, date, name, type_key,
                distance_m, duration_s, avg_speed_mps, avg_hr, max_hr,
                hr_zone_1_s, hr_zone_2_s, hr_zone_3_s, hr_zone_4_s, hr_zone_5_s,
                aerobic_effect, anaerobic_effect, avg_cadence,
                training_load, bb_cost, avg_stride_cm, avg_gct_ms,
                avg_vert_osc_mm, avg_vert_ratio, aerobic_effect_msg,
                training_effect_label, avg_power
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(athlete_id, activity_id) DO UPDATE SET
                date=excluded.date, name=excluded.name, type_key=excluded.type_key,
                distance_m=excluded.distance_m, duration_s=excluded.duration_s,
                avg_speed_mps=excluded.avg_speed_mps, avg_hr=excluded.avg_hr,
                max_hr=excluded.max_hr,
                hr_zone_1_s=excluded.hr_zone_1_s, hr_zone_2_s=excluded.hr_zone_2_s,
                hr_zone_3_s=excluded.hr_zone_3_s, hr_zone_4_s=excluded.hr_zone_4_s,
                hr_zone_5_s=excluded.hr_zone_5_s,
                aerobic_effect=excluded.aerobic_effect,
                anaerobic_effect=excluded.anaerobic_effect,
                avg_cadence=excluded.avg_cadence,
                training_load=excluded.training_load, bb_cost=excluded.bb_cost,
                avg_stride_cm=excluded.avg_stride_cm, avg_gct_ms=excluded.avg_gct_ms,
                avg_vert_osc_mm=excluded.avg_vert_osc_mm,
                avg_vert_ratio=excluded.avg_vert_ratio,
                aerobic_effect_msg=excluded.aerobic_effect_msg,
                training_effect_label=excluded.training_effect_label,
                avg_power=excluded.avg_power
            """,
            (
                athlete_id,
                a.get("activityId"),
                date,
                a.get("activityName"),
                (a.get("activityType") or {}).get("typeKey"),
                a.get("distance"),
                a.get("duration"),
                a.get("averageSpeed"),
                a.get("averageHR"),
                a.get("maxHR"),
                a.get("hrTimeInZone_1"),
                a.get("hrTimeInZone_2"),
                a.get("hrTimeInZone_3"),
                a.get("hrTimeInZone_4"),
                a.get("hrTimeInZone_5"),
                a.get("aerobicTrainingEffect"),
                a.get("anaerobicTrainingEffect"),
                a.get("averageRunningCadenceInStepsPerMinute"),
                a.get("activityTrainingLoad"),
                a.get("differenceBodyBattery"),
                a.get("avgStrideLength"),
                a.get("avgGroundContactTime"),
                a.get("avgVerticalOscillation"),
                a.get("avgVerticalRatio"),
                a.get("aerobicTrainingEffectMessage"),
                a.get("trainingEffectLabel"),
                a.get("avgPower"),
            ),
        )
        count += 1
    conn.commit()
    return count
```

- [ ] **Step 2: Voeg ingest_training_load_balance toe**

Voeg deze functie toe vóór `run_ingest`:

```python
def ingest_training_load_balance(conn: sqlite3.Connection, athlete_id: str, data: dict) -> int:
    count = 0
    for date, row in data.items():
        if not row:
            continue

        # ACWR data — uit mostRecentTrainingStatus per primair device
        acwr: dict = {}
        status_feedback = None
        status_map = (row.get("mostRecentTrainingStatus") or {}).get("latestTrainingStatusData") or {}
        for device_data in status_map.values():
            if device_data.get("primaryTrainingDevice"):
                acwr = device_data.get("acuteTrainingLoadDTO") or {}
                status_feedback = device_data.get("trainingStatusFeedbackPhrase")
                break

        # Balans data — uit mostRecentTrainingLoadBalance per primair device
        bal: dict = {}
        balance_feedback = None
        balance_map = (
            (row.get("mostRecentTrainingLoadBalance") or {})
            .get("metricsTrainingLoadBalanceDTOMap") or {}
        )
        for device_data in balance_map.values():
            if device_data.get("primaryTrainingDevice"):
                bal = device_data
                balance_feedback = device_data.get("trainingBalanceFeedbackPhrase")
                break

        conn.execute(
            """
            INSERT INTO training_load_balance (
                athlete_id, date, acwr, acwr_percent, acwr_status,
                acute_load, chronic_load, chronic_min, chronic_max,
                aerobic_low, aerobic_high, anaerobic,
                aerobic_low_target_min, aerobic_low_target_max,
                aerobic_high_target_min, aerobic_high_target_max,
                anaerobic_target_min, anaerobic_target_max,
                balance_feedback, status_feedback
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
                acwr=excluded.acwr, acwr_percent=excluded.acwr_percent,
                acwr_status=excluded.acwr_status,
                acute_load=excluded.acute_load, chronic_load=excluded.chronic_load,
                chronic_min=excluded.chronic_min, chronic_max=excluded.chronic_max,
                aerobic_low=excluded.aerobic_low, aerobic_high=excluded.aerobic_high,
                anaerobic=excluded.anaerobic,
                aerobic_low_target_min=excluded.aerobic_low_target_min,
                aerobic_low_target_max=excluded.aerobic_low_target_max,
                aerobic_high_target_min=excluded.aerobic_high_target_min,
                aerobic_high_target_max=excluded.aerobic_high_target_max,
                anaerobic_target_min=excluded.anaerobic_target_min,
                anaerobic_target_max=excluded.anaerobic_target_max,
                balance_feedback=excluded.balance_feedback,
                status_feedback=excluded.status_feedback
            """,
            (
                athlete_id, date,
                acwr.get("dailyAcuteChronicWorkloadRatio"),
                acwr.get("acwrPercent"),
                acwr.get("acwrStatus"),
                acwr.get("dailyTrainingLoadAcute"),
                acwr.get("dailyTrainingLoadChronic"),
                acwr.get("minTrainingLoadChronic"),
                acwr.get("maxTrainingLoadChronic"),
                bal.get("monthlyLoadAerobicLow"),
                bal.get("monthlyLoadAerobicHigh"),
                bal.get("monthlyLoadAnaerobic"),
                bal.get("monthlyLoadAerobicLowTargetMin"),
                bal.get("monthlyLoadAerobicLowTargetMax"),
                bal.get("monthlyLoadAerobicHighTargetMin"),
                bal.get("monthlyLoadAerobicHighTargetMax"),
                bal.get("monthlyLoadAnaerobicTargetMin"),
                bal.get("monthlyLoadAnaerobicTargetMax"),
                balance_feedback,
                status_feedback,
            ),
        )
        count += 1
    conn.commit()
    return count
```

- [ ] **Step 3: Voeg ingest_activity_splits toe**

Voeg direct na `ingest_training_load_balance` toe:

```python
def ingest_activity_splits(conn: sqlite3.Connection, athlete_id: str, activity_id: int, data: dict) -> int:
    """Ingest lap splits voor één activiteit. data = JSON van get_activity_splits()."""
    laps = data.get("lapDTOs") or data.get("laps") or []
    count = 0
    for lap in laps:
        split_num = (lap.get("lapIndex") or 0) + 1
        conn.execute(
            """
            INSERT INTO activity_splits (athlete_id, activity_id, split_num, distance_m, duration_s, avg_hr, avg_speed_mps)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(athlete_id, activity_id, split_num) DO UPDATE SET
                distance_m=excluded.distance_m, duration_s=excluded.duration_s,
                avg_hr=excluded.avg_hr, avg_speed_mps=excluded.avg_speed_mps
            """,
            (
                athlete_id, activity_id, split_num,
                lap.get("distance"),
                lap.get("duration"),
                lap.get("averageHR"),
                lap.get("averageSpeed"),
            ),
        )
        count += 1
    conn.commit()
    return count
```

- [ ] **Step 4: Update run_ingest om nieuwe functies te roepen**

Vervang in `run_ingest` de sectie die training_status verwerkt met:

```python
    ts = load("training_status.json") or {}
    print(f"  vo2max: {ingest_vo2max_from_training_status(conn, athlete_id, ts)}")
    print(f"  training_load_balance: {ingest_training_load_balance(conn, athlete_id, ts)}")

    # Splits per activiteit — verwerk alle splits_<id>.json bestanden
    splits_files = list(output_dir.glob("splits_*.json"))
    total_splits = 0
    for sf in splits_files:
        try:
            act_id = int(sf.stem.replace("splits_", ""))
            total_splits += ingest_activity_splits(conn, athlete_id, act_id, json.loads(sf.read_text()))
        except (ValueError, json.JSONDecodeError):
            pass
    print(f"  activity_splits: {total_splits} laps over {len(splits_files)} runs")
```

- [ ] **Step 5: Schrijf failing tests**

Voeg toe aan `tests/test_ingest.py`:

```python
from ingest import ingest_training_load_balance, ingest_activity_splits

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
    activities_with_new = SAMPLE_ACTIVITIES.copy()
    activities_with_new[0] = {
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
    ingest_activities(conn, "vriendin", activities_with_new)
    row = conn.execute("SELECT training_load, bb_cost, avg_power FROM activities").fetchone()
    assert abs(row["training_load"] - 149.8) < 0.1
    assert row["bb_cost"] == -9
    assert row["avg_power"] == 248.0
    p.unlink()
```

- [ ] **Step 6: Run tests**

```bash
cd ~/Documents/garmin-coach && source .venv/bin/activate
pytest tests/test_ingest.py -v
```

Expected: alle tests PASS (inclusief bestaande)

- [ ] **Step 7: Re-ingest data**

```bash
cd ~/Documents/garmin-coach && source .venv/bin/activate
python3 ingest.py --athlete vriendin --name Vriendin
```

Expected: output toont nieuwe regels `training_load_balance: N` en `activity_splits: 0 laps over 0 runs` (0 omdat nog geen splits_*.json bestanden aanwezig zijn van bestaande fetch)

- [ ] **Step 8: Commit**

```bash
git add ingest.py tests/test_ingest.py
git commit -m "feat: fase2 — ingest nieuwe activity fields, training_load_balance, activity_splits"
```

---

## Task 4: API routes — 4 nieuwe endpoints + /runs uitbreiden

**Files:**
- Modify: `api/routes.py`

- [ ] **Step 1: Voeg attention_points constanten toe bovenaan routes.py**

Voeg toe direct ná de imports:

```python
_BALANCE_MSGS: dict[str, tuple[str, str]] = {
    "AEROBIC_LOW_SHORTAGE":  ("warning", "Te weinig rustige training. Voeg Z1/Z2 duurlopen toe."),
    "AEROBIC_HIGH_SHORTAGE": ("info",    "Minder intensieve training dan aanbevolen. Overweeg een tempoloop."),
    "ANAEROBIC_SHORTAGE":    ("info",    "Weinig anaëroob werk. Korte sprints kunnen helpen."),
    "ANAEROBIC_EXCESS":      ("warning", "Te veel intensief werk. Plan een rustdag of herstelloop."),
    "AEROBIC_HIGH_EXCESS":   ("warning", "Veel intensieve training. Bouw af voor blessurepreventie."),
    "BALANCED":              ("info",    "Training is goed in balans."),
}
```

- [ ] **Step 2: Extend /runs endpoint — voeg nieuwe velden toe**

Vervang de volledige `get_runs` functie:

```python
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
```

- [ ] **Step 3: Voeg /training_load endpoint toe**

Voeg toe vóór `get_daily_stats`:

```python
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
```

- [ ] **Step 4: Voeg /run_efficiency endpoint toe**

```python
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
```

- [ ] **Step 5: Voeg /attention_points endpoint toe**

```python
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
```

- [ ] **Step 6: Voeg /activity/{activity_id}/splits endpoint toe**

```python
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
```

- [ ] **Step 7: Schrijf failing tests**

Voeg toe aan `tests/test_api.py`. Update eerst de setup fixture om training_load_balance data te bevatten:

```python
from ingest import ingest_training_load_balance, ingest_activity_splits

# In setup_db fixture, voeg toe na de bestaande ingest calls:
#     ingest_training_load_balance(conn, "vriendin", {
#         "2026-06-20": {
#             "mostRecentTrainingStatus": {
#                 "latestTrainingStatusData": {
#                     "dev1": {
#                         "primaryTrainingDevice": True,
#                         "trainingStatusFeedbackPhrase": "MAINTAINING_2",
#                         "acuteTrainingLoadDTO": {
#                             "acwrPercent": 38,
#                             "acwrStatus": "OPTIMAL",
#                             "dailyTrainingLoadAcute": 212.0,
#                             "maxTrainingLoadChronic": 328.5,
#                             "minTrainingLoadChronic": 175.2,
#                             "dailyTrainingLoadChronic": 219.0,
#                             "dailyAcuteChronicWorkloadRatio": 0.9,
#                         },
#                     }
#                 }
#             },
#             "mostRecentTrainingLoadBalance": {
#                 "metricsTrainingLoadBalanceDTOMap": {
#                     "dev1": {
#                         "primaryTrainingDevice": True,
#                         "monthlyLoadAerobicLow": 19.4,
#                         "monthlyLoadAerobicHigh": 745.2,
#                         "monthlyLoadAnaerobic": 16.6,
#                         "monthlyLoadAerobicLowTargetMin": 219,
#                         "monthlyLoadAerobicLowTargetMax": 481,
#                         "monthlyLoadAerobicHighTargetMin": 262,
#                         "monthlyLoadAerobicHighTargetMax": 525,
#                         "monthlyLoadAnaerobicTargetMin": 0,
#                         "monthlyLoadAnaerobicTargetMax": 262,
#                         "trainingBalanceFeedbackPhrase": "AEROBIC_LOW_SHORTAGE",
#                     }
#                 }
#             },
#         }
#     })
#     ingest_activity_splits(conn, "vriendin", 1001, {
#         "lapDTOs": [
#             {"lapIndex": 0, "distance": 1000.0, "duration": 325.0, "averageHR": 158.0, "averageSpeed": 3.08},
#             {"lapIndex": 1, "distance": 1000.0, "duration": 330.0, "averageHR": 162.0, "averageSpeed": 3.03},
#         ]
#     })
```

Paste de daadwerkelijke fixture update (verwijder de comment-tags en voeg de calls toe aan de echte fixture body), en voeg dan de tests toe:

```python
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
    # may be empty if no gct/cadence data but should not 500


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
```

**Pas de setup fixture aan** — open `tests/test_api.py`, zoek de `setup_db` fixture en voeg de twee ingest calls toe:

In de `yield`-regel erboven:

```python
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
```

En in `executescript` teardown, voeg toe:
```python
DELETE FROM training_load_balance; DELETE FROM activity_splits;
```

- [ ] **Step 8: Run alle API tests**

```bash
cd ~/Documents/garmin-coach && source .venv/bin/activate
pytest tests/test_api.py -v
```

Expected: alle tests PASS

- [ ] **Step 9: Commit**

```bash
git add api/routes.py tests/test_api.py
git commit -m "feat: fase2 — 4 nieuwe API endpoints (training_load, attention_points, run_efficiency, splits) + /runs uitbreiden"
```

---

## Task 5: AttentionPoints component

**Files:**
- Create: `dashboard/src/components/AttentionPoints.jsx`

- [ ] **Step 1: Maak het component**

```jsx
import { AlertTriangle, Info } from 'lucide-react'

export default function AttentionPoints({ data }) {
  const points = data.attentionPoints || []

  if (points.length === 0) {
    return null
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {points.map((p, i) => {
        const isWarning = p.level === 'warning'
        const color = isWarning ? 'var(--orange)' : 'var(--accent2)'
        const Icon = isWarning ? AlertTriangle : Info
        return (
          <div
            key={i}
            style={{
              background: 'var(--bg-card)',
              border: `1px solid var(--border)`,
              borderLeft: `4px solid ${color}`,
              borderRadius: 10,
              padding: '12px 16px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: 12,
            }}
          >
            <Icon size={18} color={color} style={{ flexShrink: 0, marginTop: 1 }} />
            <span style={{ color: 'var(--text-1)', fontSize: 14, lineHeight: 1.5 }}>
              {p.message}
            </span>
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 2: Verify syntaxis**

```bash
cd ~/Documents/garmin-coach/dashboard && node --input-type=module <<'EOF'
import { readFileSync } from 'fs'
readFileSync('src/components/AttentionPoints.jsx', 'utf8')
console.log('syntax check OK')
EOF
```

Expected: `syntax check OK`

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/AttentionPoints.jsx
git commit -m "feat: fase2 — AttentionPoints component"
```

---

## Task 6: TrainingLoad component

**Files:**
- Create: `dashboard/src/components/TrainingLoad.jsx`

- [ ] **Step 1: Maak het component**

```jsx
import { BarChart, Bar, XAxis, YAxis, ReferenceLine, ResponsiveContainer, Cell } from 'recharts'

function AcwrGauge({ acwr }) {
  const ratio = acwr ?? 0
  const clamped = Math.min(Math.max(ratio, 0), 2)
  const angle = (clamped / 2) * 180 - 90
  const rad = (angle * Math.PI) / 180
  const r = 60
  const cx = 80
  const cy = 80
  const nx = cx + r * Math.cos(rad)
  const ny = cy + r * Math.sin(rad)

  const zoneColor =
    ratio > 1.5 ? 'var(--red)'
    : ratio > 1.3 ? 'var(--orange)'
    : ratio >= 0.8 ? 'var(--green)'
    : 'var(--accent2)'

  return (
    <svg width={160} height={100} viewBox="0 0 160 100">
      {/* background arc zones */}
      {[
        { start: -180, end: -108, color: 'var(--accent2)', opacity: 0.3 }, // 0-0.8
        { start: -108, end:   27, color: 'var(--green)',   opacity: 0.3 }, // 0.8-1.3
        { start:   27, end:   54, color: 'var(--orange)',  opacity: 0.3 }, // 1.3-1.5
        { start:   54, end:   90, color: 'var(--red)',     opacity: 0.3 }, // 1.5-2.0
      ].map((zone, i) => {
        const r1 = (zone.start * Math.PI) / 180
        const r2 = (zone.end * Math.PI) / 180
        const x1 = cx + r * Math.cos(r1), y1 = cy + r * Math.sin(r1)
        const x2 = cx + r * Math.cos(r2), y2 = cy + r * Math.sin(r2)
        const large = Math.abs(zone.end - zone.start) > 90 ? 1 : 0
        return (
          <path
            key={i}
            d={`M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${large},1 ${x2},${y2} Z`}
            fill={zone.color}
            opacity={zone.opacity}
          />
        )
      })}
      {/* needle */}
      <line
        x1={cx} y1={cy}
        x2={nx} y2={ny}
        stroke={zoneColor}
        strokeWidth={3}
        strokeLinecap="round"
      />
      <circle cx={cx} cy={cy} r={5} fill={zoneColor} />
      {/* ratio label */}
      <text x={cx} y={cy - 14} textAnchor="middle" fill="var(--text-1)" fontSize={15} fontWeight={700}>
        {ratio.toFixed(2)}
      </text>
      <text x={cx} y={cy - 2} textAnchor="middle" fill="var(--text-3)" fontSize={9}>
        ACWR
      </text>
    </svg>
  )
}

const ZONE_LABELS = {
  aerobic_low:  'Aëroob Laag (Z1/Z2)',
  aerobic_high: 'Aëroob Hoog (Z3/Z4)',
  anaerobic:    'Anaëroob (Z5)',
}

export default function TrainingLoad({ data }) {
  const tl = data.trainingLoad || {}
  const latest = tl.latest
  const balance = tl.balance

  if (!latest) {
    return (
      <div className="card">
        <span className="label">Training Load</span>
        <p className="no-data">Geen training load data</p>
      </div>
    )
  }

  const barData = balance
    ? Object.entries(ZONE_LABELS).map(([key, label]) => {
        const z = balance[key] || {}
        const actual = Math.round(z.actual ?? 0)
        const tmin = z.target_min ?? 0
        const tmax = z.target_max ?? 0
        const inTarget = actual >= tmin && actual <= tmax
        return { label, actual, tmin, tmax, inTarget }
      })
    : []

  return (
    <div className="card">
      <span className="label">Training Load</span>
      <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* Left: ACWR gauge */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
          <AcwrGauge acwr={latest.acwr} />
          <span style={{ fontSize: 11, color: 'var(--text-3)' }}>
            Status: <span style={{ color: latest.acwr >= 0.8 && latest.acwr <= 1.3 ? 'var(--green)' : 'var(--orange)' }}>
              {latest.acwr_status || '—'}
            </span>
          </span>
          <span style={{ fontSize: 11, color: 'var(--text-3)' }}>
            Acuut {Math.round(latest.acute_load ?? 0)} / Chronisch {Math.round(latest.chronic_load ?? 0)}
          </span>
        </div>

        {/* Right: monthly balance bars */}
        <div style={{ flex: 1, minWidth: 220 }}>
          <span style={{ fontSize: 12, color: 'var(--text-2)', display: 'block', marginBottom: 8 }}>
            Maandelijks trainingsbalans
          </span>
          {barData.map((d) => {
            const pct = d.tmax > 0 ? Math.min((d.actual / d.tmax) * 100, 130) : 0
            const targetPct = d.tmax > 0 ? (d.tmin / d.tmax) * 100 : 0
            return (
              <div key={d.label} style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-3)', marginBottom: 3 }}>
                  <span>{d.label}</span>
                  <span style={{ color: d.inTarget ? 'var(--green)' : 'var(--orange)' }}>
                    {d.actual} / {d.tmin}–{d.tmax}
                  </span>
                </div>
                <div style={{ height: 8, background: 'var(--bg-card2)', borderRadius: 4, position: 'relative', overflow: 'hidden' }}>
                  <div style={{
                    position: 'absolute', left: 0, top: 0, bottom: 0,
                    width: `${pct}%`,
                    background: d.inTarget ? 'var(--green)' : 'var(--orange)',
                    borderRadius: 4, transition: 'width 0.3s',
                  }} />
                  <div style={{
                    position: 'absolute', left: `${targetPct}%`, top: 0, bottom: 0,
                    width: 2, background: 'var(--text-3)', opacity: 0.5,
                  }} />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/components/TrainingLoad.jsx
git commit -m "feat: fase2 — TrainingLoad component met ACWR gauge en maandbalans bars"
```

---

## Task 7: RunEfficiency component

**Files:**
- Create: `dashboard/src/components/RunEfficiency.jsx`

- [ ] **Step 1: Maak het component**

```jsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

function MiniChart({ data, dataKey, label, unit, refValue, color = 'var(--accent)', reversed = false }) {
  const vals = data.map(d => d[dataKey]).filter(v => v != null)
  const avg = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null

  return (
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
        <span className="label">{label}</span>
        {avg != null && (
          <span style={{ fontSize: 13, fontWeight: 700, color }}>
            {Math.round(avg)}<span style={{ fontSize: 10, color: 'var(--text-3)', marginLeft: 2 }}>{unit}</span>
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={90}>
        <LineChart data={[...data].reverse()} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <XAxis dataKey="date" hide />
          <YAxis domain={['auto', 'auto']} reversed={reversed} hide />
          <Tooltip
            formatter={(v) => [`${Math.round(v)} ${unit}`, label]}
            labelStyle={{ color: 'var(--text-3)', fontSize: 11 }}
            contentStyle={{ background: 'var(--bg-card2)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
          />
          {refValue != null && (
            <ReferenceLine y={refValue} stroke="var(--text-3)" strokeDasharray="3 3" />
          )}
          <Line
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            dot={false}
            strokeWidth={2}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
      {refValue != null && (
        <div style={{ fontSize: 10, color: 'var(--text-3)', textAlign: 'right' }}>
          doel: {refValue} {unit}
        </div>
      )}
    </div>
  )
}

export default function RunEfficiency({ data }) {
  const eff = data.runEfficiency || []

  if (eff.length === 0) {
    return (
      <div className="card">
        <span className="label">Loopefficiëntie</span>
        <p className="no-data">Geen efficiëntie data — haal meer runs op met 30+ dagen</p>
      </div>
    )
  }

  return (
    <div className="card">
      <span className="label">Loopefficiëntie</span>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <MiniChart
          data={eff}
          dataKey="cadence_spm"
          label="Cadans"
          unit="spm"
          refValue={170}
          color="var(--accent)"
        />
        <MiniChart
          data={eff}
          dataKey="gct_ms"
          label="Grondcontact"
          unit="ms"
          refValue={240}
          color="var(--accent2)"
          reversed
        />
        <MiniChart
          data={eff}
          dataKey="vert_osc_mm"
          label="Verticale oscillatie"
          unit="cm"
          color="var(--orange)"
          reversed
        />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/components/RunEfficiency.jsx
git commit -m "feat: fase2 — RunEfficiency component met cadans/GCT/oscillatie mini-charts"
```

---

## Task 8: SplitsPanel component

**Files:**
- Create: `dashboard/src/components/SplitsPanel.jsx`

- [ ] **Step 1: Maak het component**

```jsx
function formatPace(s) {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60)
  return `${m}:${String(sec).padStart(2, '0')}`
}

function hrColor(hr) {
  if (!hr) return 'var(--text-3)'
  if (hr >= 170) return 'var(--red)'
  if (hr >= 155) return 'var(--orange)'
  return 'var(--green)'
}

export default function SplitsPanel({ data }) {
  const splits = data.splits || []
  const latestRun = (data.runs || [])[0]

  if (splits.length === 0) {
    return (
      <div className="card">
        <span className="label">Splits laatste run</span>
        <p className="no-data">Geen splits beschikbaar — voer {`garmin_test_pull.py`} opnieuw uit na Task 2</p>
      </div>
    )
  }

  const paces = splits.map(s => s.pace_s_per_km).filter(Boolean)
  const avgPace = paces.length ? paces.reduce((a, b) => a + b, 0) / paces.length : null

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 12 }}>
        <span className="label">Splits laatste run</span>
        {latestRun && (
          <span style={{ fontSize: 11, color: 'var(--text-3)' }}>
            {latestRun.name} · {latestRun.date}
          </span>
        )}
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ color: 'var(--text-3)', fontSize: 11 }}>
              <th style={{ textAlign: 'left', padding: '4px 8px' }}>km</th>
              <th style={{ textAlign: 'right', padding: '4px 8px' }}>Pace</th>
              <th style={{ textAlign: 'right', padding: '4px 8px' }}>HR</th>
              <th style={{ textAlign: 'right', padding: '4px 8px', display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>vs gem.</th>
            </tr>
          </thead>
          <tbody>
            {splits.map((s, i) => {
              const diff = avgPace && s.pace_s_per_km ? s.pace_s_per_km - avgPace : null
              return (
                <tr
                  key={i}
                  style={{
                    borderTop: '1px solid var(--border)',
                    background: i % 2 === 0 ? 'transparent' : 'var(--bg-card2)',
                  }}
                >
                  <td style={{ padding: '6px 8px', color: 'var(--text-2)' }}>
                    km {s.split_num}
                  </td>
                  <td style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--text-1)', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
                    {formatPace(s.pace_s_per_km)}
                  </td>
                  <td style={{ padding: '6px 8px', textAlign: 'right', color: hrColor(s.avg_hr), fontWeight: 500 }}>
                    {s.avg_hr ? Math.round(s.avg_hr) : '—'}
                  </td>
                  <td style={{ padding: '6px 8px', textAlign: 'right', color: diff == null ? 'var(--text-3)' : diff > 5 ? 'var(--orange)' : diff < -5 ? 'var(--green)' : 'var(--text-3)' }}>
                    {diff == null ? '—' : `${diff > 0 ? '+' : ''}${formatPace(Math.abs(diff))}`}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/components/SplitsPanel.jsx
git commit -m "feat: fase2 — SplitsPanel component met pace/HR per km"
```

---

## Task 9: RecentRuns uitbreiden

**Files:**
- Modify: `dashboard/src/components/RecentRuns.jsx`

- [ ] **Step 1: Lees het huidige RecentRuns.jsx**

Check welke kolommen er al in staan.

- [ ] **Step 2: Vervang de component**

```jsx
function formatTime(s) {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60)
  return `${m}:${String(sec).padStart(2, '0')}`
}

function formatPace(s) {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60)
  return `${m}:${String(sec).padStart(2, '0')}/km`
}

function EffectLabel({ msg, label }) {
  if (!label) return <span style={{ color: 'var(--text-3)' }}>—</span>
  const short = label.replace(/_/g, ' ').toLowerCase()
  return (
    <span style={{ fontSize: 11, color: 'var(--accent2)', textTransform: 'capitalize' }}>
      {short}
    </span>
  )
}

export default function RecentRuns({ data }) {
  const runs = (data.runs || []).slice(0, 10)

  if (runs.length === 0) {
    return (
      <div className="card">
        <span className="label">Recente Runs</span>
        <p className="no-data">Geen runs gevonden</p>
      </div>
    )
  }

  return (
    <div className="card">
      <span className="label">Recente Runs</span>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ color: 'var(--text-3)', fontSize: 11 }}>
              <th style={{ textAlign: 'left',   padding: '4px 8px' }}>Datum</th>
              <th style={{ textAlign: 'right',  padding: '4px 8px' }}>km</th>
              <th style={{ textAlign: 'right',  padding: '4px 8px' }}>Pace</th>
              <th style={{ textAlign: 'right',  padding: '4px 8px' }}>HR</th>
              <th style={{ textAlign: 'right',  padding: '4px 8px' }}>AE</th>
              <th style={{ textAlign: 'right',  padding: '4px 8px' }}>Load</th>
              <th style={{ textAlign: 'right',  padding: '4px 8px' }}>BB</th>
              <th style={{ textAlign: 'left',   padding: '4px 8px' }}>Effect</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r, i) => (
              <tr
                key={i}
                style={{
                  borderTop: '1px solid var(--border)',
                  background: i % 2 === 0 ? 'transparent' : 'var(--bg-card2)',
                }}
              >
                <td style={{ padding: '6px 8px', color: 'var(--text-2)' }}>{r.date}</td>
                <td style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--text-1)' }}>
                  {r.distance_km?.toFixed(1)}
                </td>
                <td style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--text-2)', fontVariantNumeric: 'tabular-nums' }}>
                  {formatPace(r.avg_pace_s_per_km)}
                </td>
                <td style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--text-2)' }}>
                  {r.avg_hr ? Math.round(r.avg_hr) : '—'}
                </td>
                <td style={{ padding: '6px 8px', textAlign: 'right', color: r.aerobic_effect >= 3 ? 'var(--green)' : 'var(--text-2)' }}>
                  {r.aerobic_effect?.toFixed(1) ?? '—'}
                </td>
                <td style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--text-2)' }}>
                  {r.training_load ? Math.round(r.training_load) : '—'}
                </td>
                <td style={{ padding: '6px 8px', textAlign: 'right', color: r.bb_cost < -20 ? 'var(--orange)' : 'var(--text-2)' }}>
                  {r.bb_cost != null ? r.bb_cost : '—'}
                </td>
                <td style={{ padding: '6px 8px' }}>
                  <EffectLabel label={r.training_effect_label} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/RecentRuns.jsx
git commit -m "feat: fase2 — RecentRuns uitgebreid met training_load, bb_cost, training_effect_label"
```

---

## Task 10: App.jsx wiring + api.js + panels_config update

**Files:**
- Modify: `dashboard/src/api.js`
- Modify: `dashboard/src/App.jsx`
- Modify: `ingest.py` (panels_config update)

- [ ] **Step 1: Update api.js**

Vervang de volledige inhoud:

```js
const BASE = '/api'

async function get(path) {
  const r = await fetch(BASE + path)
  if (!r.ok) throw new Error(`${r.status} ${path}`)
  return r.json()
}

export const api = {
  athletes:       () => get('/athletes'),
  hero:           (id) => get(`/athlete/${id}/hero`),
  runs:           (id) => get(`/athlete/${id}/runs`),
  weeklyVolume:   (id) => get(`/athlete/${id}/weekly_volume`),
  tempoTrend:     (id) => get(`/athlete/${id}/tempo_trend`),
  zoneDist:       (id) => get(`/athlete/${id}/zone_distribution`),
  vo2maxTrend:    (id) => get(`/athlete/${id}/vo2max_trend`),
  dailyStats:     (id) => get(`/athlete/${id}/daily_stats?days=14`),
  recovery:       (id) => get(`/athlete/${id}/recovery?days=7`),
  trainingLoad:   (id) => get(`/athlete/${id}/training_load`),
  runEfficiency:  (id) => get(`/athlete/${id}/run_efficiency`),
  attentionPoints:(id) => get(`/athlete/${id}/attention_points`),
  splits:         (id, actId) => get(`/athlete/${id}/activity/${actId}/splits`),
}
```

- [ ] **Step 2: Update App.jsx**

Vervang de volledige inhoud van `dashboard/src/App.jsx`:

```jsx
import { useState, useEffect } from 'react'
import './theme.css'
import { api } from './api'
import GoalBanner from './components/GoalBanner'
import AttentionPoints from './components/AttentionPoints'
import HeroRow from './components/HeroRow'
import TrainingLoad from './components/TrainingLoad'
import WeekVolume from './components/WeekVolume'
import TempoTrend from './components/TempoTrend'
import ZoneDistribution from './components/ZoneDistribution'
import RunEfficiency from './components/RunEfficiency'
import VO2MaxTrend from './components/VO2MaxTrend'
import RecentRuns from './components/RecentRuns'
import SplitsPanel from './components/SplitsPanel'
import DailyStats from './components/DailyStats'
import RecoveryStrip from './components/RecoveryStrip'

const PANEL_COMPONENTS = {
  GoalBanner, AttentionPoints, HeroRow, TrainingLoad,
  WeekVolume, TempoTrend, ZoneDistribution, RunEfficiency,
  VO2MaxTrend, RecentRuns, SplitsPanel, DailyStats, RecoveryStrip,
}

function AthleteTab({ athleteId }) {
  const [data, setData] = useState({})
  const [panels, setPanels] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [athletes, hero, runs, weekVol, tempo, zones, vo2, daily, recovery,
               trainingLoad, runEfficiency, attentionPoints] = await Promise.all([
          api.athletes(),
          api.hero(athleteId),
          api.runs(athleteId),
          api.weeklyVolume(athleteId),
          api.tempoTrend(athleteId),
          api.zoneDist(athleteId),
          api.vo2maxTrend(athleteId),
          api.dailyStats(athleteId),
          api.recovery(athleteId),
          api.trainingLoad(athleteId),
          api.runEfficiency(athleteId),
          api.attentionPoints(athleteId),
        ])

        const athlete = athletes.find(a => a.id === athleteId) || {}
        setPanels(athlete.panels || Object.keys(PANEL_COMPONENTS))

        // Splits voor de meest recente run
        const latestRun = runs[0]
        const splits = latestRun
          ? await api.splits(athleteId, latestRun.activity_id).catch(() => [])
          : []

        setData({ hero, runs, weekVol, tempo, zones, vo2, daily, recovery,
                  trainingLoad, runEfficiency, attentionPoints, splits })
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [athleteId])

  if (loading) return <div style={{ padding: 40, color: 'var(--text-2)' }}>Laden...</div>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {panels.map(name => {
        const Comp = PANEL_COMPONENTS[name]
        if (!Comp) return null
        return <Comp key={name} athleteId={athleteId} data={data} />
      })}
    </div>
  )
}

export default function App() {
  const [athletes, setAthletes] = useState([])
  const [activeId, setActiveId] = useState(null)

  useEffect(() => {
    api.athletes().then(list => {
      setAthletes(list)
      if (list.length > 0) setActiveId(list[0].id)
    })
  }, [])

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      <div style={{
        background: 'var(--bg-card)', borderBottom: '1px solid var(--border)',
        padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 24,
      }}>
        <span style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-1)' }}>
          🏃 Garmin Coach
        </span>
        <div style={{ display: 'flex', gap: 8 }}>
          {athletes.map(a => (
            <button
              key={a.id}
              onClick={() => setActiveId(a.id)}
              style={{
                padding: '6px 14px', borderRadius: 8, border: 'none', cursor: 'pointer',
                background: activeId === a.id ? 'var(--accent)' : 'var(--bg-card2)',
                color: 'var(--text-1)', fontSize: 13, fontWeight: 600,
              }}
            >
              {a.display_name}
            </button>
          ))}
        </div>
      </div>
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '24px 16px' }}>
        {activeId && <AthleteTab athleteId={activeId} />}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Update panels_config in ingest.py**

Zoek `default_panels` in `run_ingest` en vervang:

```python
    default_panels = [
        "GoalBanner", "AttentionPoints", "HeroRow", "TrainingLoad",
        "WeekVolume", "TempoTrend", "ZoneDistribution", "RunEfficiency",
        "VO2MaxTrend", "RecentRuns", "SplitsPanel",
        "DailyStats", "RecoveryStrip",
    ]
```

- [ ] **Step 4: Update bestaande athlete panels_config in DB**

```bash
cd ~/Documents/garmin-coach && source .venv/bin/activate
python3 - <<'EOF'
import json
from db import get_conn, DB_PATH

new_panels = [
    "GoalBanner", "AttentionPoints", "HeroRow", "TrainingLoad",
    "WeekVolume", "TempoTrend", "ZoneDistribution", "RunEfficiency",
    "VO2MaxTrend", "RecentRuns", "SplitsPanel",
    "DailyStats", "RecoveryStrip",
]
conn = get_conn()
conn.execute(
    "UPDATE athletes SET panels_config=?",
    (json.dumps(new_panels),)
)
conn.commit()
print("panels_config updated")
EOF
```

Expected: `panels_config updated`

- [ ] **Step 5: Run alle tests**

```bash
cd ~/Documents/garmin-coach && source .venv/bin/activate
pytest tests/ -v
```

Expected: alle tests PASS

- [ ] **Step 6: Start dashboard en verify**

```bash
cd ~/Documents/garmin-coach && bash start.sh
```

Controleer in de browser op `http://localhost:5173`:
- AttentionPoints toont aandachtspunten na GoalBanner
- TrainingLoad toont ACWR gauge + balans bars
- RunEfficiency toont 3 mini-charts (of "geen data" als GCT missing)
- RecentRuns heeft nieuwe kolommen Load/BB/Effect
- SplitsPanel toont "Geen splits beschikbaar" (tot splits opgehaald zijn)

- [ ] **Step 7: Commit**

```bash
git add dashboard/src/api.js dashboard/src/App.jsx ingest.py
git commit -m "feat: fase2 — App.jsx wiring alle nieuwe panels, api.js uitbreiden, panels_config update"
```

---

## Fase 2 complete

Na Task 10 is het dashboard volledig uitgebreid. Om splits te activeren:

```bash
cd ~/Documents/garmin-coach
source .venv/bin/activate
python3 garmin_test_pull.py --athlete vriendin --days 30
python3 ingest.py --athlete vriendin --name Vriendin
```

Dit haalt splits_*.json op per run en verwerkt ze naar activity_splits tabel. De SplitsPanel toont dan km-splits van de meest recente hardlooprun.
