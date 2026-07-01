# Vercel Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the Garmin Coach dashboard to Vercel (free tier) so girlfriend can open it on her phone — React frontend on Vercel CDN, FastAPI on Vercel Python serverless, Supabase Postgres instead of SQLite, GitHub Actions for daily Garmin sync.

**Architecture:** Vite/React frontend served from Vercel CDN. FastAPI routes exposed as Vercel Python serverless functions via `vercel.json` rewrites. Supabase free-tier Postgres replaces SQLite (psycopg2). GitHub Actions cron runs `garmin_test_pull.py` + `ingest.py` daily at 06:00 UTC and pushes to Supabase.

**Tech Stack:** Python 3.12, FastAPI, psycopg2-binary, Vite 8, React 19, Vercel CLI, Supabase, GitHub Actions

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `db.py` | Modify | Swap sqlite3 → psycopg2; read `DATABASE_URL` env var |
| `requirements.txt` | Modify | Add psycopg2-binary, python-dotenv |
| `vercel.json` | Create | Route `/api/*` to FastAPI serverless; build frontend |
| `api/main.py` | Modify | Remove SQLite startup, update CORS for prod |
| `api/routes.py` | Modify | Use psycopg2 cursor (dict_cursor) instead of sqlite3.Row |
| `.github/workflows/sync.yml` | Create | Daily cron: garmin pull + ingest to Supabase |
| `scripts/migrate_to_supabase.py` | Create | One-time SQLite → Supabase migration |
| `.env.example` | Create | Document required env vars |
| `dashboard/vite.config.js` | No change needed | Local proxy stays, Vercel routing handles prod |

---

## Task 1: Supabase-compatible db.py

**Files:**
- Modify: `db.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Add psycopg2-binary and python-dotenv to requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-garminconnect==0.2.22
psycopg2-binary==2.9.10
python-dotenv==1.0.1
```

- [ ] **Step 2: Rewrite db.py to support both Postgres (prod) and SQLite (local fallback)**

Replace entire `db.py` content:

```python
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
"""

SCHEMA_PG = """
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


def use_postgres() -> bool:
    return bool(DATABASE_URL)


def get_pg_conn():
    import psycopg2
    import psycopg2.extras
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
    import psycopg2
    conn = get_pg_conn()
    cur = conn.cursor()
    for stmt in SCHEMA_PG.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            cur.execute(stmt)
    conn.commit()
    cur.close()
    conn.close()


def _init_sqlite(path: Path) -> None:
    with get_conn(path) as conn:
        conn.executescript(SCHEMA_SQLITE)
    _migrate_activities(path)


def _migrate_activities(path: Path) -> None:
    with get_conn(path) as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(activities)").fetchall()}
        for col, col_type in ACTIVITY_NEW_COLUMNS:
            if col not in existing:
                conn.execute(f"ALTER TABLE activities ADD COLUMN {col} {col_type}")
        conn.commit()
```

- [ ] **Step 3: Verify local tests still pass**

```bash
cd ~/Documents/garmin-coach && python -m pytest tests/ -v
```

Expected: all tests pass (db.py changes are backward-compatible for SQLite path).

- [ ] **Step 4: Commit**

```bash
cd ~/Documents/garmin-coach && git add db.py requirements.txt && git commit -m "feat: db.py dual-mode SQLite/Postgres for Vercel deployment"
```

---

## Task 2: Postgres-aware routes.py

**Files:**
- Modify: `api/routes.py`

Routes currently use `sqlite3.Row` (dict-like by column name). psycopg2 uses tuples by default. We use `psycopg2.extras.RealDictCursor` to get dict-style rows identical to sqlite3.Row.

- [ ] **Step 1: Add `_pg_conn()` helper and update `_conn()` at top of routes.py**

Replace the `_conn` function and add a context manager for Postgres:

```python
# at top of routes.py, after existing imports:
import db as db_module

def _conn():
    """Return (conn, is_pg) tuple."""
    if db_module.use_postgres():
        import psycopg2.extras
        conn = db_module.get_pg_conn()
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn
    return db_module.get_conn(db_module.DB_PATH)
```

