# Fase 3 · Plan 1 — Dagelijkse micro-aanpassing

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Het plan past de eerstvolgende training(en) automatisch aan op je signalen (readiness/ACWR/slaap, gemiste runs), transparant en overrulebaar — met harde vangrails.

**Architecture:** Nieuwe pure module `adapt_engine.py` (regels: workout → aanpassing). Overlay-kolommen op `planned_workout` (origineel blijft basis). Adaptatie draait in de dagelijkse sync (`scripts/adapt.py`) + on-demand endpoint. API geeft de **effectieve** workout terug. Frontend toont "aangepast · reden" + revert.

**Tech Stack:** Python 3.9 (`from __future__ import annotations`), FastAPI dual SQLite/Postgres, React/Vite, pytest/vitest. Repo `~/garmin-coach`.

**Scope:** Alleen dagelijkse micro-aanpassing + gemiste-run-absorptie. Vooruit herplannen = Plan 2. Geen LLM.

---

## Bestandsstructuur

| Bestand | Verantwoordelijkheid | Actie |
|---|---|---|
| `db.py` | overlay-kolommen + migratie | Modify |
| `scripts/migrate_to_supabase.py` | (planned_workout al in TABLES) | geen |
| `adapt_engine.py` | `adjust_day`, `absorb_missed` (pure) | Create |
| `coach_rules.py` | `duiding_adjustment(reason_key)` | Modify |
| `api/routes.py` | effectieve workout + `/adapt` + `/override` | Modify |
| `scripts/adapt.py` | adaptatie draaien tegen DB (sync + CLI) | Create |
| `scripts/sync_local.sh` | adapt-stap na push | Modify |
| `dashboard/src/ui/WorkoutCard.jsx` | aangepast-badge + revert | Modify |
| `dashboard/src/ui/WeekStrip.jsx` | gemist-merk | Modify |
| `dashboard/src/api.js` | `overrideWorkout` | Modify |
| tests: `test_adapt_engine.py` (new), `test_api.py`, `test_coach_rules.py` | | Create/Modify |

Tests: `.venv/bin/python -m pytest` · `cd dashboard && npm test`.

---

## Task 1: DB overlay-kolommen + migratie

**Files:** Modify `db.py`.

- [ ] **Step 1:** In `SCHEMA_SQLITE` en `SCHEMA_PG`, voeg aan de `planned_workout`-kolommen toe (na `linked_activity_id INTEGER`):
```sql
    adjusted_run_type TEXT, adjusted_title TEXT, adjusted_segments TEXT,
    adjusted_target_pace_s INTEGER, adjustment_reason TEXT,
    is_adjusted INTEGER DEFAULT 0, user_override INTEGER DEFAULT 0, missed INTEGER DEFAULT 0,
```

- [ ] **Step 2:** Voeg een SQLite-kolom-migratie toe (mirror `_migrate_body_battery`). Definieer:
```python
PLANNED_WORKOUT_NEW_COLUMNS = [
    ("adjusted_run_type", "TEXT"), ("adjusted_title", "TEXT"), ("adjusted_segments", "TEXT"),
    ("adjusted_target_pace_s", "INTEGER"), ("adjustment_reason", "TEXT"),
    ("is_adjusted", "INTEGER DEFAULT 0"), ("user_override", "INTEGER DEFAULT 0"), ("missed", "INTEGER DEFAULT 0"),
]

def _migrate_planned_workout(path: Path) -> None:
    with get_conn(path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(planned_workout)").fetchall()}
        for col, ctype in PLANNED_WORKOUT_NEW_COLUMNS:
            if col not in cols:
                conn.execute(f"ALTER TABLE planned_workout ADD COLUMN {col} {ctype}")
        conn.commit()
```
Roep 'm aan in `_init_sqlite` na `_migrate_body_battery(path)`: `_migrate_planned_workout(path)`.
(Postgres: de kolommen staan in `SCHEMA_PG`; `_init_pg` doet `CREATE TABLE IF NOT EXISTS`. Bestaande Supabase-tabel: voeg in `_init_pg` ná de create-loop een idempotente ALTER-lus toe voor `planned_workout` — `ALTER TABLE planned_workout ADD COLUMN IF NOT EXISTS <col> <type>` voor elk van PLANNED_WORKOUT_NEW_COLUMNS.)

