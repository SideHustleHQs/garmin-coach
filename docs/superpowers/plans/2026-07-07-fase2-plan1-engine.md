# Fase 2 · Plan 1 — Planningsengine (backend)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Een regelgebaseerde engine die per atleet een compleet trainingsplan (nu → racedag) genereert en via API-endpoints ontsluit, plus de plannen voor Rowan (marathon sub-4) en vriendin (16 km) aanmaken.

**Architecture:** Nieuwe pure module `plan_engine.py` (paces → periodisering → week-assemblage, geen I/O). Drie nieuwe tabellen in de bestaande dual SQLite/Postgres-laag. Endpoints in `api/routes.py` volgen het bestaande `_conn`/`_exec`/`_athlete_or_404`-patroon. `coach_rules.py` krijgt workout-duiding.

**Tech Stack:** Python 3.9 (`from __future__ import annotations`), FastAPI, SQLite+Postgres (psycopg2), pytest. Repo: `~/garmin-coach`. Tests: `.venv/bin/python -m pytest` (conftest forceert SQLite).

**Scope:** Alleen backend + plan-bootstrap. Schema-UI = Plan 2. Statisch plan (geen adaptief=Fase 3, geen LLM=Fase 4).

---

## Bestandsstructuur

| Bestand | Verantwoordelijkheid | Actie |
|---|---|---|
| `db.py` | Schema | Modify: 3 tabellen |
| `scripts/migrate_to_supabase.py` | SQLite→Postgres | Modify: TABLES/TABLE_PKS |
| `plan_engine.py` | Paces, periodisering, week-assemblage, generate_plan, estimate_finish (pure) | Create |
| `coach_rules.py` | `duiding_workout(run_type, phase)` | Modify |
| `api/routes.py` | Endpoints plan/week/workout/register + POST plan | Modify |
| `scripts/create_plans.py` | Seed prefs + genereer beide plannen | Create |
| `tests/test_plan_engine.py` | Engine-tests | Create |
| `tests/test_coach_rules.py` | duiding-test | Modify |
| `tests/test_api.py` | Endpoint-tests | Modify |

Tests draaien vanuit repo-root: `.venv/bin/python -m pytest`.

---

## Task 1: DB-schema — 3 tabellen

**Files:** Modify `db.py` (`SCHEMA_SQLITE`, `SCHEMA_PG`).

- [ ] **Step 1: Voeg toe aan `SCHEMA_SQLITE`** (vóór de sluitende `"""`):

```sql
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
```

