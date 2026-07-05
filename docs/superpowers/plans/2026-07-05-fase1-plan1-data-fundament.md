# Fase 1 · Plan 1 — Backend data-fundament + home-endpoint

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** De ontbrekende hardloop-data (HRV, slaap, body-battery-niveau) ingesten en een geconsolideerd `/home`-endpoint bouwen dat readiness, fitheid, belasting en laatste run met regelgebaseerde duiding als één view-klare payload teruggeeft.

**Architecture:** Bestaande dual-mode datalaag (SQLite lokaal / Postgres prod via `db.py`) uitbreiden met twee tabellen + een body-battery-kolom. Pure-functie-modules `metrics.py` (afgeleide metrics) en `coach_rules.py` (regelgebaseerde duiding, stabiele interface voor Fase 4). Eén nieuw FastAPI-endpoint dat alles samenvoegt.

**Tech Stack:** Python 3.9+, FastAPI, SQLite + Postgres (psycopg2), pytest. Bestaande conventies: per-functie ingest in `ingest.py`, `_conn()`/`_exec()`-helpers in `api/routes.py`, fixtures in `tests/`.

**Scope-grens:** Alleen backend. Frontend-herbouw + PWA = Plan 2. Geen trainingsplan/AI (latere fasen). Duiding is regelgebaseerd.

---

## Bestandsstructuur

| Bestand | Verantwoordelijkheid | Actie |
|---|---|---|
| `db.py` | Schema (SQLite + Postgres) | Modify: `hrv`- en `sleep`-tabel + `bb_level_*`-kolommen |
| `ingest.py` | JSON → DB upserts | Modify: `ingest_hrv`, `ingest_sleep`, body-battery-niveau, `run_ingest`-wiring |
| `scripts/migrate_to_supabase.py` | SQLite → Postgres push | Modify: `TABLES` + `TABLE_PKS` |
| `metrics.py` | Afgeleide metrics (pure functies) | Create |
| `coach_rules.py` | Regelgebaseerde duiding (pure functies) | Create |
| `api/routes.py` | View-klare endpoints | Modify: nieuw `/athlete/{id}/home` |
| `tests/test_ingest.py` | Ingest-tests | Modify |
| `tests/test_metrics.py` | Metrics-tests | Create |
| `tests/test_coach_rules.py` | Duiding-tests | Create |
| `tests/test_api.py` | API-tests | Modify |

Uitvoeren van tests: vanuit repo-root met `.venv/bin/python -m pytest`.

---

## Task 1: DB-schema — hrv- en sleep-tabel + body-battery-niveau

**Files:**
- Modify: `db.py` (`SCHEMA_SQLITE`, `SCHEMA_PG`)

- [ ] **Step 1: Voeg tabellen + kolommen toe aan `SCHEMA_SQLITE`**

Voeg vóór de sluitende `"""` van `SCHEMA_SQLITE` toe:

```sql
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
```

In de bestaande `body_battery`-tabel in `SCHEMA_SQLITE`, voeg drie kolommen toe aan de kolomdefinitie (na `drained REAL`):

```sql
    level_current INTEGER, level_high INTEGER, level_low INTEGER,
```

- [ ] **Step 2: Spiegel dit in `SCHEMA_PG`**

Voeg dezelfde twee `CREATE TABLE`-statements toe aan `SCHEMA_PG` (identieke kolommen; `TEXT`/`INTEGER` bestaan ook in Postgres). Voeg dezelfde drie kolommen toe aan de Postgres `body_battery`-definitie.

- [ ] **Step 3: Body-battery-kolom-migratie voor bestaande SQLite-DB's**

`_init_sqlite` roept `_migrate_activities` aan voor `activities`. Body_battery heeft nu ook nieuwe kolommen. Voeg in `db.py` een generieke helper toe en roep 'm aan in `_init_sqlite` ná `_migrate_activities`:

```python
BODY_BATTERY_NEW_COLUMNS = [
    ("level_current", "INTEGER"),
    ("level_high", "INTEGER"),
    ("level_low", "INTEGER"),
]

def _migrate_body_battery(path: Path) -> None:
    with get_conn(path) as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(body_battery)").fetchall()}
        for col, col_type in BODY_BATTERY_NEW_COLUMNS:
            if col not in existing:
                conn.execute(f"ALTER TABLE body_battery ADD COLUMN {col} {col_type}")
        conn.commit()
```