Voeg daarvoor in `_init_pg` toe (na de bestaande statements-loop, binnen de `with conn.cursor()`):
```python
        for col, ctype in PLANNED_WORKOUT_NEW_COLUMNS:
            cur.execute(f"ALTER TABLE planned_workout ADD COLUMN IF NOT EXISTS {col} {ctype}")
```

- [ ] **Step 3: Verifieer** `.venv/bin/python -c "import db; db.init_db(db.Path('/tmp/a.db')); db.init_db(db.Path('/tmp/a.db')); print('ok')"; rm -f /tmp/a.db` → `ok`.

- [ ] **Step 4: Commit** `git add db.py && git commit -m "feat(db): planned_workout adjustment overlay columns"`

---

## Task 2: `adapt_engine.adjust_day` (TDD)

**Files:** Create `adapt_engine.py`, `tests/test_adapt_engine.py`.

- [ ] **Step 1: Falende tests** — `tests/test_adapt_engine.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from adapt_engine import adjust_day

PACES = {"mp": 341, "easy": 376, "long": 361, "tempo": 316, "interval": 286}

def _wo(run_type, target=None, km=None):
    return {"run_type": run_type, "title": "x", "target_pace_s": target, "distance_km": km,
            "segments": [{"label": "werk", "target_pace_s": target}] if target else None}

def test_low_readiness_downgrades_quality_to_easy():
    adj = adjust_day(_wo("quality", 316), {"readiness": 34, "acwr": 1.0}, PACES)
    assert adj and adj["adjusted_run_type"] == "easy"
    assert adj["adjusted_target_pace_s"] == PACES["easy"]
    assert "readiness" in adj["adjustment_reason"].lower() or "rustig" in adj["adjustment_reason"].lower()

def test_high_acwr_downgrades_long_to_easy():
    adj = adjust_day(_wo("long", 361, 20), {"readiness": 70, "acwr": 1.6}, PACES)
    assert adj and adj["adjusted_run_type"] == "easy"

def test_low_readiness_easy_becomes_rest():
    adj = adjust_day(_wo("easy", 376, 6), {"readiness": 30, "acwr": 1.0}, PACES)
    assert adj and adj["adjusted_run_type"] == "rest"

def test_mid_readiness_softens_quality_to_mp():
    adj = adjust_day(_wo("quality", 316), {"readiness": 48, "acwr": 1.0}, PACES)
    assert adj and adj["adjusted_run_type"] == "quality"
    assert adj["adjusted_target_pace_s"] == PACES["mp"]

def test_fresh_and_ahead_sharpens_quality():
    adj = adjust_day(_wo("quality", 316), {"readiness": 82, "acwr": 0.9, "recent_quality_hit": True, "downgrade_last_48h": False}, PACES)
    assert adj and adj["adjusted_target_pace_s"] == 306  # 10s sneller

def test_fresh_but_recent_downgrade_no_upgrade():
    adj = adjust_day(_wo("quality", 316), {"readiness": 82, "acwr": 0.9, "recent_quality_hit": True, "downgrade_last_48h": True}, PACES)
    assert adj is None

def test_good_signals_no_change():
    assert adjust_day(_wo("easy", 376, 6), {"readiness": 68, "acwr": 1.0}, PACES) is None

def test_rest_day_never_adjusted():
    assert adjust_day({"run_type": None, "title": "Rust"}, {"readiness": 20, "acwr": 2.0}, PACES) is None
```

- [ ] **Step 2: Run — faalt** (`ModuleNotFoundError`).

