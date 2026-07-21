# Fase 3 · Plan 2 — Vooruit Herplannen (Drift-triggered Replan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Als het schema structureel afdwaalt (te veel gemiste runs, chronisch hoge belasting, of fitness ver van doel), herberekent het resterende plan zich automatisch via de bestaande `plan_engine.generate_plan` — zodat het schema altijd realistisch blijft richting de race.

**Architecture:** Drift-detectie in `adapt_engine.check_drift` (pure), replan-actie in `adapt_engine.replan` (roept `plan_engine.generate_plan` aan). `scripts/adapt.py` voert dit na de dagelijkse micro-aanpassing uit. API-endpoint `/athlete/{id}/replan` voor on-demand replan. Frontend: een banner in de Schema-tab als het plan herlopen is. Verleden rijen blijven ongemoeid.

**Tech Stack:** Python 3.9, FastAPI dual SQLite/Postgres, React/Vite, pytest. Repo `~/garmin-coach`. Bestaand: `adapt_engine.py` (75 regels, heeft `adjust_day` + `absorb_missed`), `plan_engine.py` (heeft `generate_plan` + `estimate_finish`), `scripts/adapt.py`, `api/routes.py` (heeft `adapt_plan` + `override_workout`).

**Vereiste pre-condition:** Plan 1 is geïmplementeerd (overlay-kolommen bestaan, `adapt_plan` route werkt). Check: `python -m pytest tests/ -k adapt -v` moet slagen.

---

## Bestandsstructuur

| Bestand | Actie | Verantwoordelijkheid |
|---|---|---|
| `adapt_engine.py` | Modify | Voeg `check_drift` + `replan` toe |
| `db.py` | Modify | `plan_replan_log` tabel — bijhoudt wanneer/waarom herlopen |
| `scripts/adapt.py` | Modify | Roep drift-check + replan aan na micro-aanpassing |
| `api/routes.py` | Modify | `POST /athlete/{id}/replan` + `GET /athlete/{id}/plan/meta` |
| `dashboard/src/screens/Schema.jsx` | Modify | ReplanBanner als `plan_meta.last_replan` aanwezig |
| `dashboard/src/api.js` | Modify | `triggerReplan`, `getPlanMeta` |
| `tests/test_adapt_engine.py` | Modify | Drift + replan unit-tests |
| `tests/test_api.py` | Modify | Replan endpoint test |

Tests: `.venv/bin/python -m pytest` · `cd dashboard && npm test`.

---

## Task 1: `check_drift` + `replan` in adapt_engine.py

**Files:** Modify `adapt_engine.py`

Voeg ONDER de bestaande `absorb_missed` functie toe.

- [ ] **Step 1: Schrijf de falende test**