In `_init_sqlite`, na `_migrate_activities(path)`:

```python
    _migrate_body_battery(path)
```

- [ ] **Step 4: Verifieer schema laadt**

Run: `.venv/bin/python -c "import db; db.init_db(db.Path('/tmp/schema_test.db')); print('ok')"`
Expected: print `ok`, geen exceptions. Daarna: `rm -f /tmp/schema_test.db`.

- [ ] **Step 5: Commit**

```bash
git add db.py
git commit -m "feat(db): add hrv, sleep tables and body-battery level columns"
```

---

## Task 2: ingest_hrv

**Files:**
- Modify: `ingest.py`
- Test: `tests/test_ingest.py`

- [ ] **Step 1: Schrijf de falende test**

Voeg toe aan `tests/test_ingest.py`:

```python
def test_ingest_hrv_stores_summary():
    from ingest import ingest_hrv
    conn = get_conn(_new_db())
    upsert_athlete(conn, "rowan", "Rowan", [])
    data = {
        "2026-07-02": {
            "hrvSummary": {"calendarDate": "2026-07-02", "lastNightAvg": 70,
                           "lastNight5MinHigh": 107, "status": "BALANCED"}
        },
        "2026-07-03": None,
    }
    n = ingest_hrv(conn, "rowan", data)
    assert n == 1
    row = conn.execute(
        "SELECT last_night_avg, last_night_high, status FROM hrv WHERE athlete_id='rowan' AND date='2026-07-02'"
    ).fetchone()
    assert row["last_night_avg"] == 70
    assert row["last_night_high"] == 107
    assert row["status"] == "BALANCED"
```

Als `_new_db()` nog niet bestaat in dit testbestand, voeg bovenaan (na imports) toe:

```python
def _new_db():
    import tempfile
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    p = Path(f.name)
    init_db(p)
    return p
```

- [ ] **Step 2: Run test — verwacht falen**

Run: `.venv/bin/python -m pytest tests/test_ingest.py::test_ingest_hrv_stores_summary -v`
Expected: FAIL met `ImportError: cannot import name 'ingest_hrv'`.

- [ ] **Step 3: Implementeer `ingest_hrv`**

Voeg toe aan `ingest.py` (na `ingest_body_battery`):

```python
def ingest_hrv(conn: sqlite3.Connection, athlete_id: str, data: dict) -> int:
    count = 0
    for date, row in (data or {}).items():
        if not row:
            continue
        summary = row.get("hrvSummary") or {}
        avg = summary.get("lastNightAvg")
        if avg is None:
            continue
        conn.execute(
            """
            INSERT INTO hrv (athlete_id, date, last_night_avg, last_night_high, status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
                last_night_avg=excluded.last_night_avg,
                last_night_high=excluded.last_night_high,
                status=excluded.status
            """,
            (athlete_id, summary.get("calendarDate", date), avg,
             summary.get("lastNight5MinHigh"), summary.get("status")),
        )
        count += 1
    conn.commit()
    return count
```

- [ ] **Step 4: Run test — verwacht slagen**

Run: `.venv/bin/python -m pytest tests/test_ingest.py::test_ingest_hrv_stores_summary -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest.py tests/test_ingest.py
git commit -m "feat(ingest): store HRV summary, tolerate null days"
```

---

## Task 3: ingest_sleep

**Files:**
- Modify: `ingest.py`
- Test: `tests/test_ingest.py`

- [ ] **Step 1: Schrijf de falende test**