- [ ] **Step 3: Implementeer** `adapt_engine.py`:
```python
"""Regelgebaseerde dagelijkse plan-aanpassing. Pure functies, geen I/O.
Stabiele interface — Fase 4 kan de regels vervangen door een LLM."""
from __future__ import annotations


def _easy(paces, km=6):
    return {"adjusted_run_type": "easy", "adjusted_title": f"Rustige duurloop {km} km",
            "adjusted_target_pace_s": paces["easy"],
            "adjusted_segments": [{"label": f"Rustige duurloop {km} km",
                                   "distance_m": km * 1000, "target_pace_s": paces["easy"]}]}


def adjust_day(workout: dict, signals: dict, paces: dict) -> dict | None:
    """Geef een aanpassing voor deze geplande workout, of None (origineel behouden).
    workout: run_type/title/target_pace_s/distance_km/segments. signals: readiness/acwr/
    sleep_score/sleep_s/recent_quality_hit/downgrade_last_48h. paces: compute_paces-dict."""
    rt = workout.get("run_type")
    if rt not in ("easy", "quality", "long"):
        return None  # rust/kracht/hyrox/race: niet aanpassen

    readiness = signals.get("readiness")
    acwr = signals.get("acwr")
    sleep_score = signals.get("sleep_score")
    sleep_s = signals.get("sleep_s")

    bad = (readiness is not None and readiness < 40) or (acwr is not None and acwr > 1.5)
    mid = (readiness is not None and 40 <= readiness < 55) or \
          (sleep_score is not None and sleep_score < 50) or \
          (sleep_s is not None and sleep_s < 5 * 3600)

    if bad:
        if rt in ("quality", "long"):
            adj = _easy(paces)
            adj["adjustment_reason"] = f"Lage readiness/hoge belasting → vandaag rustig i.p.v. {rt}."
            return adj
        return {"adjusted_run_type": "rest", "adjusted_title": "Rust", "adjusted_segments": None,
                "adjusted_target_pace_s": None,
                "adjustment_reason": "Je herstel is laag — vandaag rust."}

    if mid:
        if rt == "quality":
            return {"adjusted_run_type": "quality", "adjusted_title": workout.get("title") or "Kwaliteit (zachter)",
                    "adjusted_target_pace_s": paces["mp"],
                    "adjusted_segments": [{"label": "werk op marathonpace", "target_pace_s": paces["mp"]}],
                    "adjustment_reason": "Matig herstel → kwaliteit één stap zachter (marathonpace)."}
        if rt == "long":
            km = round((workout.get("distance_km") or 16) * 0.85)
            adj = _easy(paces, km); adj["adjusted_run_type"] = "long"
            adj["adjusted_title"] = f"Lange duurloop {km} km (ingekort)"
            adj["adjusted_target_pace_s"] = paces["long"]
            adj["adjusted_segments"] = [{"label": adj["adjusted_title"], "distance_m": km * 1000, "target_pace_s": paces["long"]}]
            adj["adjustment_reason"] = "Matig herstel → lange duurloop iets ingekort."
            return adj
        return None  # easy blijft easy

    # fris + vóór → kleine opwaardering (alleen quality, geen recente downgrade)
    if rt == "quality" and readiness is not None and readiness >= 75 \
            and signals.get("recent_quality_hit") and not signals.get("downgrade_last_48h"):
        base = workout.get("target_pace_s") or paces["tempo"]
        return {"adjusted_run_type": "quality", "adjusted_title": (workout.get("title") or "Kwaliteit") + " (aangescherpt)",
                "adjusted_target_pace_s": base - 10,
                "adjusted_segments": [{"label": "werk (scherper)", "target_pace_s": base - 10}],
                "adjustment_reason": "Je bent fris en ligt voor — 10 s/km scherper."}
    return None
```

- [ ] **Step 4: Run — slaagt** (`.venv/bin/python -m pytest tests/test_adapt_engine.py -v` → 8 PASS). Volledige suite groen.

- [ ] **Step 5: Commit** `git add adapt_engine.py tests/test_adapt_engine.py && git commit -m "feat(adapt): rule-based daily workout adjustment"`