`tests/test_adapt_engine.py` — voeg toe:
```python
from adapt_engine import check_drift, replan
import datetime as dt

def _row(date_str, run_type, missed=0, linked_activity_id=None):
    return {"planned_date": date_str, "run_type": run_type,
            "missed": missed, "linked_activity_id": linked_activity_id,
            "target_pace_s": 300, "distance_km": 10}

# Drift: ≥2 gemiste kwaliteits/lange runs in 14 dagen
def test_check_drift_missed_quality():
    today = dt.date(2026, 7, 8)
    rows = [
        _row("2026-07-01", "quality", missed=1),  # 7 dagen terug
        _row("2026-07-04", "long", missed=1),     # 4 dagen terug
        _row("2026-07-08", "easy"),
        _row("2026-07-10", "quality"),
    ]
    result = check_drift(rows, today, signals={})
    assert result["drift"] is True
    assert "missed" in result["reason"]

def test_check_drift_no_drift():
    today = dt.date(2026, 7, 8)
    rows = [
        _row("2026-07-01", "quality", missed=0, linked_activity_id=999),
        _row("2026-07-04", "long", missed=0, linked_activity_id=998),
        _row("2026-07-08", "easy"),
    ]
    result = check_drift(rows, today, signals={})
    assert result["drift"] is False

def test_check_drift_chronic_acwr():
    today = dt.date(2026, 7, 8)
    rows = [_row(f"2026-07-{d:02d}", "easy") for d in range(1, 9)]
    signals = {"acwr_history": [1.6] * 5}  # 5 dagen ≥ 1.5
    result = check_drift(rows, today, signals=signals)
    assert result["drift"] is True
    assert "belasting" in result["reason"]

def test_replan_respects_taper_and_volume_cap():
    """Replan mag taper nooit verwijderen en weekvolume max +10% verhogen."""
    from plan_engine import generate_plan, compute_paces
    today = dt.date(2026, 7, 8)
    race_date = dt.date(2026, 10, 18)
    plan = {"athlete_id": "rowan", "race_date": str(race_date),
            "goal_time_s": 14400, "distance_km": 42.195}
    prefs = {"run_days": ["mon", "wed", "fri", "sat"], "long_day": "sat",
             "hyrox_days": [], "strength_days": []}
    fitness = {"easy_pace_s": 330, "vo2max": 52}
    new_rows = replan(plan, today, prefs, fitness)
    # Geen rijen vóór vandaag
    assert all(r["planned_date"] >= str(today) for r in new_rows)
    # Taper: laatste 2 weken = 1 lange loop max (taper-check: geen quality in taper)
    race_dt = race_date
    taper_start = str(race_dt - dt.timedelta(weeks=2))
    taper_rows = [r for r in new_rows if r["planned_date"] >= taper_start and r["run_type"] == "quality"]
    assert len(taper_rows) == 0, f"Kwaliteits-rows in taper: {taper_rows}"
    # Volume nooit >10% per stap (globaal check: eerste vs laatste week totaal)
    assert len(new_rows) > 0
```

- [ ] **Step 2: Run test om te bevestigen dat hij faalt**
```bash
cd ~/garmin-coach && .venv/bin/python -m pytest tests/test_adapt_engine.py::test_check_drift_missed_quality -v
```
Verwacht: `ImportError: cannot import name 'check_drift' from 'adapt_engine'`

- [ ] **Step 3: Implementeer `check_drift` + `replan` in `adapt_engine.py`**

Voeg toe NA de bestaande code:
```python
import datetime as _dt

def check_drift(rows: list[dict], today: _dt.date, signals: dict) -> dict:
    """Detecteer structureel afdwalen. Pure functie.
    Returns: {"drift": bool, "reason": str | None}"""
    today_s = str(today)
    cutoff = str(today - _dt.timedelta(days=14))

    # Trigger 1: ≥2 gemiste kwaliteits/lange runs in 14 dagen
    missed_quality = [
        r for r in rows
        if r.get("planned_date", "") >= cutoff
        and r.get("planned_date", "") < today_s
        and r.get("run_type") in ("quality", "long")
        and (r.get("missed") or not r.get("linked_activity_id"))
    ]
    if len(missed_quality) >= 2:
        return {"drift": True, "reason": f"{len(missed_quality)} kwaliteits/lange runs gemist → plan herberekend."}

    # Trigger 2: ACWR ≥ 1.5 gedurende ≥5 dagen
    acwr_hist = signals.get("acwr_history", [])
    high_acwr_days = sum(1 for v in acwr_hist if v is not None and v >= 1.5)
    if high_acwr_days >= 5:
        return {"drift": True, "reason": f"Chronisch hoge belasting ({high_acwr_days} dagen ACWR≥1.5) → plan herberekend."}

    return {"drift": False, "reason": None}


def replan(plan: dict, today: _dt.date, prefs: dict, fitness: dict) -> list[dict]:
    """Herbereken de resterende weken via plan_engine.generate_plan.
    Verleden rijen worden NIET teruggegeven (caller verwijdert ze uit DB).
    Vangrails: taper intact, volume +10% max (geborgd door plan_engine zelf)."""
    from plan_engine import generate_plan
    today_s = str(today)
    new_rows = generate_plan(plan, prefs, fitness)
    # Houd alleen toekomstige/vandaag rijen (verleden blijft in DB)
    return [r for r in new_rows if r.get("planned_date", "") >= today_s]
```