```python
def test_ingest_sleep_stores_durations_and_score():
    from ingest import ingest_sleep
    conn = get_conn(_new_db())
    upsert_athlete(conn, "rowan", "Rowan", [])
    data = {
        "2026-07-02": {
            "dailySleepDTO": {
                "sleepTimeSeconds": 27720, "deepSleepSeconds": 5400,
                "lightSleepSeconds": 16200, "remSleepSeconds": 5400, "awakeSleepSeconds": 720,
                "sleepScores": {"overall": {"value": 82}},
            }
        },
        "2026-07-03": {"dailySleepDTO": {"sleepTimeSeconds": None}},
    }
    n = ingest_sleep(conn, "rowan", data)
    assert n == 1
    row = conn.execute(
        "SELECT duration_s, deep_s, score FROM sleep WHERE athlete_id='rowan' AND date='2026-07-02'"
    ).fetchone()
    assert row["duration_s"] == 27720
    assert row["deep_s"] == 5400
    assert row["score"] == 82
```

- [ ] **Step 2: Run test — verwacht falen**

Run: `.venv/bin/python -m pytest tests/test_ingest.py::test_ingest_sleep_stores_durations_and_score -v`
Expected: FAIL met `ImportError: cannot import name 'ingest_sleep'`.

- [ ] **Step 3: Implementeer `ingest_sleep`**

```python
def ingest_sleep(conn: sqlite3.Connection, athlete_id: str, data: dict) -> int:
    count = 0
    for date, row in (data or {}).items():
        if not row:
            continue
        dto = row.get("dailySleepDTO") or {}
        duration = dto.get("sleepTimeSeconds")
        if not duration:
            continue
        scores = dto.get("sleepScores") or {}
        overall = (scores.get("overall") or {}).get("value")
        conn.execute(
            """
            INSERT INTO sleep (athlete_id, date, duration_s, deep_s, light_s, rem_s, awake_s, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
                duration_s=excluded.duration_s, deep_s=excluded.deep_s,
                light_s=excluded.light_s, rem_s=excluded.rem_s,
                awake_s=excluded.awake_s, score=excluded.score
            """,
            (athlete_id, date, duration, dto.get("deepSleepSeconds"),
             dto.get("lightSleepSeconds"), dto.get("remSleepSeconds"),
             dto.get("awakeSleepSeconds"), overall),
        )
        count += 1
    conn.commit()
    return count
```

- [ ] **Step 4: Run test — verwacht slagen**

Run: `.venv/bin/python -m pytest tests/test_ingest.py::test_ingest_sleep_stores_durations_and_score -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest.py tests/test_ingest.py
git commit -m "feat(ingest): store nightly sleep durations and score"
```

---

## Task 4: Body-battery-niveau uit valuesArray

**Files:**
- Modify: `ingest.py` (`ingest_body_battery`)
- Test: `tests/test_ingest.py`

- [ ] **Step 1: Schrijf de falende test**

```python
def test_ingest_body_battery_derives_level():
    conn = get_conn(_new_db())
    upsert_athlete(conn, "rowan", "Rowan", [])
    data = [{
        "date": "2026-07-02", "charged": 70.0, "drained": 35.0,
        "bodyBatteryValuesArray": [[1, 40], [2, 55], [3, None], [4, 82], [5, 61]],
    }]
    ingest_body_battery(conn, "rowan", data)
    row = conn.execute(
        "SELECT level_current, level_high, level_low FROM body_battery WHERE athlete_id='rowan' AND date='2026-07-02'"
    ).fetchone()
    assert row["level_current"] == 61
    assert row["level_high"] == 82
    assert row["level_low"] == 40
```

- [ ] **Step 2: Run test — verwacht falen**

Run: `.venv/bin/python -m pytest tests/test_ingest.py::test_ingest_body_battery_derives_level -v`
Expected: FAIL (`level_current` is None of KeyError — kolom niet gevuld).

- [ ] **Step 3: Breid `ingest_body_battery` uit**

Vervang de body van `ingest_body_battery` door (behoudt bestaande charged/drained-upsert, voegt niveau toe):

```python
def ingest_body_battery(conn: sqlite3.Connection, athlete_id: str, data: list) -> int:
    count = 0
    for row in data:
        if row is None:
            continue
        levels = [v[1] for v in (row.get("bodyBatteryValuesArray") or []) if v and v[1] is not None]
        level_current = levels[-1] if levels else None
        level_high = max(levels) if levels else None
        level_low = min(levels) if levels else None
        conn.execute(
            """
            INSERT INTO body_battery (athlete_id, date, charged, drained, level_current, level_high, level_low)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
                charged=excluded.charged, drained=excluded.drained,
                level_current=excluded.level_current, level_high=excluded.level_high, level_low=excluded.level_low
            """,
            (athlete_id, row.get("date"), row.get("charged"), row.get("drained"),
             level_current, level_high, level_low),
        )
        count += 1
    conn.commit()
    return count
```