---

## Task 3: `adapt_engine.absorb_missed` (TDD)

**Files:** Modify `adapt_engine.py`, `tests/test_adapt_engine.py`.

- [ ] **Step 1: Falende test**:
```python
from adapt_engine import absorb_missed

def test_absorb_missed_marks_and_reschedules():
    rows = [
        {"date": "2026-07-13", "run_type": "quality", "done": False, "day_type": "run"},
        {"date": "2026-07-16", "run_type": "easy", "done": True, "day_type": "run"},
        {"date": "2026-07-18", "run_type": "long", "done": False, "day_type": "run"},
    ]
    out = absorb_missed(rows, today="2026-07-17")
    by = {r["date"]: r for r in out}
    assert by["2026-07-13"]["missed"] is True   # verleden, niet gedaan
    assert by["2026-07-16"]["missed"] is False   # gedaan
    assert by["2026-07-18"]["missed"] is False   # toekomst

def test_absorb_missed_empty():
    assert absorb_missed([], today="2026-07-17") == []
```

- [ ] **Step 2: Run — faalt.**

- [ ] **Step 3: Implementeer** (toevoegen aan `adapt_engine.py`):
```python
def absorb_missed(rows: list[dict], today: str) -> list[dict]:
    """Markeer verleden run-dagen zonder afgeronde activity als missed.
    (Herplanning/verschuiven van gemiste sessies gebeurt in Plan 2 — hier alleen markeren.)"""
    out = []
    for r in rows:
        r = dict(r)
        r["missed"] = bool(r.get("day_type") == "run" and r["date"] < today and not r.get("done"))
        out.append(r)
    return out
```

- [ ] **Step 4: Run — slaagt.** Suite groen.

- [ ] **Step 5: Commit** `git add adapt_engine.py tests/test_adapt_engine.py && git commit -m "feat(adapt): mark missed past run days"`

---

## Task 4: `coach_rules` reden-helper (klein) + effectieve workout in API

**Files:** Modify `api/routes.py`, `tests/test_api.py`.

De aanpassing levert al `adjustment_reason`; geen aparte coach-functie nodig. Deze taak: **effectieve workout** teruggeven + `/adapt` + `/override`.

- [ ] **Step 1: Falende test** (toevoegen aan `tests/test_api.py`):
```python
def test_adapt_and_override_flow():
    client = TestClient(app)
    body = {"race_name": "M", "race_date": "2026-10-18", "race_distance_km": 42.195,
            "goal_time_s": 14400, "start_date": "2026-07-13", "weeks": 14,
            "run_days": ["mon", "thu", "sat"], "fixed_days": {"tue": "strength", "wed": "hyrox", "fri": "strength"}}
    client.post("/api/athlete/vriendin/plan", json=body)
    # forceer lage readiness zodat adapt afschaalt
    conn = get_conn(TEST_DB)
    conn.execute("INSERT OR REPLACE INTO training_readiness (athlete_id,date,score,level) VALUES ('vriendin','2026-07-13',30,'LOW')")
    conn.commit()
    r = client.post("/api/athlete/vriendin/adapt")
    assert r.status_code == 200
    wk = client.get("/api/athlete/vriendin/plan/week?week=1").json()
    q = next((d for d in wk if d.get("is_adjusted")), None)
    assert q is not None and q["run_type"] == "easy"        # effectieve = aangepast
    # override → origineel terug
    client.post(f"/api/athlete/vriendin/workout/{q['date']}/override")
    wk2 = client.get("/api/athlete/vriendin/plan/week?week=1").json()
    d2 = next(d for d in wk2 if d["date"] == q["date"])
    assert d2["run_type"] == "quality" and d2.get("user_override") is True
```

- [ ] **Step 2: Run — faalt.**