The rest of routes.py uses `conn.execute(sql, params).fetchone()` / `.fetchall()` — both sqlite3 and psycopg2 RealDictCursor support this with one difference: **sqlite3 uses `?` placeholders, psycopg2 uses `%s`**.

- [ ] **Step 2: Replace all `?` placeholders with `%s` when using Postgres, OR switch all queries to use `%s` universally**

The cleanest fix: replace every `?` in sql strings with `%s`. psycopg2 accepts `%s` always; sqlite3 also supports `%s` for named params but NOT positional — so we use a helper.

Add this at top of routes.py:

```python
def _ph() -> str:
    """Placeholder char for current DB backend."""
    return "%s" if db_module.use_postgres() else "?"
```

This approach is verbose. Simpler: **just switch all query placeholders to `%s`** — sqlite3 does NOT support `%s` for positional params.

Better approach: use a thin wrapper that translates `?` → `%s` for Postgres:

```python
def _exec(conn, sql: str, params=()) -> Any:
    if db_module.use_postgres():
        sql = sql.replace("?", "%s")
    return conn.execute(sql, params)
```

Add `_exec` helper to routes.py and replace every `conn.execute(sql, params)` call with `_exec(conn, sql, params)`.

- [ ] **Step 3: Apply _exec wrapper throughout routes.py**

In routes.py, add after imports:

```python
def _exec(conn, sql: str, params=()):
    if db_module.use_postgres():
        sql = sql.replace("?", "%s")
    return conn.execute(sql, params)
```

Then replace every occurrence of `conn.execute(sql, (params,))` with `_exec(conn, sql, (params,))` throughout routes.py.

Note: The pattern is `conn.execute("... WHERE athlete_id=?", (athlete_id,))` → `_exec(conn, "... WHERE athlete_id=?", (athlete_id,))`.

- [ ] **Step 4: Close Postgres connections after each request**

Postgres connections must be explicitly closed (unlike SQLite context managers). Add at end of each route function:

```python
finally:
    if db_module.use_postgres():
        conn.close()
```

Or wrap each route with a try/finally block. This avoids connection pool exhaustion on Vercel serverless.

- [ ] **Step 5: Verify local tests pass (SQLite path untouched)**

```bash
cd ~/Documents/garmin-coach && python -m pytest tests/ -v
```

- [ ] **Step 6: Commit**

```bash
cd ~/Documents/garmin-coach && git add api/routes.py && git commit -m "feat: routes.py Postgres-compatible via _exec helper + RealDictCursor"
```

---

## Task 3: vercel.json + api/main.py

**Files:**
- Create: `vercel.json`
- Modify: `api/main.py`

- [ ] **Step 1: Create vercel.json at repo root**

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/main.py",
      "use": "@vercel/python",
      "config": { "maxLambdaSize": "15mb" }
    },
    {
      "src": "dashboard/package.json",
      "use": "@vercel/static-build",
      "config": { "distDir": "dashboard/dist" }
    }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "api/main.py" },
    { "src": "/(.*)", "dest": "dashboard/dist/$1" }
  ]
}
```

- [ ] **Step 2: Update api/main.py for Vercel (remove startup event, update CORS)**

Replace `api/main.py` with:

```python
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

app = FastAPI(title="Garmin Coach API")

# Allow Vercel preview URLs + localhost
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    os.environ.get("VERCEL_URL", ""),  # set automatically by Vercel
    os.environ.get("FRONTEND_URL", ""),  # set manually for custom domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in ALLOWED_ORIGINS if o],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Init DB on cold start (idempotent CREATE TABLE IF NOT EXISTS)
import db as db_module
db_module.init_db()

app.include_router(router)
```

Note: `@app.on_event("startup")` is removed — Vercel Python serverless has no startup lifecycle. DB init runs at module-load time instead (cold start only).

- [ ] **Step 3: Create .env.example**

```bash
cat > ~/Documents/garmin-coach/.env.example << 'EOF'
# Supabase Postgres connection string (from Supabase dashboard → Settings → Database)
DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres

# Garmin Connect credentials (for sync script)
GARMIN_EMAIL=your@email.com
GARMIN_PASSWORD=yourpassword

# Athlete ID used in ingest.py
ATHLETE_ID=vriendin

# Set by Vercel automatically — no need to set manually
# VERCEL_URL=garmin-coach-xxx.vercel.app

# Set manually if using custom domain
# FRONTEND_URL=https://yourdomain.com
EOF
```

- [ ] **Step 4: Commit**

```bash
cd ~/Documents/garmin-coach && git add vercel.json api/main.py .env.example && git commit -m "feat: vercel.json + main.py for serverless deployment"
```

---

## Task 4: One-time migration script SQLite → Supabase

**Files:**
- Create: `scripts/migrate_to_supabase.py`

This script runs once locally: reads all data from garmin_coach.db and upserts it into Supabase.

- [ ] **Step 1: Create scripts/migrate_to_supabase.py**

```python
#!/usr/bin/env python3
"""One-time migration: garmin_coach.db → Supabase Postgres.
Usage: DATABASE_URL=postgres://... python scripts/migrate_to_supabase.py
"""
import os
import sqlite3
from pathlib import Path

import psycopg2
import psycopg2.extras

SQLITE_PATH = Path(__file__).parent.parent / "garmin_coach.db"
DATABASE_URL = os.environ["DATABASE_URL"]

TABLES = [
    "athletes",
    "activities",
    "daily_stats",
    "daily_heart_rates",
    "body_battery",
    "training_readiness",
    "vo2max",
    "training_load_balance",
    "activity_splits",
]


def migrate():
    src = sqlite3.connect(SQLITE_PATH)
    src.row_factory = sqlite3.Row

    dst = psycopg2.connect(DATABASE_URL)
    dst.autocommit = False

    with dst.cursor() as cur:
        for table in TABLES:
            rows = src.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                print(f"  {table}: 0 rows, skip")
                continue

            cols = rows[0].keys()
            col_list = ", ".join(cols)
            placeholders = ", ".join(["%s"] * len(cols))
            conflict_cols = _pk(table)
            update_set = ", ".join(
                f"{c}=EXCLUDED.{c}" for c in cols if c not in conflict_cols
            )
            sql = (
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
                f"ON CONFLICT ({', '.join(conflict_cols)}) DO UPDATE SET {update_set}"
            )
            data = [tuple(r) for r in rows]
            psycopg2.extras.execute_batch(cur, sql, data, page_size=200)
            print(f"  {table}: {len(rows)} rows upserted")

    dst.commit()
    src.close()
    dst.close()
    print("Migration complete.")


def _pk(table: str) -> list[str]:
    return {
        "athletes": ["id"],
        "activities": ["athlete_id", "activity_id"],
        "daily_stats": ["athlete_id", "date"],
        "daily_heart_rates": ["athlete_id", "date"],
        "body_battery": ["athlete_id", "date"],
        "training_readiness": ["athlete_id", "date"],
        "vo2max": ["athlete_id", "date"],
        "training_load_balance": ["athlete_id", "date"],
        "activity_splits": ["athlete_id", "activity_id", "split_num"],
    }[table]


if __name__ == "__main__":
    migrate()
```

- [ ] **Step 2: Make executable**

```bash
chmod +x ~/Documents/garmin-coach/scripts/migrate_to_supabase.py
```

- [ ] **Step 3: Commit**

```bash
cd ~/Documents/garmin-coach && git add scripts/migrate_to_supabase.py && git commit -m "feat: one-time SQLite → Supabase migration script"
```

---

## Task 5: GitHub Actions daily sync

**Files:**
- Create: `.github/workflows/sync.yml`

- [ ] **Step 1: Create .github/workflows/sync.yml**

```yaml
name: Daily Garmin Sync

on:
  schedule:
    - cron: "0 6 * * *"   # 06:00 UTC = 08:00 CEST
  workflow_dispatch:        # allow manual trigger