- [ ] **Step 4: Run test — verwacht slagen**

Run: `.venv/bin/python -m pytest tests/test_ingest.py::test_ingest_body_battery_derives_level -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest.py tests/test_ingest.py
git commit -m "feat(ingest): derive body-battery current/high/low level from values array"
```

---

## Task 5: Wire HRV + slaap in `run_ingest`

**Files:**
- Modify: `ingest.py` (`run_ingest`)
- Test: `tests/test_ingest.py`

De pull (`garmin_test_pull.py`) schrijft al `hrv.json` en `sleep.json` naar `output/<athlete>/`. `run_ingest` laadt ze nog niet.

- [ ] **Step 1: Schrijf de falende test**

```python
def test_run_ingest_loads_hrv_and_sleep(tmp_path):
    import json as _json
    from ingest import run_ingest
    out = tmp_path / "rowan"
    out.mkdir()
    (out / "hrv.json").write_text(_json.dumps({
        "2026-07-02": {"hrvSummary": {"calendarDate": "2026-07-02", "lastNightAvg": 65, "status": "BALANCED"}}
    }))
    (out / "sleep.json").write_text(_json.dumps({
        "2026-07-02": {"dailySleepDTO": {"sleepTimeSeconds": 25200, "sleepScores": {"overall": {"value": 80}}}}
    }))
    db_module.DB_PATH = _new_db()
    run_ingest("rowan", "Rowan", out)
    conn = get_conn(db_module.DB_PATH)
    assert conn.execute("SELECT COUNT(*) c FROM hrv WHERE athlete_id='rowan'").fetchone()["c"] == 1
    assert conn.execute("SELECT COUNT(*) c FROM sleep WHERE athlete_id='rowan'").fetchone()["c"] == 1
```

Zorg dat `import db as db_module` bovenaan `tests/test_ingest.py` staat; zo niet, voeg toe.

- [ ] **Step 2: Run test — verwacht falen**

Run: `.venv/bin/python -m pytest tests/test_ingest.py::test_run_ingest_loads_hrv_and_sleep -v`
Expected: FAIL (count is 0 — nog niet geladen).

- [ ] **Step 3: Voeg laden toe in `run_ingest`**

In `ingest.py`, in `run_ingest`, na de bestaande `training_readiness`-load-regel, voeg toe:

```python
    hrv = load("hrv.json") or {}
    print(f"  hrv: {ingest_hrv(conn, athlete_id, hrv)}")

    sleep = load("sleep.json") or {}
    print(f"  sleep: {ingest_sleep(conn, athlete_id, sleep)}")
```

- [ ] **Step 4: Run test — verwacht slagen**

Run: `.venv/bin/python -m pytest tests/test_ingest.py::test_run_ingest_loads_hrv_and_sleep -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest.py tests/test_ingest.py
git commit -m "feat(ingest): load hrv.json and sleep.json in run_ingest"
```

---

## Task 6: `migrate_to_supabase.py` — nieuwe tabellen meenemen

**Files:**
- Modify: `scripts/migrate_to_supabase.py`

- [ ] **Step 1: Voeg tabellen toe aan `TABLES` en `TABLE_PKS`**

In `TABLES` (na `"training_readiness"`), voeg `"hrv"` en `"sleep"` toe. In `TABLE_PKS`, voeg toe:

```python
    "hrv": ["athlete_id", "date"],
    "sleep": ["athlete_id", "date"],
```

- [ ] **Step 2: Verifieer import laadt**

Run: `.venv/bin/python -c "import scripts.migrate_to_supabase as m; assert 'hrv' in m.TABLES and 'sleep' in m.TABLES and 'hrv' in m.TABLE_PKS; print('ok')"`
Expected: print `ok`.

- [ ] **Step 3: Commit**