- [ ] **Step 3: Implementeer** in `api/routes.py`:
Voeg `import adapt_engine` toe. Voeg een `_effective`-helper toe die `_wo_dict` vervangt/uitbreidt zodat de effectieve velden teruggegeven worden:
```python
def _wo_dict(r) -> dict:
    override = bool(r["user_override"])
    use_adj = bool(r["is_adjusted"]) and not override
    run_type = r["adjusted_run_type"] if use_adj and r["adjusted_run_type"] is not None else r["run_type"]
    title = r["adjusted_title"] if use_adj and r["adjusted_title"] else r["title"]
    target = r["adjusted_target_pace_s"] if use_adj and r["adjusted_target_pace_s"] is not None else r["target_pace_s"]
    seg_src = r["adjusted_segments"] if use_adj and r["adjusted_segments"] else r["segments"]
    return {"date": r["date"], "week_num": r["week_num"], "phase": r["phase"],
            "day_type": r["day_type"], "run_type": run_type, "title": title,
            "distance_km": r["distance_km"], "target_pace_s": target,
            "coach_note": r["coach_note"], "status": r["status"],
            "segments": json.loads(seg_src) if seg_src else None,
            "is_adjusted": use_adj, "adjustment_reason": r["adjustment_reason"] if use_adj else None,
            "user_override": override, "missed": bool(r["missed"])}
```
(Let op: `planned_workout SELECT *` moet de nieuwe kolommen bevatten — `SELECT *` doet dat automatisch. Waar `get_plan_week`/`get_workout` nu `_wo_dict(r)` gebruiken blijft ongewijzigd.)

Voeg endpoints toe:
```python
@router.post("/athlete/{athlete_id}/adapt")
def adapt_plan(athlete_id: str) -> dict[str, Any]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        today = _dt.date.today().isoformat()
        plan = _exec(conn, "SELECT goal_time_s, race_distance_km FROM training_plan WHERE athlete_id=? ORDER BY id DESC LIMIT 1", (athlete_id,)).fetchone()
        if not plan:
            return {"ok": True, "adjusted": 0}
        paces = plan_engine.compute_paces(plan["goal_time_s"], plan["race_distance_km"], _fitness(conn, athlete_id).get("current_easy_s"))
        rd = _exec(conn, "SELECT score FROM training_readiness WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,)).fetchone()
        load = _exec(conn, "SELECT acwr FROM training_load_balance WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,)).fetchone()
        sl = _exec(conn, "SELECT duration_s, score FROM sleep WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,)).fetchone()
        signals = {"readiness": rd["score"] if rd else None, "acwr": load["acwr"] if load else None,
                   "sleep_s": sl["duration_s"] if sl else None, "sleep_score": sl["score"] if sl else None,
                   "recent_quality_hit": False, "downgrade_last_48h": False}
        # pas toekomstige/vandaag, niet-override run-dagen aan
        rows = _exec(conn, "SELECT date, run_type, title, target_pace_s, distance_km, segments FROM planned_workout WHERE athlete_id=? AND date>=? AND user_override=0", (athlete_id, today)).fetchall()
        n = 0
        for r in rows:
            wo = {"run_type": r["run_type"], "title": r["title"], "target_pace_s": r["target_pace_s"],
                  "distance_km": r["distance_km"], "segments": json.loads(r["segments"]) if r["segments"] else None}
            adj = adapt_engine.adjust_day(wo, signals, paces)
            if adj:
                _exec(conn, """UPDATE planned_workout SET is_adjusted=1, adjusted_run_type=?, adjusted_title=?,
                       adjusted_target_pace_s=?, adjusted_segments=?, adjustment_reason=? WHERE athlete_id=? AND date=?""",
                      (adj["adjusted_run_type"], adj["adjusted_title"], adj.get("adjusted_target_pace_s"),
                       json.dumps(adj["adjusted_segments"]) if adj.get("adjusted_segments") else None,
                       adj["adjustment_reason"], athlete_id, r["date"]))
                n += 1
            else:
                _exec(conn, "UPDATE planned_workout SET is_adjusted=0 WHERE athlete_id=? AND date=?", (athlete_id, r["date"]))
        # markeer gemiste verleden runs
        _exec(conn, """UPDATE planned_workout SET missed=1 WHERE athlete_id=? AND date<? AND day_type='run' AND linked_activity_id IS NULL""", (athlete_id, today))
        conn.commit()
        return {"ok": True, "adjusted": n}
    finally:
        if db_module.use_postgres():
            conn.close()


@router.post("/athlete/{athlete_id}/workout/{wdate}/override")
def override_workout(athlete_id: str, wdate: str) -> dict[str, Any]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        _exec(conn, "UPDATE planned_workout SET user_override=1 WHERE athlete_id=? AND date=?", (athlete_id, wdate))
        conn.commit()
        return {"ok": True}
    finally:
        if db_module.use_postgres():
            conn.close()
```