jobs:
  sync:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Pull Garmin data
        env:
          GARMIN_EMAIL: ${{ secrets.GARMIN_EMAIL }}
          GARMIN_PASSWORD: ${{ secrets.GARMIN_PASSWORD }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          ATHLETE_ID: ${{ secrets.ATHLETE_ID }}
        run: python garmin_test_pull.py

      - name: Ingest to Supabase
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          ATHLETE_ID: ${{ secrets.ATHLETE_ID }}
        run: python ingest.py
```

- [ ] **Step 2: Verify garmin_test_pull.py and ingest.py read GARMIN_EMAIL/GARMIN_PASSWORD/ATHLETE_ID from env**

Check what env vars garmin_test_pull.py uses:

```bash
grep -n "environ\|os\.getenv\|GARMIN\|ATHLETE" ~/Documents/garmin-coach/garmin_test_pull.py | head -20
```

If hardcoded, update to read from env with fallback:

```python
import os
EMAIL = os.environ.get("GARMIN_EMAIL", "hardcoded@example.com")
PASSWORD = os.environ.get("GARMIN_PASSWORD", "hardcoded")
ATHLETE_ID = os.environ.get("ATHLETE_ID", "vriendin")
```

- [ ] **Step 3: Commit**

```bash
cd ~/Documents/garmin-coach && mkdir -p .github/workflows && git add .github/workflows/sync.yml && git commit -m "feat: GitHub Actions daily Garmin sync at 06:00 UTC"
```

---

## Task 6: GitHub repo + Vercel deploy

This task is manual/interactive — Claude guides, user executes.

- [ ] **Step 1: Create GitHub repo and push**

```bash
cd ~/Documents/garmin-coach
gh repo create garmin-coach --private --source=. --push
```

- [ ] **Step 2: Add GitHub Secrets**

Go to: https://github.com/[user]/garmin-coach/settings/secrets/actions

Add these secrets:
- `GARMIN_EMAIL` — Garmin Connect email
- `GARMIN_PASSWORD` — Garmin Connect password  
- `DATABASE_URL` — Supabase connection string (from Supabase → Settings → Database → URI)
- `ATHLETE_ID` — `vriendin`

- [ ] **Step 3: Create Supabase project**

1. Go to https://supabase.com → New project (free tier)
2. Region: eu-west-1 (Frankfurt, closest to NL)
3. Copy the connection string from Settings → Database → URI

- [ ] **Step 4: Initialize Supabase schema**

```bash
DATABASE_URL="postgres://..." python -c "import db; db.init_db()"
```

- [ ] **Step 5: Migrate existing SQLite data**

```bash
DATABASE_URL="postgres://..." python scripts/migrate_to_supabase.py
```

- [ ] **Step 6: Deploy to Vercel**

```bash
cd ~/Documents/garmin-coach
vercel --prod
```

When prompted:
- Link to existing project? **No, create new**
- Project name: `garmin-coach`
- Root directory: `.` (repo root)

Add environment variable in Vercel dashboard:
- `DATABASE_URL` = Supabase connection string

- [ ] **Step 7: Verify deployment**

```bash
vercel --prod
# Note the deployment URL, e.g. https://garmin-coach-xxx.vercel.app
curl https://garmin-coach-xxx.vercel.app/api/athletes
```

Expected: JSON array with athlete data.

- [ ] **Step 8: Test manual sync trigger**

In GitHub → Actions → Daily Garmin Sync → Run workflow

Verify sync completes without errors and Supabase data is updated.

---

## Self-Review

**Spec coverage:**
- ✅ SQLite → Supabase: Tasks 1-2
- ✅ FastAPI serverless: Task 3 (vercel.json + main.py)
- ✅ GitHub Actions sync: Task 5
- ✅ Migration of existing data: Task 4
- ✅ Frontend deploy: covered by vercel.json builds + Task 6

**Placeholder scan:** No TBDs. All SQL in migration script is complete. All env vars documented.

**Type consistency:** `_exec(conn, sql, params)` signature consistent across all references. `use_postgres()` called identically in db.py and routes.py.

**Known limitation:** routes.py has many `conn.execute()` calls. Task 2 Step 3 says "replace every occurrence" — implementer must do a grep pass to ensure none are missed. Pattern: `grep -n "conn\.execute" api/routes.py`.