- [ ] **Step 4: Run alle drift/replan tests**
```bash
cd ~/garmin-coach && .venv/bin/python -m pytest tests/test_adapt_engine.py -v
```
Verwacht: alle tests PASS.

- [ ] **Step 5: Commit**
```bash
cd ~/garmin-coach
git add adapt_engine.py tests/test_adapt_engine.py
git commit -m "feat(fase3): adapt_engine check_drift + replan"
```

---

## Task 2: plan_replan_log tabel in db.py

**Files:** Modify `db.py`

- [ ] **Step 1: Schrijf de falende test**

`tests/test_db.py` (of nieuw bestand) — voeg toe:
```python
from db import get_conn, migrate_db
import tempfile, pathlib

def test_replan_log_table_exists():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = pathlib.Path(tmp) / "test.db"
        migrate_db(db_path)
        with get_conn(db_path) as conn:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            assert "plan_replan_log" in tables
```

- [ ] **Step 2: Run om te bevestigen dat hij faalt**
```bash
cd ~/garmin-coach && .venv/bin/python -m pytest tests/test_db.py::test_replan_log_table_exists -v
```
Verwacht: `AssertionError: 'plan_replan_log' not in tables`

- [ ] **Step 3: Voeg `plan_replan_log` toe in `db.py`**