- [ ] **Step 4: Run — slaagt.** Volledige suite groen.

- [ ] **Step 5: Commit** `git add api/routes.py tests/test_api.py && git commit -m "feat(api): /adapt applies daily adjustments; /override; effective workout in responses"`

---

## Task 5: Sync-integratie (`scripts/adapt.py` + sync_local.sh)

**Files:** Create `scripts/adapt.py`; Modify `scripts/sync_local.sh`.

- [ ] **Step 1: `scripts/adapt.py`** — draait `adjust_day` + missed-markering tegen de DB voor beide atleten (zelfde logica als het `/adapt`-endpoint, maar standalone met `db.get_conn`). Volg het patroon van `scripts/create_plans.py` (`db_module.init_db()`, per atleet ophalen fitheid/signalen, `adapt_engine.adjust_day`, UPDATE). Gebruik dezelfde SQL als in het `/adapt`-endpoint (Step 3 Task 4). Print per atleet het aantal aangepaste dagen.

- [ ] **Step 2:** In `scripts/sync_local.sh`, ná de "PUSH → Supabase"-stap, voeg toe:
```bash
if [[ -n "${DATABASE_URL:-}" ]]; then
  log "ADAPT (dagelijkse bijsturing)..."
  "$PY" scripts/adapt.py >>"$LOG" 2>&1 && log "OK adapt" || log "FOUT adapt (zie log)"
fi
```

- [ ] **Step 3: Verifieer lokaal** `DATABASE_URL= .venv/bin/python scripts/adapt.py` draait zonder fouten (print aangepaste-tellingen; kan 0 zijn als signalen goed).

- [ ] **Step 4: Commit** `git add scripts/adapt.py scripts/sync_local.sh && git commit -m "feat(adapt): run daily adjustment in sync + standalone script"`

---

## Task 6: Frontend — aangepast-badge + revert + gemist-merk

**Files:** Modify `dashboard/src/ui/WorkoutCard.jsx`, `dashboard/src/ui/WeekStrip.jsx`, `dashboard/src/api.js`, `dashboard/src/screens/Schema.jsx`.

- [ ] **Step 1: api.js** — voeg toe: `overrideWorkout: (id, date) => post(`/athlete/${id}/workout/${date}/override`),`

- [ ] **Step 2: WorkoutCard.jsx** — toon aanpassing + revert. Voeg direct onder de titel-`<p>` toe (component krijgt extra prop `onRevert`):
```jsx
      {w.is_adjusted ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8,
          background: 'var(--bg)', borderRadius: 9, padding: '7px 10px', margin: '0 0 10px' }}>
          <span style={{ fontSize: 11.5, color: 'var(--amber, #E8A33D)' }}>aangepast · {w.adjustment_reason}</span>
          {onRevert ? <button onClick={() => onRevert(w.date)} style={{ background: 'none', border: 'none', color: 'var(--accent)', fontSize: 11.5, fontWeight: 600, whiteSpace: 'nowrap' }}>← origineel</button> : null}
        </div>
      ) : null}
```
Werk de functie-signatuur bij: `export default function WorkoutCard({ workout, onRevert }) {`.