- [ ] **Step 2: Spiegel in `SCHEMA_PG`** — dezelfde 3 tabellen, met deze verschillen voor Postgres:
`training_plan.id` → `SERIAL PRIMARY KEY` (i.p.v. `INTEGER PRIMARY KEY AUTOINCREMENT`); laat de FK-regels weg (SCHEMA_PG bevat geen FK's, conform bestaande stijl).

- [ ] **Step 3: Verifieer laadt**

Run: `.venv/bin/python -c "import db; db.init_db(db.Path('/tmp/p.db')); db.init_db(db.Path('/tmp/p.db')); print('ok')"; rm -f /tmp/p.db`
Expected: `ok`, idempotent, geen fouten.

- [ ] **Step 4: Commit**

```bash
git add db.py
git commit -m "feat(db): training_plan, planned_workout, athlete_training_prefs tables"
```

---

## Task 2: migrate_to_supabase — nieuwe tabellen

**Files:** Modify `scripts/migrate_to_supabase.py`.

- [ ] **Step 1:** Voeg aan `TABLES` (aan het eind) toe: `"athlete_training_prefs"`, `"training_plan"`, `"planned_workout"`. Voeg aan `TABLE_PKS` toe:

```python
    "athlete_training_prefs": ["athlete_id"],
    "training_plan": ["id"],
    "planned_workout": ["athlete_id", "date"],
```

- [ ] **Step 2: Verifieer**

Run: `.venv/bin/python -c "import importlib.util; s=importlib.util.spec_from_file_location('m','scripts/migrate_to_supabase.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); assert all(t in m.TABLES for t in ['training_plan','planned_workout','athlete_training_prefs']); print('ok')"` (indien `DATABASE_URL` vereist bij import: prefix met `DATABASE_URL=postgresql://dummy`).
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add scripts/migrate_to_supabase.py
git commit -m "feat(migrate): push training plan tables to Supabase"
```

---

## Task 3: plan_engine — `compute_paces` (TDD)

**Files:** Create `plan_engine.py`; Create `tests/test_plan_engine.py`.

- [ ] **Step 1: Falende test** — `tests/test_plan_engine.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from plan_engine import compute_paces


def test_compute_paces_from_goal_time():
    # sub-4 marathon: 14400s / 42.195km = 341 s/km marathonpace
    p = compute_paces(goal_time_s=14400, distance_km=42.195, current_easy_s=None)
    assert p["mp"] == 341
    assert p["easy"] == 376      # mp + 35
    assert p["long"] == 361      # mp + 20
    assert p["tempo"] == 316     # mp - 25
    assert p["interval"] == 286  # mp - 55


def test_compute_paces_without_goal_uses_current_easy():
    p = compute_paces(goal_time_s=None, distance_km=16.1, current_easy_s=360)
    # race-pace = current_easy - 20
    assert p["mp"] == 340
    assert p["easy"] == 360
```

- [ ] **Step 2: Run — faalt**

Run: `.venv/bin/python -m pytest tests/test_plan_engine.py::test_compute_paces_from_goal_time -v` → FAIL (ModuleNotFoundError).

- [ ] **Step 3: Implementeer** — `plan_engine.py`:

```python
"""Regelgebaseerde trainingsplan-engine. Pure functies, geen I/O."""
from __future__ import annotations


def compute_paces(goal_time_s: int | None, distance_km: float, current_easy_s: int | None) -> dict:
    """Doel-paces in seconden/km. Met doeltijd: afgeleid van racepace.
    Zonder doeltijd: afgeleid van huidige easy-pace."""
    if goal_time_s:
        mp = round(goal_time_s / distance_km)
    elif current_easy_s:
        mp = current_easy_s - 20
    else:
        mp = 360  # conservatieve default (6:00/km)
    return {
        "mp": mp,
        "easy": (current_easy_s if (goal_time_s is None and current_easy_s) else mp + 35),
        "long": mp + 20,
        "tempo": mp - 25,
        "interval": mp - 55,
    }
```

- [ ] **Step 4: Run — slaagt**

Run: `.venv/bin/python -m pytest tests/test_plan_engine.py -v` → 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add plan_engine.py tests/test_plan_engine.py
git commit -m "feat(engine): compute_paces from goal time or current fitness"
```

---

## Task 4: plan_engine — `phase_for_week` (TDD)

**Files:** Modify `plan_engine.py`, `tests/test_plan_engine.py`.

- [ ] **Step 1: Falende test** (toevoegen):

```python
from plan_engine import phase_for_week

def test_phase_for_week_boundaries():
    total = 14
    assert phase_for_week(1, total) == "base"
    assert phase_for_week(4, total) == "base"    # <=30%
    assert phase_for_week(5, total) == "build"
    assert phase_for_week(10, total) == "build"  # <=70%
    assert phase_for_week(11, total) == "peak"
    assert phase_for_week(12, total) == "peak"   # <=85%
    assert phase_for_week(13, total) == "taper"
    assert phase_for_week(14, total) == "taper"
```

- [ ] **Step 2: Run — faalt** (`ImportError: phase_for_week`).

- [ ] **Step 3: Implementeer** (toevoegen aan `plan_engine.py`):

```python
def phase_for_week(week: int, total_weeks: int) -> str:
    """Periodiseringsfase op basis van positie in het plan (1-indexed week)."""
    frac = week / total_weeks
    if frac <= 0.30:
        return "base"
    if frac <= 0.70:
        return "build"
    if frac <= 0.85:
        return "peak"
    return "taper"
```

- [ ] **Step 4: Run — slaagt.** `.venv/bin/python -m pytest tests/test_plan_engine.py -v`

- [ ] **Step 5: Commit**

```bash
git add plan_engine.py tests/test_plan_engine.py
git commit -m "feat(engine): phase_for_week periodization boundaries"
```

---

## Task 5: plan_engine — `long_run_progression` (TDD)

**Files:** Modify `plan_engine.py`, `tests/test_plan_engine.py`.

- [ ] **Step 1: Falende test**:

```python
from plan_engine import long_run_progression

def test_long_run_progression_builds_cutbacks_and_tapers():
    lr = long_run_progression(total_weeks=14, start_km=14, peak_km=32)
    assert len(lr) == 14
    assert lr[0] == 14                    # week 1 = start
    assert lr[10] == 32 or lr[9] == 32    # piek ~3 wk voor eind (peak fase)
    assert lr[13] < lr[10]                # taper: laatste week korter dan piek
    assert lr[2] < lr[1] or lr[3] < lr[2] # cutback aanwezig in opbouw
    assert max(lr) == 32                  # piek = peak_km
```

- [ ] **Step 2: Run — faalt.**

- [ ] **Step 3: Implementeer** (toevoegen):

```python
def long_run_progression(total_weeks: int, start_km: float, peak_km: float) -> list[float]:
    """Lange-duurloop per week: lineaire opbouw met cutback elke 3e week,
    piek in de peak-fase, daarna taper omlaag."""
    peak_week = max(1, round(total_weeks * 0.85))  # laatste peak-week
    out: list[float] = []
    for w in range(1, total_weeks + 1):
        if w >= peak_week:
            # taper: van piek terug naar ~60%
            steps_after = total_weeks - peak_week
            i = w - peak_week
            km = peak_km - (peak_km * 0.4) * (i / steps_after) if steps_after else peak_km
        else:
            base = start_km + (peak_km - start_km) * ((w - 1) / (peak_week - 1))
            if w % 3 == 0:  # cutback elke 3e week
                base *= 0.75
            km = base
        out.append(round(km))
    out[peak_week - 1] = round(peak_km)  # verzeker exacte piek
    return out
```

- [ ] **Step 4: Run — slaagt.**

- [ ] **Step 5: Commit**

```bash
git add plan_engine.py tests/test_plan_engine.py
git commit -m "feat(engine): long-run progression with cutbacks and taper"
```

---

## Task 6: plan_engine — `assemble_week` (TDD)

**Files:** Modify `plan_engine.py`, `tests/test_plan_engine.py`.

- [ ] **Step 1: Falende test**:

```python
from plan_engine import assemble_week

PREFS_ROWAN = {
    "run_days": ["mon", "thu", "sat"],
    "fixed_days": {"tue": "strength", "wed": "hyrox", "fri": "strength"},
}

def test_assemble_week_places_runs_and_respects_hyrox():
    days = assemble_week(
        run_days=PREFS_ROWAN["run_days"], fixed_days=PREFS_ROWAN["fixed_days"],
        long_km=20, easy_km=7, quality={"type": "tempo", "title": "Tempo 8 km"},
    )
    by = {d["weekday"]: d for d in days}
    assert len(days) == 7
    assert by["wed"]["day_type"] == "hyrox"
    assert by["tue"]["day_type"] == "strength"
    assert by["sat"]["run_type"] == "long"          # lange run in weekend-slot
    # thu volgt direct op hyrox(wed) → mag GEEN quality/long zijn
    assert by["thu"]["run_type"] == "easy"
    # quality op een run-dag die niet direct na hyrox valt (mon)
    assert by["mon"]["run_type"] == "quality"
    # dagen zonder run/fixed = rest
    assert by["sun"]["day_type"] == "rest"
```

- [ ] **Step 2: Run — faalt.**

- [ ] **Step 3: Implementeer** (toevoegen):

```python
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
HARD_TYPES = {"hyrox"}


def assemble_week(run_days: list[str], fixed_days: dict, long_km: float,
                  easy_km: float, quality: dict) -> list[dict]:
    """Bouw één week: lange run op laatste run-dag, quality op een run-dag die
    NIET direct na een harde (hyrox) dag valt, easy op de rest. Fixed dagen
    (strength/hyrox) ingevuld, overige dagen rest."""
    long_day = run_days[-1]
    # kandidaat-quality-dagen: run-dagen (excl. long) waarvan de vorige dag geen hard-type is
    def prev(d):
        return WEEKDAYS[(WEEKDAYS.index(d) - 1) % 7]
    candidates = [d for d in run_days if d != long_day and fixed_days.get(prev(d)) not in HARD_TYPES]
    quality_day = candidates[0] if candidates else next(d for d in run_days if d != long_day)

    days = []
    for wd in WEEKDAYS:
        if wd == long_day:
            days.append({"weekday": wd, "day_type": "run", "run_type": "long",
                         "distance_km": long_km, "title": f"Lange duurloop {round(long_km)} km"})
        elif wd == quality_day:
            days.append({"weekday": wd, "day_type": "run", "run_type": "quality",
                         "distance_km": None, "title": quality["title"], "quality": quality})
        elif wd in run_days:
            days.append({"weekday": wd, "day_type": "run", "run_type": "easy",
                         "distance_km": easy_km, "title": f"Rustige duurloop {round(easy_km)} km"})
        elif wd in fixed_days:
            days.append({"weekday": wd, "day_type": fixed_days[wd], "run_type": None,
                         "title": {"hyrox": "Hyrox", "strength": "Krachttraining"}.get(fixed_days[wd], fixed_days[wd])})
        else:
            days.append({"weekday": wd, "day_type": "rest", "run_type": None, "title": "Rust"})
    return days
```

- [ ] **Step 4: Run — slaagt.**

- [ ] **Step 5: Commit**

```bash
git add plan_engine.py tests/test_plan_engine.py
git commit -m "feat(engine): assemble_week places runs around fixed hyrox/strength days"
```

---

## Task 7: coach_rules — `duiding_workout` (TDD)

**Files:** Modify `coach_rules.py`, `tests/test_coach_rules.py`.

- [ ] **Step 1: Falende test** (toevoegen aan `tests/test_coach_rules.py`):

```python
from coach_rules import duiding_workout

def test_duiding_workout_variants():
    assert isinstance(duiding_workout("long", "build"), str)
    assert "lang" in duiding_workout("long", "build").lower()
    assert "taper" in duiding_workout("easy", "taper").lower() or "herstel" in duiding_workout("easy", "taper").lower()
    assert isinstance(duiding_workout("quality", "peak"), str)
```

- [ ] **Step 2: Run — faalt** (`ImportError: duiding_workout`).

- [ ] **Step 3: Implementeer** (toevoegen aan `coach_rules.py`):

```python
def duiding_workout(run_type: str, phase: str) -> str:
    if phase == "taper":
        return "Taper-fase: kort en scherp, focus op herstel richting je race."
    if run_type == "long":
        return "Je lange duurloop bouwt de duur-uithouding die je marathon draagt."
    if run_type == "quality":
        return {"base": "Rustige kwaliteit om je snelheid te wekken.",
                "build": "Tempo-werk op racepace-niveau — hier win je je tijd.",
                "peak": "Scherpe piek-sessie op racepace, dicht bij je doel."}.get(phase, "Kwaliteitstraining.")
    return "Rustige duurloop op easy-pace — bouwt je aerobe basis, houdt herstel hoog."
```

- [ ] **Step 4: Run — slaagt.** `.venv/bin/python -m pytest tests/test_coach_rules.py -v`

- [ ] **Step 5: Commit**

```bash
git add coach_rules.py tests/test_coach_rules.py
git commit -m "feat(coach): rule-based workout duiding per run_type and phase"
```

---

## Task 8: plan_engine — `generate_plan` + `estimate_finish` (TDD)

**Files:** Modify `plan_engine.py`, `tests/test_plan_engine.py`.

- [ ] **Step 1: Falende test**:

```python
from plan_engine import generate_plan, estimate_finish
import datetime

def test_generate_plan_full_shape():
    plan = {"race_distance_km": 42.195, "goal_time_s": 14400,
            "start_date": "2026-07-13", "weeks": 14}
    prefs = {"run_days": ["mon", "thu", "sat"],
             "fixed_days": {"tue": "strength", "wed": "hyrox", "fri": "strength"}}
    fitness = {"current_easy_s": 375, "longest_km": 14}
    rows = generate_plan(plan, prefs, fitness)
    # 14 weken * 7 dagen = 98 dagrijen
    assert len(rows) == 98
    runs = [r for r in rows if r["day_type"] == "run"]
    assert len(runs) == 14 * 3  # 3 runs/week
    assert any(r["run_type"] == "long" for r in runs)
    assert all("phase" in r and "date" in r for r in rows)
    # taper aanwezig in laatste week
    assert any(r["phase"] == "taper" for r in rows)
    # quality-run heeft segments met doel-pace
    q = next(r for r in runs if r["run_type"] == "quality")
    assert q["segments"] and isinstance(q["segments"], list)

def test_estimate_finish_returns_range():
    lo, hi = estimate_finish(distance_km=42.195, goal_time_s=14400, fitness={"current_easy_s": 375})
    assert lo < hi
    assert isinstance(lo, int) and isinstance(hi, int)
```

- [ ] **Step 2: Run — faalt.**

- [ ] **Step 3: Implementeer** (toevoegen aan `plan_engine.py`):

```python
import datetime as _dt


def _quality_spec(phase: str, paces: dict) -> dict:
    """Segments + titel voor de kwaliteitsrun per fase."""
    if phase == "base":
        return {"type": "tempo", "title": "Tempo-run 6 km", "segments": [
            {"label": "Inlopen 1,5 km", "distance_m": 1500, "target_pace_s": paces["easy"]},
            {"label": "3 km tempo", "distance_m": 3000, "target_pace_s": paces["tempo"]},
            {"label": "Uitlopen 1,5 km", "distance_m": 1500, "target_pace_s": paces["easy"]}]}
    if phase == "peak":
        return {"type": "interval", "title": "Intervallen 8 km", "segments": [
            {"label": "Inlopen 2 km", "distance_m": 2000, "target_pace_s": paces["easy"]},
            {"label": "5× 1 km", "reps": 5, "distance_m": 1000, "target_pace_s": paces["interval"]},
            {"label": "tussen 400 m dribbel", "distance_m": 400, "target_pace_s": paces["easy"] + 20},
            {"label": "Uitlopen 1,5 km", "distance_m": 1500, "target_pace_s": paces["easy"]}]}
    return {"type": "tempo", "title": "Tempo-intervallen 8 km", "segments": [
        {"label": "Inlopen 2 km", "distance_m": 2000, "target_pace_s": paces["easy"]},
        {"label": "4× 1 km tempo", "reps": 4, "distance_m": 1000, "target_pace_s": paces["tempo"]},
        {"label": "tussen 400 m dribbel", "distance_m": 400, "target_pace_s": paces["easy"] + 20},
        {"label": "Uitlopen 1,5 km", "distance_m": 1500, "target_pace_s": paces["easy"]}]}


def generate_plan(plan: dict, prefs: dict, fitness: dict) -> list[dict]:
    import coach_rules
    weeks = plan["weeks"]
    paces = compute_paces(plan.get("goal_time_s"), plan["race_distance_km"], fitness.get("current_easy_s"))
    peak_km = 32 if plan["race_distance_km"] > 30 else round(plan["race_distance_km"] * 1.15)
    start_km = max(fitness.get("longest_km") or 8, round(peak_km * 0.45))
    long_by_week = long_run_progression(weeks, start_km, peak_km)
    start = _dt.date.fromisoformat(plan["start_date"])

    rows: list[dict] = []
    for w in range(1, weeks + 1):
        phase = phase_for_week(w, weeks)
        quality = _quality_spec(phase, paces)
        easy_km = max(5, round(long_by_week[w - 1] * 0.4))
        days = assemble_week(prefs["run_days"], prefs["fixed_days"],
                             long_km=long_by_week[w - 1], easy_km=easy_km, quality=quality)
        for d in days:
            date = start + _dt.timedelta(days=(w - 1) * 7 + WEEKDAYS.index(d["weekday"]))
            run_type = d.get("run_type")
            if run_type == "quality":
                segments = quality["segments"]
                target = paces["tempo"]
            elif run_type == "long":
                segments = [{"label": f"Lange duurloop {round(d['distance_km'])} km",
                             "distance_m": int(d["distance_km"] * 1000), "target_pace_s": paces["long"]}]
                target = paces["long"]
            elif run_type == "easy":
                segments = [{"label": d["title"], "distance_m": int((d["distance_km"] or 0) * 1000),
                             "target_pace_s": paces["easy"]}]
                target = paces["easy"]
            else:
                segments = None
                target = None
            rows.append({
                "date": date.isoformat(), "week_num": w, "phase": phase,
                "day_type": d["day_type"], "run_type": run_type, "title": d["title"],
                "distance_km": d.get("distance_km"), "segments": segments, "target_pace_s": target,
                "coach_note": coach_rules.duiding_workout(run_type, phase) if run_type else None,
            })
    return rows


def estimate_finish(distance_km: float, goal_time_s: int | None, fitness: dict) -> tuple[int, int]:
    """Geschatte finishtijd-range (s). Met doeltijd: rond het doel; anders uit easy-pace."""
    if goal_time_s:
        center = goal_time_s
    else:
        easy = fitness.get("current_easy_s") or 360
        center = round((easy - 15) * distance_km)
    return (round(center * 0.97), round(center * 1.03))
```

- [ ] **Step 4: Run — slaagt.** `.venv/bin/python -m pytest tests/test_plan_engine.py -v` (alle engine-tests groen).

- [ ] **Step 5: Commit**

```bash
git add plan_engine.py tests/test_plan_engine.py
git commit -m "feat(engine): generate_plan (full periodized schedule) + estimate_finish"
```

---

## Task 9: API — `POST /plan` + `GET /plan` (TDD)

**Files:** Modify `api/routes.py`, `tests/test_api.py`.

Context: `api/routes.py` heeft `_conn()`, `_exec(conn, sql, params)` (`?`→`%s`), `_athlete_or_404`. Voor fitheid hergebruik: bereken `current_easy_s` als de mediaan-pace van recente easy runs, `longest_km` als max distance — of simpel: gemiddelde pace + max afstand uit `activities`.

- [ ] **Step 1: Falende test** (toevoegen aan `tests/test_api.py`; de `setup_db`-fixture seed `vriendin` met runs):

```python
def test_create_and_get_plan():
    client = TestClient(app)
    body = {"race_name": "Test Marathon", "race_date": "2026-10-18",
            "race_distance_km": 42.195, "goal_time_s": 14400,
            "start_date": "2026-07-13", "weeks": 14,
            "run_days": ["mon", "thu", "sat"],
            "fixed_days": {"tue": "strength", "wed": "hyrox", "fri": "strength"}}
    r = client.post("/api/athlete/vriendin/plan", json=body)
    assert r.status_code == 200
    g = client.get("/api/athlete/vriendin/plan").json()
    assert g["race_name"] == "Test Marathon"
    assert g["weeks"] == 14
    assert "estimated_time_s" in g and len(g["estimated_time_s"]) == 2
    assert g["total_planned_km"] > 0
```

- [ ] **Step 2: Run — faalt** (404).

- [ ] **Step 3: Implementeer** — voeg bovenaan `api/routes.py` toe: `import json`, `import plan_engine` (json is er waarschijnlijk al). Voeg een helper + twee endpoints toe:

```python
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
        if db_module.use_postgres():
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
```

- [ ] **Step 4: Run — slaagt.** `.venv/bin/python -m pytest tests/test_api.py::test_create_and_get_plan -v` → PASS; volledige suite groen.

- [ ] **Step 5: Commit**

```bash
git add api/routes.py tests/test_api.py
git commit -m "feat(api): POST /plan generates plan, GET /plan header + estimate"
```

---

## Task 10: API — `/plan/week`, `/workout/{date}`, register (TDD)

**Files:** Modify `api/routes.py`, `tests/test_api.py`.

- [ ] **Step 1: Falende test**:

```python
def test_plan_week_and_workout_and_register():
    client = TestClient(app)
    body = {"race_name": "M", "race_date": "2026-10-18", "race_distance_km": 42.195,
            "goal_time_s": 14400, "start_date": "2026-07-13", "weeks": 14,
            "run_days": ["mon", "thu", "sat"],
            "fixed_days": {"tue": "strength", "wed": "hyrox", "fri": "strength"}}
    client.post("/api/athlete/vriendin/plan", json=body)
    wk = client.get("/api/athlete/vriendin/plan/week?week=1").json()
    assert len(wk) == 7
    run_day = next(d for d in wk if d["day_type"] == "run")
    w = client.get(f"/api/athlete/vriendin/workout/{run_day['date']}").json()
    assert w["title"] and "segments" in w
    reg = client.post(f"/api/athlete/vriendin/workout/{run_day['date']}/register")
    assert reg.status_code == 200
    wk2 = client.get("/api/athlete/vriendin/plan/week?week=1").json()
    assert any(d["date"] == run_day["date"] and d["status"] == "done" for d in wk2)
```

- [ ] **Step 2: Run — faalt.**

- [ ] **Step 3: Implementeer** (toevoegen aan `api/routes.py`):

```python
def _wo_dict(r) -> dict:
    return {"date": r["date"], "week_num": r["week_num"], "phase": r["phase"],
            "day_type": r["day_type"], "run_type": r["run_type"], "title": r["title"],
            "distance_km": r["distance_km"], "target_pace_s": r["target_pace_s"],
            "coach_note": r["coach_note"], "status": r["status"],
            "segments": json.loads(r["segments"]) if r["segments"] else None}


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
        if db_module.use_postgres():
            conn.commit()
        return {"ok": True, "linked_activity_id": act["activity_id"] if act else None}
    finally:
        if db_module.use_postgres():
            conn.close()
```

- [ ] **Step 4: Run — slaagt.** Volledige suite groen.

- [ ] **Step 5: Commit**

```bash
git add api/routes.py tests/test_api.py
git commit -m "feat(api): plan week, workout detail, register-done endpoints"
```

---

## Task 11: Plan-bootstrap-script + eind-validatie

**Files:** Create `scripts/create_plans.py`.

- [ ] **Step 1: Schrijf `scripts/create_plans.py`** — maakt beide plannen via de engine tegen de actieve DB (SQLite of Supabase via `DATABASE_URL`):

```python
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
```

- [ ] **Step 2: Volledige suite + rooktest**

Run: `.venv/bin/python -m pytest -q` → alles groen.
Run: `.venv/bin/python scripts/create_plans.py` → print `rowan: 98 dagen gepland` en `vriendin: 70 dagen gepland` (lokale SQLite), geen exceptions.

- [ ] **Step 3: Verifieer plan-endpoint lokaal**

Run: `.venv/bin/uvicorn api.main:app --port 8000 & sleep 3; curl -s "localhost:8000/api/athlete/rowan/plan" | .venv/bin/python -m json.tool | head -20; curl -s "localhost:8000/api/athlete/rowan/plan/week?week=1" | .venv/bin/python -m json.tool | head -30; kill %1`
Expected: plan-header (race, weken, estimated_time_s) + een week met 7 dagen incl. runs met segments.

- [ ] **Step 4: Commit**

```bash
git add scripts/create_plans.py
git commit -m "feat(engine): plan bootstrap script for both athletes"
```

---

## Zelf-review (uitgevoerd)

- **Spec-dekking:** data-model ✓ (T1), migrate ✓ (T2), compute_paces ✓ (T3), periodisering ✓ (T4/T5), week-assemblage met Hyrox-regel ✓ (T6), coach-duiding ✓ (T7), generate_plan + estimate_finish ✓ (T8), endpoints plan/week/workout/register ✓ (T9/T10), bootstrap beide atleten ✓ (T11), foutafhandeling (geen plan → `{"plan": null}`; workout 404; onvoldoende fitheid → defaults in compute_paces/_fitness) ✓. Auto-match bij sync = handmatig register in Fase 2 (spec noemt beide toegestaan); volledige auto-match-in-sync valt naar Plan 2/Fase 3.
- **Placeholders:** geen TBD; alle stappen bevatten echte code + commando's.
- **Type-consistentie:** `generate_plan(plan, prefs, fitness)` en de rij-velden (`date/week_num/phase/day_type/run_type/title/distance_km/segments/target_pace_s/coach_note`) matchen de INSERT in T9 en `_wo_dict` in T10; `compute_paces`-sleutels (`mp/easy/long/tempo/interval`) matchen `_quality_spec`/`generate_plan`; `assemble_week` output-velden matchen het gebruik in `generate_plan`.

## Volgende plan
Plan 2 (frontend): Schema-tab (Optie A) — `PlanHeader` + `WeekStrip` + `WorkoutCard` op deze endpoints, API-client, build + deploy. Daarna plan-bootstrap tegen Supabase draaien zodat het live op het dashboard staat.