```bash
git add scripts/migrate_to_supabase.py
git commit -m "feat(migrate): push hrv and sleep tables to Supabase"
```

---

## Task 7: `metrics.py` — afgeleide metrics (pure functies)

**Files:**
- Create: `metrics.py`
- Test: `tests/test_metrics.py`

- [ ] **Step 1: Schrijf de falende tests**

Maak `tests/test_metrics.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metrics import pace_at_hr, weekly_volume_km


def test_pace_at_hr_averages_runs_in_band():
    runs = [
        {"date": "2026-07-01", "distance_m": 10000, "duration_s": 3000, "avg_hr": 150},  # 5:00/km, in band
        {"date": "2026-07-03", "distance_m": 8000, "duration_s": 2560, "avg_hr": 148},   # 5:20/km, in band
        {"date": "2026-07-05", "distance_m": 5000, "duration_s": 1200, "avg_hr": 175},   # buiten band
    ]
    trend = pace_at_hr(runs, hr_min=145, hr_max=155)
    assert len(trend) == 2
    assert trend[0]["pace_s_per_km"] == 300.0
    assert trend[1]["pace_s_per_km"] == 320.0


def test_pace_at_hr_empty_when_no_runs_in_band():
    runs = [{"date": "2026-07-05", "distance_m": 5000, "duration_s": 1200, "avg_hr": 175}]
    assert pace_at_hr(runs, hr_min=145, hr_max=155) == []


def test_weekly_volume_sums_by_iso_week():
    runs = [
        {"date": "2026-06-29", "distance_m": 10000},  # ISO week 27 (ma)
        {"date": "2026-07-01", "distance_m": 5000},   # ISO week 27
        {"date": "2026-07-06", "distance_m": 8000},   # ISO week 28
    ]
    weeks = weekly_volume_km(runs)
    assert weeks["2026-W27"] == 15.0
    assert weeks["2026-W28"] == 8.0
```

- [ ] **Step 2: Run tests — verwacht falen**

Run: `.venv/bin/python -m pytest tests/test_metrics.py -v`
Expected: FAIL met `ModuleNotFoundError: No module named 'metrics'`.

- [ ] **Step 3: Implementeer `metrics.py`**

```python
"""Pure functies: afgeleide hardloop-metrics uit opgeslagen data. Geen I/O."""
from __future__ import annotations

from datetime import date as _date


def pace_at_hr(runs: list[dict], hr_min: int = 145, hr_max: int = 155) -> list[dict]:
    """Aerobe efficiëntie: pace (s/km) van runs met gemiddelde HR in de band.

    runs: dicts met date, distance_m, duration_s, avg_hr. Gesorteerd op date oplopend.
    """
    out = []
    for r in runs:
        hr = r.get("avg_hr")
        dist_m = r.get("distance_m") or 0
        dur_s = r.get("duration_s") or 0
        if hr is None or dist_m <= 0 or dur_s <= 0:
            continue
        if hr_min <= hr <= hr_max:
            pace = dur_s / (dist_m / 1000)
            out.append({"date": r["date"], "pace_s_per_km": round(pace, 1)})
    return out


def weekly_volume_km(runs: list[dict]) -> dict[str, float]:
    """Som van afstand (km) per ISO-week (sleutel 'YYYY-Www')."""
    totals: dict[str, float] = {}
    for r in runs:
        d = _date.fromisoformat(r["date"][:10])
        iso_year, iso_week, _ = d.isocalendar()
        key = f"{iso_year}-W{iso_week:02d}"
        totals[key] = totals.get(key, 0.0) + (r.get("distance_m") or 0) / 1000.0
    return {k: round(v, 1) for k, v in totals.items()}
```

- [ ] **Step 4: Run tests — verwacht slagen**

Run: `.venv/bin/python -m pytest tests/test_metrics.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add metrics.py tests/test_metrics.py
git commit -m "feat(metrics): pace-at-HR and weekly-volume pure functions"
```

---

## Task 8: `coach_rules.py` — regelgebaseerde duiding

**Files:**
- Create: `coach_rules.py`
- Test: `tests/test_coach_rules.py`