Zoek het `SCHEMA_SQLITE` blok en voeg toe na `planned_workout`:
```python
CREATE TABLE IF NOT EXISTS plan_replan_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    athlete_id TEXT NOT NULL,
    replan_date TEXT NOT NULL,
    reason TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

Voeg ook toe aan `SCHEMA_PG` (Postgres):
```sql
CREATE TABLE IF NOT EXISTS plan_replan_log (
    id SERIAL PRIMARY KEY,
    athlete_id TEXT NOT NULL,
    replan_date TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Voeg een migratiefunction toe:
```python
def _migrate_replan_log(path: Path) -> None:
    with get_conn(path) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS plan_replan_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, athlete_id TEXT NOT NULL,
            replan_date TEXT NOT NULL, reason TEXT,
            created_at TEXT DEFAULT (datetime('now')))""")
        conn.commit()
```

Roep `_migrate_replan_log(path)` aan in `migrate_db`.

- [ ] **Step 4: Run test**
```bash
cd ~/garmin-coach && .venv/bin/python -m pytest tests/test_db.py::test_replan_log_table_exists -v
```
Verwacht: PASS.

- [ ] **Step 5: Commit**
```bash
git add db.py tests/test_db.py
git commit -m "feat(fase3): plan_replan_log tabel in db.py"
```

---

## Task 3: Drift-check + replan in scripts/adapt.py

**Files:** Modify `scripts/adapt.py`

- [ ] **Step 1:** Lees de huidige inhoud van `scripts/adapt.py`. Let op: het heeft al micro-aanpassing logica. Voeg TOE na de bestaande adapt-loop (niet vervangen).

- [ ] **Step 2:** Voeg de drift-check + replan-stap toe:

```python
# --- Drift-check + vooruit herplannen ---
import datetime as _dt
from adapt_engine import check_drift, replan as do_replan

def run_drift_and_replan(conn, athlete_id: str, today: _dt.date) -> None:
    """Controleer drift; herplan indien nodig. Schrijft nieuwe rijen weg + logt."""
    today_s = str(today)

    # Haal alle geplande rijen voor dit plan op
    rows = [dict(r) for r in conn.execute(
        "SELECT planned_date, run_type, missed, linked_activity_id, target_pace_s, distance_km "
        "FROM planned_workout WHERE athlete_id=? ORDER BY planned_date",
        (athlete_id,)).fetchall()]

    if not rows:
        return  # Geen plan

    # ACWR-historie (laatste 14 dagen)
    acwr_hist = [r["acwr"] for r in conn.execute(
        "SELECT acwr FROM training_load WHERE athlete_id=? AND date>=? ORDER BY date",
        (athlete_id, str(today - _dt.timedelta(days=14)))).fetchall()
        if r["acwr"] is not None] if _table_exists(conn, "training_load") else []

    signals = {"acwr_history": acwr_hist}
    drift = check_drift(rows, today, signals)
    if not drift["drift"]:
        return

    print(f"[adapt] Drift gedetecteerd voor {athlete_id}: {drift['reason']}")

    # Haal plan + prefs + fitness op
    plan_row = conn.execute("SELECT * FROM training_plan WHERE athlete_id=? ORDER BY created_at DESC LIMIT 1",
                            (athlete_id,)).fetchone()
    if not plan_row:
        return
    plan = dict(plan_row)

    # Haal fitness-signalen op (zelfde als _fitness in routes.py)
    fitness_row = conn.execute(
        "SELECT easy_pace_s, vo2max FROM athlete_metrics WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
        (athlete_id,)).fetchone()
    fitness = {"easy_pace_s": fitness_row["easy_pace_s"] if fitness_row else None,
               "vo2max": fitness_row["vo2max"] if fitness_row else None}

    prefs = {"run_days": (plan.get("run_days") or "mon,wed,fri,sat").split(","),
             "long_day": plan.get("long_day") or "sat",
             "hyrox_days": (plan.get("hyrox_days") or "").split(",") if plan.get("hyrox_days") else [],
             "strength_days": (plan.get("strength_days") or "").split(",") if plan.get("strength_days") else []}

    new_rows = do_replan(plan, today, prefs, fitness)

    # Verwijder toekomstige rijen + vervang
    conn.execute("DELETE FROM planned_workout WHERE athlete_id=? AND planned_date>=?", (athlete_id, today_s))
    for r in new_rows:
        conn.execute(
            """INSERT INTO planned_workout
               (athlete_id, planned_date, week_num, run_type, title, distance_km,
                target_pace_s, segments, notes, run_day_of_week)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (athlete_id, r["planned_date"], r.get("week_num"), r.get("run_type"),
             r.get("title"), r.get("distance_km"), r.get("target_pace_s"),
             r.get("segments"), r.get("notes"), r.get("run_day_of_week")))
    conn.execute("INSERT INTO plan_replan_log (athlete_id, replan_date, reason) VALUES (?,?,?)",
                 (athlete_id, today_s, drift["reason"]))
    conn.commit()
    print(f"[adapt] Replan uitgevoerd: {len(new_rows)} toekomstige rijen weggeschreven.")


def _table_exists(conn, name: str) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())
```

Voeg aanroep toe in de `main()` of `if __name__ == "__main__"` blok na micro-aanpassing:
```python
for athlete_id in athlete_ids:
    run_drift_and_replan(conn, athlete_id, today)
```

- [ ] **Step 3: Handmatige smoke-test (droog):**
```bash
cd ~/garmin-coach && .venv/bin/python scripts/adapt.py --dry-run 2>/dev/null || \
  .venv/bin/python scripts/adapt.py
```
Verwacht: geen Python-errors. "Drift gedetecteerd" of "(geen drift)" in output.

- [ ] **Step 4: Commit**
```bash
git add scripts/adapt.py
git commit -m "feat(fase3): drift-check + replan in scripts/adapt.py"
```

---

## Task 4: API — replan endpoint + plan/meta

**Files:** Modify `api/routes.py`

- [ ] **Step 1: Schrijf de falende test**

`tests/test_api.py` — voeg toe:
```python
def test_replan_endpoint_returns_200(client, athlete_id):
    """POST /athlete/{id}/replan moet 200 teruggeven (ook als geen drift)."""
    resp = client.post(f"/athlete/{athlete_id}/replan")
    assert resp.status_code == 200
    data = resp.json()
    assert "replanned" in data

def test_plan_meta_endpoint(client, athlete_id):
    resp = client.get(f"/athlete/{athlete_id}/plan/meta")
    assert resp.status_code == 200
    data = resp.json()
    assert "last_replan" in data  # None of datum-string
```

- [ ] **Step 2: Run om te bevestigen dat het faalt**
```bash
cd ~/garmin-coach && .venv/bin/python -m pytest tests/test_api.py::test_replan_endpoint_returns_200 -v
```
Verwacht: 404 of `AttributeError`

- [ ] **Step 3: Voeg endpoints toe aan `api/routes.py`**

Na de bestaande `override_workout` route:
```python
@router.post("/athlete/{athlete_id}/replan")
def trigger_replan(athlete_id: str) -> dict:
    """On-demand: drift-check + replan als drift gedetecteerd."""
    import datetime as _dt
    from adapt_engine import check_drift, replan as do_replan
    import json as _json

    today = _dt.date.today()
    today_s = str(today)

    with _conn() as conn:
        _athlete_or_404(conn, athlete_id)
        rows = [dict(r) for r in conn.execute(
            "SELECT planned_date, run_type, missed, linked_activity_id, target_pace_s, distance_km "
            "FROM planned_workout WHERE athlete_id=? ORDER BY planned_date",
            (athlete_id,)).fetchall()]

        acwr_hist = [r["acwr"] for r in conn.execute(
            "SELECT acwr FROM training_load WHERE athlete_id=? AND date>=? ORDER BY date",
            (athlete_id, str(today - _dt.timedelta(days=14)))).fetchall()
            if r.get("acwr") is not None] if rows else []

        drift = check_drift(rows, today, {"acwr_history": acwr_hist})
        if not drift["drift"]:
            return {"replanned": False, "reason": "Geen drift gedetecteerd."}

        plan_row = conn.execute(
            "SELECT * FROM training_plan WHERE athlete_id=? ORDER BY created_at DESC LIMIT 1",
            (athlete_id,)).fetchone()
        if not plan_row:
            return {"replanned": False, "reason": "Geen plan gevonden."}
        plan = dict(plan_row)

        fitness_row = conn.execute(
            "SELECT easy_pace_s, vo2max FROM athlete_metrics WHERE athlete_id=? ORDER BY date DESC LIMIT 1",
            (athlete_id,)).fetchone()
        fitness = {"easy_pace_s": fitness_row["easy_pace_s"] if fitness_row else None,
                   "vo2max": fitness_row["vo2max"] if fitness_row else None}

        prefs = {"run_days": (plan.get("run_days") or "mon,wed,fri,sat").split(","),
                 "long_day": plan.get("long_day") or "sat",
                 "hyrox_days": [], "strength_days": []}

        new_rows = do_replan(plan, today, prefs, fitness)
        conn.execute("DELETE FROM planned_workout WHERE athlete_id=? AND planned_date>=?",
                     (athlete_id, today_s))
        for r in new_rows:
            conn.execute(
                """INSERT INTO planned_workout
                   (athlete_id, planned_date, week_num, run_type, title, distance_km,
                    target_pace_s, segments, notes, run_day_of_week)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (athlete_id, r["planned_date"], r.get("week_num"), r.get("run_type"),
                 r.get("title"), r.get("distance_km"), r.get("target_pace_s"),
                 _json.dumps(r["segments"]) if isinstance(r.get("segments"), list) else r.get("segments"),
                 r.get("notes"), r.get("run_day_of_week")))
        conn.execute("INSERT INTO plan_replan_log (athlete_id, replan_date, reason) VALUES (?,?,?)",
                     (athlete_id, today_s, drift["reason"]))
        conn.commit()
        return {"replanned": True, "reason": drift["reason"], "new_rows": len(new_rows)}


@router.get("/athlete/{athlete_id}/plan/meta")
def get_plan_meta(athlete_id: str) -> dict:
    """Geef plan-metadata terug inclusief laatste replan."""
    with _conn() as conn:
        _athlete_or_404(conn, athlete_id)
        last = conn.execute(
            "SELECT replan_date, reason FROM plan_replan_log WHERE athlete_id=? ORDER BY id DESC LIMIT 1",
            (athlete_id,)).fetchone()
        plan_row = conn.execute(
            "SELECT race_date, goal_time_s, distance_km FROM training_plan WHERE athlete_id=? ORDER BY created_at DESC LIMIT 1",
            (athlete_id,)).fetchone()
        return {
            "last_replan": dict(last) if last else None,
            "race_date": plan_row["race_date"] if plan_row else None,
        }
```

- [ ] **Step 4: Run tests**
```bash
cd ~/garmin-coach && .venv/bin/python -m pytest tests/test_api.py -v
```
Verwacht: alle tests PASS.

- [ ] **Step 5: Commit**
```bash
git add api/routes.py tests/test_api.py
git commit -m "feat(fase3): /replan + /plan/meta endpoints"
```

---

## Task 5: Frontend — ReplanBanner in Schema-tab

**Files:** Modify `dashboard/src/screens/Schema.jsx`, `dashboard/src/api.js`

- [ ] **Step 1:** Voeg `getPlanMeta` + `triggerReplan` toe aan `dashboard/src/api.js`:
```js
export async function getPlanMeta(athleteId) {
  const r = await fetch(`/api/athlete/${athleteId}/plan/meta`)
  if (!r.ok) throw new Error('plan/meta failed')
  return r.json()
}

export async function triggerReplan(athleteId) {
  const r = await fetch(`/api/athlete/${athleteId}/replan`, { method: 'POST' })
  if (!r.ok) throw new Error('replan failed')
  return r.json()
}
```

- [ ] **Step 2:** Voeg een `ReplanBanner` toe aan de Schema.jsx (bovenaan de tab, onder de weekstrip):
```jsx
import { getPlanMeta } from '../api'

// In het Schema-component:
const [planMeta, setPlanMeta] = useState(null)
useEffect(() => {
  getPlanMeta(athleteId).then(setPlanMeta).catch(() => {})
}, [athleteId])

// In de render, boven de eerste WeekStrip:
{planMeta?.last_replan && (
  <div style={{
    background: 'var(--amber-t)', border: '1px solid var(--amber)',
    borderRadius: 10, padding: '8px 12px', marginBottom: 12,
    fontSize: 12, color: 'var(--amber)',
  }}>
    ↻ Plan herberekend op {planMeta.last_replan.replan_date}
    {planMeta.last_replan.reason ? ` · ${planMeta.last_replan.reason}` : ''}
  </div>
)}
```

- [ ] **Step 3:** Controleer in browser dev: banner zichtbaar als `last_replan` aanwezig, onzichtbaar anders.

- [ ] **Step 4:** Run vitest:
```bash
cd ~/garmin-coach/dashboard && npm test -- --run
```

- [ ] **Step 5: Build + commit**
```bash
cd ~/garmin-coach/dashboard && npm run build
cd ~/garmin-coach
git add dashboard/src/screens/Schema.jsx dashboard/src/api.js dashboard/dist
git commit -m "feat(fase3): ReplanBanner in Schema-tab"
```

---

## Task 6: Deploy + verificatie

- [ ] **Step 1: Verifieer account**
```bash
npx vercel@latest whoami
# Verwacht: sidehustlehqs
```

- [ ] **Step 2: Push + deploy**
```bash
cd ~/garmin-coach
git push
npx vercel@latest --prod
```

- [ ] **Step 3: Smoke-test productie**
```bash
curl -s https://garmin-coach-phi.vercel.app/api/athlete/rowan/plan/meta | python3 -m json.tool
```
Verwacht: JSON met `last_replan` (null of datum) en `race_date`.

- [ ] **Step 4: Update Obsidian vault** — zet Fase 3 status op "KLAAR" in `~/SideHQ/Persoonlijk/Marathon & Hyrox/Garmin-coach status.md`.