- [ ] **Step 3: WeekStrip.jsx** — grijs "gemist"-merk: in de dag-`button`, als `d.missed` toon een klein puntje/opacity. Voeg in de map, na de icoon-`<span>`:
```jsx
            {d.missed ? <span style={{ display: 'block', fontSize: 8, color: 'var(--faint)' }}>gemist</span> : null}
```

- [ ] **Step 4: Schema.jsx** — geef `onRevert` door aan `WorkoutCard`, en herlaad de week na override:
```jsx
  function revert(date) {
    api.overrideWorkout(athleteId, date).then(() => setWeek(w => w))  // triggert de week-effect opnieuw
      .then(() => api.planWeek(athleteId, week).then(setDays))
  }
```
En in de render: `<WorkoutCard workout={selectedWorkout} onRevert={revert} />`. (Als de week-effect al op `week` hangt, volstaat een expliciete `api.planWeek(...).then(setDays)` na override.)

- [ ] **Step 5: Verifieer build** `cd ~/garmin-coach/dashboard && npx vite build` slaagt.

- [ ] **Step 6: Commit** `git add dashboard/src && git commit -m "feat(ui): show adjusted workout + reason + revert; missed marker"`

---

## Task 7: Build, deploy, live-verificatie

- [ ] **Step 1:** `cd ~/garmin-coach/dashboard && npm run build` → `cd ~/garmin-coach && git add dashboard/dist && git commit -m "build: adaptive daily-adjust bundle" && git push`
- [ ] **Step 2:** `npx vercel@latest whoami` (=sidehustlehqs) → `npx vercel@latest --prod --yes`
- [ ] **Step 3:** Trigger adaptatie live + check:
```bash
curl -s -X POST https://garmin-coach-phi.vercel.app/api/athlete/rowan/adapt
curl -s "https://garmin-coach-phi.vercel.app/api/athlete/rowan/plan/week?week=$(python3 -c 'import datetime;print(max(1,(datetime.date.today()-datetime.date(2026,7,13)).days//7+1))')" | .venv/bin/python -c "import sys,json;ds=json.load(sys.stdin);print([(d['date'][5:],d['run_type'],d.get('is_adjusted')) for d in ds])"
```
Expected: `/adapt` geeft `{"ok":true,...}`; de week toont eventueel `is_adjusted=true` dagen (afhankelijk van Rowan's readiness). Open het dashboard/Schema en controleer het "aangepast · reden"-label + "← origineel" werkt. Geen console-errors.
- [ ] **Step 4:** Meld resultaat.

---

## Zelf-review (uitgevoerd)
- **Spec-dekking:** overlay-kolommen + migratie ✓ (T1); `adjust_day` met alle drempels + vangrail (geen upgrade na recente downgrade) ✓ (T2); missed-markering ✓ (T3); effectieve workout + `/adapt` + `/override` ✓ (T4); sync-integratie ✓ (T5); frontend badge/revert/missed ✓ (T6); deploy+verificatie ✓ (T7). Vangrail "geen 2 harde dagen achtereen / niet ná hyrox" zit al in `assemble_week` (Fase 2) en `adjust_day` verzwaart nooit een niet-quality dag. Verschuiven van gemiste sessies (echte herplanning) = bewust Plan 2.
- **Placeholders:** geen; echte code/commando's. (T5 `adapt.py` verwijst naar dezelfde SQL als T4 — die staat volledig in T4.)
- **Type-consistentie:** `adjust_day(workout, signals, paces)`-keys matchen T4-aanroep + de UPDATE-kolommen; `_wo_dict` effectieve velden (`is_adjusted/adjustment_reason/user_override/missed`) matchen de frontend (WorkoutCard/WeekStrip); `overrideWorkout` matcht `/override`.

## Volgende plan
Plan 2: `adapt_engine.replan` + drift-detectie (gemiste runs / ACWR-trend / fitheid-afwijking) → resterende weken herperiodiseren, met volume-cap + taper intact.