Interface bewust stabiel: elke functie neemt een simpele dict en geeft een NL-string terug. Fase 4 kan de implementatie vervangen door een LLM zonder de aanroepende code te wijzigen.

- [ ] **Step 1: Schrijf de falende tests**

Maak `tests/test_coach_rules.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from coach_rules import duiding_readiness, duiding_load, duiding_run


def test_duiding_readiness_high():
    msg = duiding_readiness({"score": 82})
    assert "goed" in msg.lower() or "klaar" in msg.lower()


def test_duiding_readiness_low_mentions_rust():
    msg = duiding_readiness({"score": 35})
    assert "rust" in msg.lower() or "herstel" in msg.lower()


def test_duiding_load_high_warns():
    msg = duiding_load({"acwr": 1.6})
    assert "hoog" in msg.lower() or "blessure" in msg.lower()


def test_duiding_load_optimal():
    msg = duiding_load({"acwr": 1.0})
    assert "optimaal" in msg.lower() or "veilig" in msg.lower()


def test_duiding_run_negative_split():
    msg = duiding_run({"splits_pace": [324, 315, 306, 302, 294]})
    assert "negative split" in msg.lower() or "sneller" in msg.lower()


def test_duiding_run_handles_missing_data():
    assert isinstance(duiding_run({}), str)
    assert isinstance(duiding_readiness({}), str)
    assert isinstance(duiding_load({}), str)
```

- [ ] **Step 2: Run tests — verwacht falen**

Run: `.venv/bin/python -m pytest tests/test_coach_rules.py -v`
Expected: FAIL met `ModuleNotFoundError: No module named 'coach_rules'`.

- [ ] **Step 3: Implementeer `coach_rules.py`**

```python
"""Regelgebaseerde coach-duiding (NL). Stabiele interface — Fase 4 vervangt de body
door een LLM zonder dat aanroepende code wijzigt. Elke functie: dict in, str uit."""
from __future__ import annotations


def duiding_readiness(snapshot: dict) -> str:
    score = snapshot.get("score")
    if score is None:
        return "Nog geen readiness-data voor vandaag."
    if score >= 75:
        return "Je bent goed hersteld en klaar voor een pittige sessie."
    if score >= 50:
        return "Redelijk hersteld — een rustige tot gemiddelde training past vandaag."
    return "Je herstel is laag. Kies voor rust of een lichte herstel-run."


def duiding_load(load: dict) -> str:
    acwr = load.get("acwr")
    if acwr is None:
        return "Nog onvoldoende data om je belasting te beoordelen."
    if acwr > 1.5:
        return f"Zeer hoge belasting (ratio {acwr:.1f}) — blessurerisico. Neem rust."
    if acwr > 1.3:
        return f"Belasting loopt op (ratio {acwr:.1f}). Houd deze week iets in."
    if acwr < 0.8:
        return f"Belasting is laag (ratio {acwr:.1f}). Ruimte om volume op te bouwen."
    return f"Je belasting is optimaal en veilig (ratio {acwr:.1f})."


def duiding_run(run: dict) -> str:
    paces = run.get("splits_pace") or []
    if len(paces) >= 3:
        if paces[-1] < paces[0]:
            return "Mooie negative split — je laatste kilometers waren je snelste."
        if paces[-1] > paces[0] * 1.05:
            return "Je tempo zakte richting het einde. Let op je pacing en herstel."
    hr = run.get("avg_hr")
    if hr is not None:
        return "Nette run met je hartslag onder controle."
    return "Run opgeslagen."
```

- [ ] **Step 4: Run tests — verwacht slagen**

Run: `.venv/bin/python -m pytest tests/test_coach_rules.py -v`
Expected: 6 PASS.

- [ ] **Step 5: Commit**

```bash
git add coach_rules.py tests/test_coach_rules.py
git commit -m "feat(coach): rule-based duiding for readiness, load, run"
```

---

## Task 9: `/athlete/{id}/home` endpoint

**Files:**
- Modify: `api/routes.py`
- Test: `tests/test_api.py`

Consolideert readiness (incl. HRV/slaap/body-battery-niveau), fitheid-samenvatting, belasting-samenvatting, laatste-run-samenvatting, en duiding.

- [ ] **Step 1: Schrijf de falende test**

Voeg toe aan `tests/test_api.py` (de bestaande `setup_db`-fixture seed `vriendin`). Voeg eerst readiness al aanwezig; test de vorm:

```python
def test_home_endpoint_shape():
    client = TestClient(app)
    r = client.get("/api/athlete/vriendin/home")
    assert r.status_code == 200
    body = r.json()
    assert set(["readiness", "fitness", "load", "last_run"]).issubset(body.keys())
    assert "duiding" in body["readiness"]
    assert "duiding" in body["load"]


def test_home_endpoint_404_unknown_athlete():
    client = TestClient(app)
    assert client.get("/api/athlete/nobody/home").status_code == 404
```

- [ ] **Step 2: Run test — verwacht falen**

Run: `.venv/bin/python -m pytest tests/test_api.py::test_home_endpoint_shape -v`
Expected: FAIL met 404 of `KeyError` (endpoint bestaat nog niet).

- [ ] **Step 3: Implementeer het endpoint**

Bovenaan `api/routes.py` bij de imports toevoegen:

```python
import coach_rules
```

Voeg dit endpoint toe (na `get_hero`):

```python
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
```

- [ ] **Step 4: Run tests — verwacht slagen**

Run: `.venv/bin/python -m pytest tests/test_api.py::test_home_endpoint_shape tests/test_api.py::test_home_endpoint_404_unknown_athlete -v`
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add api/routes.py tests/test_api.py
git commit -m "feat(api): consolidated /home endpoint with readiness, fitness, load, last run + duiding"
```

---

## Task 10: Volledige test-suite + lokale sync-rooktest

**Files:** geen wijziging — validatie.

- [ ] **Step 1: Draai de volledige suite**

Run: `.venv/bin/python -m pytest -q`
Expected: alle tests PASS (bestaande + nieuwe).

- [ ] **Step 2: Rooktest ingest op echte pull-data (SQLite)**

Run: `.venv/bin/python ingest.py --athlete rowan --name Rowan`
Expected: output toont o.a. `hrv:` en `sleep:` regels met tellingen; geen exceptions.

- [ ] **Step 3: Verifieer /home tegen lokale data**

Run (twee terminals of achtergrond): `.venv/bin/uvicorn api.main:app --port 8000 &` daarna
`curl -s localhost:8000/api/athlete/rowan/home | .venv/bin/python -m json.tool | head -40`
Expected: JSON met `readiness`, `fitness`, `load`, `last_run` en gevulde `duiding`-velden. Stop de server daarna (`kill %1`).

- [ ] **Step 4: Commit (indien nog iets aangepast)**

```bash
git add -A && git commit -m "test: full suite green + home smoke-verified on real data" || echo "niets te committen"
```

---

## Zelf-review (uitgevoerd)

- **Spec-dekking:** ingest HRV ✓ (T2,5), slaap ✓ (T3,5), body-battery-niveau ✓ (T4), `metrics.py` pace@HR + weekvolume ✓ (T7), `coach_rules.py` ✓ (T8), view-klare `/home` ✓ (T9), migrate meegroeit ✓ (T6), foutafhandeling/lege staten (null-tolerant ingest + `None`-velden in `/home` + 404) ✓. Fitheid-detail (rust-HR-trend) en belasting-detail bestaan al deels als losse endpoints (`vo2max_trend`, `training_load`, `run_efficiency`); frontend consumeert die in Plan 2. pace@HR-trend-endpoint wordt in Plan 2 toegevoegd als de frontend het nodig heeft (functie staat klaar in `metrics.py`).
- **Placeholders:** geen TBD/TODO; alle stappen bevatten echte code + commando's.
- **Type-consistentie:** `ingest_hrv`/`ingest_sleep`/`ingest_body_battery` signatures matchen aanroep in `run_ingest`; `coach_rules.duiding_*` dict-in/str-uit matcht gebruik in `/home`; `weekly_volume_km`/`pace_at_hr` matchen tests.

## Volgende plan
Plan 2: frontend-herbouw (5 schermen + UI-primitieven, mobiel-eerst) op deze endpoints + PWA (manifest, service worker, icoon, installeerbaar).
