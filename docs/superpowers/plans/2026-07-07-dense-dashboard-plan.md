# Vol dashboard (health + training) — Implementatieplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Het "Vandaag"-scherm ombouwen tot een vol dashboard (hardloop-stats boven, gezondheid onder, geplande training bovenaan), gevoed door één geconsolideerd `/dashboard`-endpoint.

**Architecture:** Nieuw `GET /athlete/{id}/dashboard`-endpoint dat alle schermdata in één call assembleert uit bestaande tabellen (+ `metrics.pace_at_hr`), null-tolerant. Frontend: herbouwde `screens/Home.jsx` met nieuwe `StatTile`/`SectionHeader`-primitieven; hergebruik bestaande primitieven.

**Tech Stack:** FastAPI (dual SQLite/Postgres via `_conn`/`_exec`), React 19/Vite, Vitest, pytest. Repo `~/garmin-coach`. Deploy: `dashboard/dist` committen → `npx vercel@latest --prod` (whoami=sidehustlehqs).

**Voorwaarden:** Alle data wordt al opgeslagen (activities, daily_stats, daily_heart_rates, body_battery[+level], training_readiness, vo2max, training_load_balance, hrv, sleep, planned_workout). `metrics.pace_at_hr`, `coach_rules.duiding_*` bestaan.

---

## Bestandsstructuur

| Bestand | Verantwoordelijkheid | Actie |
|---|---|---|
| `api/routes.py` | `GET /dashboard` (geconsolideerd) | Modify |
| `dashboard/src/api.js` | `dashboard(id)` | Modify |
| `dashboard/src/ui/StatTile.jsx` | herbruikbare stat-tegel (waarde/unit/trend/sparkline) | Create |
| `dashboard/src/ui/SectionHeader.jsx` | sectietitel | Create |
| `dashboard/src/screens/Home.jsx` | volle dashboard-layout | Replace |
| `tests/test_api.py` | endpoint-test | Modify |
| `dashboard/src/ui/StatTile.test.jsx` | tile smoke | Create (optioneel via vitest) |

Tests: `.venv/bin/python -m pytest` (backend), `cd dashboard && npm test` (frontend).

---

## Task 1: `GET /athlete/{id}/dashboard` endpoint (TDD)

**Files:** Modify `api/routes.py`, `tests/test_api.py`.

- [ ] **Step 1: Falende test** — voeg toe aan `tests/test_api.py`:

```python
def test_dashboard_endpoint_shape():
    client = TestClient(app)
    r = client.get("/api/athlete/vriendin/dashboard")
    assert r.status_code == 200
    b = r.json()
    for key in ["today_workout", "readiness", "running", "last_run", "health"]:
        assert key in b
    assert set(["vo2max", "vo2max_trend", "weekly_volume", "acwr", "pace_at_hr"]).issubset(b["running"].keys())
    assert set(["hrv", "hrv_trend", "sleep", "body_battery", "resting_hr", "resting_hr_trend", "steps", "active_calories"]).issubset(b["health"].keys())
    assert isinstance(b["running"]["vo2max_trend"], list)


def test_dashboard_404_unknown():
    client = TestClient(app)
    assert client.get("/api/athlete/nobody/dashboard").status_code == 404
```

- [ ] **Step 2: Run — faalt**

Run: `.venv/bin/python -m pytest tests/test_api.py::test_dashboard_endpoint_shape -v` → FAIL (404).

- [ ] **Step 3: Implementeer** — zorg dat `import datetime as _dt`, `import metrics`, `import coach_rules` bovenaan `api/routes.py` staan (voeg toe wat mist). Voeg dit endpoint toe (na `get_home`):

```python
@router.get("/athlete/{athlete_id}/dashboard")
def get_dashboard(athlete_id: str) -> dict[str, Any]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        today = _dt.date.today().isoformat()

        def one(sql, params):
            return _exec(conn, sql, params).fetchone()
        def many(sql, params):
            return _exec(conn, sql, params).fetchall()

        tw = one("""SELECT title, run_type, day_type, week_num, target_pace_s
                    FROM planned_workout WHERE athlete_id=? AND date=?""", (athlete_id, today))
        today_workout = ({"title": tw["title"], "run_type": tw["run_type"], "day_type": tw["day_type"],
                          "week_num": tw["week_num"], "target_pace_s": tw["target_pace_s"]} if tw else None)

        rd = one("SELECT score, level FROM training_readiness WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,))
        hrv_l = one("SELECT last_night_avg FROM hrv WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,))
        sleep_l = one("SELECT duration_s, score FROM sleep WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,))
        bb = one("SELECT level_current FROM body_battery WHERE athlete_id=? AND level_current IS NOT NULL ORDER BY date DESC LIMIT 1", (athlete_id,))
        readiness_score = rd["score"] if rd else None

        vo2_rows = many("SELECT date, vo2max FROM vo2max WHERE athlete_id=? ORDER BY date", (athlete_id,))
        vo2_trend = [{"date": r["date"], "vo2max": r["vo2max"]} for r in vo2_rows]
        vo2_latest = vo2_trend[-1]["vo2max"] if vo2_trend else None

        load = one("SELECT acwr, acwr_status FROM training_load_balance WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,))

        runs = many("""SELECT date, distance_m, duration_s, avg_hr FROM activities
                       WHERE athlete_id=? AND type_key='running' AND distance_m>0 ORDER BY date""", (athlete_id,))
        pace_trend = metrics.pace_at_hr([dict(r) for r in runs])

        if db_module.use_postgres():
            week_expr = "to_char(date::date, 'IYYY-\"W\"IW')"
        else:
            week_expr = "strftime('%Y-W%W', date)"
        wv = many(f"""SELECT {week_expr} AS week, SUM(distance_m)/1000.0 AS km
                      FROM activities WHERE athlete_id=? AND type_key='running'
                      GROUP BY week ORDER BY week DESC LIMIT 6""", (athlete_id,))
        weekly_volume = [{"week": r["week"], "km": round(r["km"], 1)} for r in reversed(wv)]

        rest_rows = many("""SELECT date, resting_hr FROM daily_heart_rates
                            WHERE athlete_id=? AND resting_hr IS NOT NULL ORDER BY date""", (athlete_id,))
        rest_trend = [{"date": r["date"], "resting_hr": r["resting_hr"]} for r in rest_rows]
        hrv_rows = many("SELECT date, last_night_avg FROM hrv WHERE athlete_id=? AND last_night_avg IS NOT NULL ORDER BY date", (athlete_id,))
        hrv_trend = [{"date": r["date"], "hrv": r["last_night_avg"]} for r in hrv_rows]
        ds = one("SELECT steps, active_calories FROM daily_stats WHERE athlete_id=? ORDER BY date DESC LIMIT 1", (athlete_id,))

        last = one("""SELECT date, name, activity_id, distance_m, duration_s, avg_hr,
                             hr_zone_1_s, hr_zone_2_s, hr_zone_3_s, hr_zone_4_s, hr_zone_5_s
                      FROM activities WHERE athlete_id=? AND type_key='running' AND distance_m>0
                      ORDER BY date DESC LIMIT 1""", (athlete_id,))
        last_run = None
        if last:
            dist_km = (last["distance_m"] or 0) / 1000
            dur_s = last["duration_s"] or 0
            splits = many("""SELECT distance_m, duration_s FROM activity_splits
                             WHERE athlete_id=? AND activity_id=? ORDER BY split_num""", (athlete_id, last["activity_id"]))
            sp = [round(s["duration_s"] / (s["distance_m"] / 1000), 1) for s in splits if (s["distance_m"] or 0) > 0 and (s["duration_s"] or 0) > 0]
            last_run = {
                "date": last["date"], "activity_id": last["activity_id"], "name": last["name"],
                "distance_km": round(dist_km, 2),
                "avg_pace_s_per_km": round(dur_s / dist_km, 1) if dist_km > 0 else None,
                "avg_hr": last["avg_hr"],
                "zones": {"z1": last["hr_zone_1_s"], "z2": last["hr_zone_2_s"], "z3": last["hr_zone_3_s"],
                          "z4": last["hr_zone_4_s"], "z5": last["hr_zone_5_s"]},
                "duiding": coach_rules.duiding_run({"splits_pace": sp, "avg_hr": last["avg_hr"]}),
            }

        return {
            "today_workout": today_workout,
            "readiness": {
                "score": readiness_score, "level": rd["level"] if rd else None,
                "hrv": hrv_l["last_night_avg"] if hrv_l else None,
                "sleep_s": sleep_l["duration_s"] if sleep_l else None,
                "body_battery": bb["level_current"] if bb else None,
                "duiding": coach_rules.duiding_readiness({"score": readiness_score}),
            },
            "running": {
                "vo2max": vo2_latest, "vo2max_trend": vo2_trend,
                "weekly_volume": weekly_volume,
                "acwr": load["acwr"] if load else None,
                "acwr_status": load["acwr_status"] if load else None,
                "pace_at_hr": pace_trend[-1]["pace_s_per_km"] if pace_trend else None,
                "pace_at_hr_trend": pace_trend,
            },
            "last_run": last_run,
            "health": {
                "hrv": hrv_l["last_night_avg"] if hrv_l else None, "hrv_trend": hrv_trend,
                "sleep": {"duration_s": sleep_l["duration_s"] if sleep_l else None,
                          "score": sleep_l["score"] if sleep_l else None},
                "body_battery": bb["level_current"] if bb else None,
                "resting_hr": rest_trend[-1]["resting_hr"] if rest_trend else None,
                "resting_hr_trend": rest_trend,
                "steps": ds["steps"] if ds else None,
                "active_calories": ds["active_calories"] if ds else None,
            },
        }
    finally:
        if db_module.use_postgres():
            conn.close()
```

- [ ] **Step 4: Run — slaagt**

Run: `.venv/bin/python -m pytest tests/test_api.py::test_dashboard_endpoint_shape tests/test_api.py::test_dashboard_404_unknown -v` → PASS. Dan volledige suite groen.

- [ ] **Step 5: Commit**

```bash
git add api/routes.py tests/test_api.py
git commit -m "feat(api): consolidated /dashboard endpoint (training + health)"
```

---

## Task 2: API-client + StatTile + SectionHeader

**Files:** Modify `dashboard/src/api.js`; Create `dashboard/src/ui/StatTile.jsx`, `dashboard/src/ui/SectionHeader.jsx`.

- [ ] **Step 1: api.js** — voeg toe in het `api`-object: `dashboard: (id) => get(`/athlete/${id}/dashboard`),`

- [ ] **Step 2: SectionHeader.jsx**
```jsx
export default function SectionHeader({ children }) {
  return <p style={{ fontSize: 11, color: 'var(--faint)', textTransform: 'uppercase',
    letterSpacing: '.08em', fontWeight: 600, margin: '16px 2px 8px' }}>{children}</p>
}
```

- [ ] **Step 3: StatTile.jsx** (props: label, value, unit, trendVals?, trendColor?, trendDir?, onClick?, children?)
```jsx
import Sparkline from './Sparkline'

export default function StatTile({ label, value, unit, trendVals, trendColor = 'var(--z2)', trendDir, onClick, children }) {
  return (
    <div onClick={onClick} style={{ background: 'var(--card)', border: '1px solid var(--line)',
      borderRadius: 13, padding: 11, cursor: onClick ? 'pointer' : 'default' }}>
      <p style={{ fontSize: 10.5, color: 'var(--faint)', textTransform: 'uppercase', letterSpacing: '.04em', margin: 0 }}>{label}</p>
      <p className="tnum" style={{ fontSize: 19, fontWeight: 500, margin: '3px 0 0' }}>
        {value ?? '–'}{unit ? <span style={{ fontSize: 10.5, color: 'var(--faint)', fontWeight: 500 }}> {unit}</span> : null}
        {trendDir ? <span style={{ fontSize: 11, color: trendDir === 'up' ? 'var(--good)' : 'var(--hard)' }}> {trendDir === 'up' ? '↑' : '↓'}</span> : null}
      </p>
      {trendVals && trendVals.filter(v => v != null).length >= 2 ? <Sparkline vals={trendVals} color={trendColor} height={22} /> : null}
      {children}
    </div>
  )
}
```

- [ ] **Step 4: Verifieer build** — `cd ~/garmin-coach/dashboard && npx vite build` slaagt.

- [ ] **Step 5: Commit**
```bash
cd ~/garmin-coach
git add dashboard/src/api.js dashboard/src/ui/StatTile.jsx dashboard/src/ui/SectionHeader.jsx
git commit -m "feat(ui): dashboard api + StatTile/SectionHeader primitives"
```

---

## Task 3: Home-scherm herbouwen (vol dashboard)

**Files:** Replace `dashboard/src/screens/Home.jsx`.

- [ ] **Step 1: Vervang `dashboard/src/screens/Home.jsx`** volledig:
```jsx
import { useState, useEffect } from 'react'
import { api } from '../api'
import Card from '../ui/Card'
import ReadinessHero from '../ui/ReadinessHero'
import StatTile from '../ui/StatTile'
import SectionHeader from '../ui/SectionHeader'
import VolumeBars from '../ui/VolumeBars'
import ZoneBar from '../ui/ZoneBar'
import CoachNote from '../ui/CoachNote'
import { paceStr, kmStr, sleepStr } from '../format'

export default function Home({ athleteId, onOpenRun, onNav }) {
  const [d, setD] = useState(null)
  const [err, setErr] = useState(false)

  useEffect(() => {
    setD(null); setErr(false)
    api.dashboard(athleteId).then(setD).catch(() => setErr(true))
  }, [athleteId])

  if (err) return <p style={{ color: 'var(--hard)' }}>Kon data niet laden.</p>
  if (!d) return <p style={{ color: 'var(--faint)' }}>Laden…</p>

  const r = d.running || {}
  const h = d.health || {}
  const tw = d.today_workout
  const lr = d.last_run

  return (
    <div>
      {/* Training vandaag */}
      <Card onClick={() => onNav && onNav('schema')} style={{ borderColor: '#3a2418' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 10.5, color: 'var(--accent)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em' }}>
            Training vandaag{tw && tw.week_num ? ` · week ${tw.week_num}` : ''}
          </span>
        </div>
        {tw ? (
          <>
            <p style={{ fontSize: 17, fontWeight: 600, margin: 0 }}>{tw.title}</p>
            {tw.target_pace_s ? <p style={{ fontSize: 12, color: 'var(--muted)', margin: '4px 0 0' }}>doel {paceStr(tw.target_pace_s)} /km</p> : null}
          </>
        ) : <p style={{ fontSize: 14, color: 'var(--muted)', margin: 0 }}>Geen training gepland vandaag.</p>}
      </Card>

      <ReadinessHero readiness={d.readiness} />

      <SectionHeader>Hardlopen</SectionHeader>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <StatTile label="VO₂max" value={r.vo2max} trendVals={(r.vo2max_trend || []).map(x => x.vo2max)} trendColor="var(--good)" onClick={() => onNav && onNav('fitness')} />
        <StatTile label="Weekvolume" value={r.weekly_volume && r.weekly_volume.length ? Math.round(r.weekly_volume[r.weekly_volume.length - 1].km) : null} unit="km" onClick={() => onNav && onNav('load')}>
          <VolumeBars vals={(r.weekly_volume || []).map(w => w.km)} height={22} />
        </StatTile>
        <StatTile label="Belasting (ACWR)" value={r.acwr} onClick={() => onNav && onNav('load')} />
        <StatTile label="Tempo @150bpm" value={paceStr(r.pace_at_hr)} unit="/km" trendVals={(r.pace_at_hr_trend || []).map(x => x.pace_s_per_km)} trendColor="var(--good)" onClick={() => onNav && onNav('fitness')} />
      </div>

      {lr && (
        <Card onClick={() => onOpenRun && onOpenRun(lr.activity_id)} style={{ marginTop: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Laatste run</span>
            <span style={{ fontSize: 11, color: 'var(--faint)' }}>{lr.date} · {kmStr(lr.distance_km)} km</span>
          </div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 10 }}>
            <span className="tnum" style={{ fontSize: 17, fontWeight: 600 }}>{paceStr(lr.avg_pace_s_per_km)} <span style={{ fontSize: 10.5, color: 'var(--faint)' }}>/km</span></span>
            <span className="tnum" style={{ fontSize: 17, fontWeight: 600 }}>{lr.avg_hr ?? '–'} <span style={{ fontSize: 10.5, color: 'var(--faint)' }}>bpm</span></span>
          </div>
          <ZoneBar zones={lr.zones} />
          {lr.duiding ? <div style={{ marginTop: 10 }}><CoachNote>{lr.duiding}</CoachNote></div> : null}
        </Card>
      )}

      <SectionHeader>Gezondheid</SectionHeader>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
        <StatTile label="HRV" value={h.hrv} trendVals={(h.hrv_trend || []).map(x => x.hrv)} trendColor="var(--z2)" />
        <StatTile label="Slaap" value={sleepStr(h.sleep && h.sleep.duration_s)}>
          {h.sleep && h.sleep.score != null ? <p style={{ fontSize: 10.5, color: 'var(--faint)', margin: '2px 0 0' }}>score {h.sleep.score}</p> : null}
        </StatTile>
        <StatTile label="Body" value={h.body_battery} />
        <StatTile label="Rust-HR" value={h.resting_hr} unit="bpm" trendVals={(h.resting_hr_trend || []).map(x => x.resting_hr)} trendColor="var(--z1)" />
        <StatTile label="Stappen" value={h.steps != null ? h.steps.toLocaleString('nl-NL') : null} />
        <StatTile label="Actieve kcal" value={h.active_calories != null ? Math.round(h.active_calories) : null} />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verifieer build** — `cd ~/garmin-coach/dashboard && npx vite build` slaagt.

- [ ] **Step 3: Commit**
```bash
cd ~/garmin-coach
git add dashboard/src/screens/Home.jsx
git commit -m "feat(ui): dense Vandaag dashboard — training + health sections"
```

---

## Task 4: Build, deploy, live-verificatie

**Files:** `dashboard/dist/**`.

- [ ] **Step 1: Build + commit dist + push**
```bash
cd ~/garmin-coach/dashboard && npm run build
cd ~/garmin-coach && git add dashboard/dist && git commit -m "build: dense dashboard bundle" && git push
```

- [ ] **Step 2: Deploy**
```bash
npx vercel@latest whoami   # MOET sidehustlehqs zijn
npx vercel@latest --prod --yes
```

- [ ] **Step 3: Live-verificatie**
```bash
curl -s "https://garmin-coach-phi.vercel.app/api/athlete/rowan/dashboard" | .venv/bin/python -c "import sys,json;d=json.load(sys.stdin);print('secties:',list(d.keys()));print('health hrv/sleep/rustHR/steps:',d['health']['hrv'],d['health']['sleep'],d['health']['resting_hr'],d['health']['steps']);print('today_workout:',bool(d['today_workout']))"
```
Expected: alle secties aanwezig; gezondheids-velden gevuld (Rowan heeft HRV/slaap/rust-HR/stappen); today_workout aanwezig (plan is live). Open daarna https://garmin-coach-phi.vercel.app (Vandaag-tab) en bevestig het volle dashboard rendert (Training vandaag, readiness, Hardlopen-tegels, laatste run, Gezondheid-tegels). Geen console-errors.

- [ ] **Step 4: Klaar** — meld resultaat.

---

## Zelf-review (uitgevoerd)

- **Spec-dekking:** geconsolideerd `/dashboard`-endpoint met today_workout/readiness/running/last_run/health ✓ (T1); null-tolerant (alle velden via `... if x else None`) ✓; `StatTile`/`SectionHeader` ✓ (T2); Home-herbouw met secties Hardlopen (boven) + Gezondheid (onder) + Training-vandaag bovenaan ✓ (T3); tegels aantikbaar → fitness/load-detail ✓; lege/laad/fout-staten ✓; build+deploy+verificatie ✓ (T4). "–"-fallback voor ontbrekende running-stats zit in `StatTile` (`value ?? '–'`).
- **Placeholders:** geen; echte code/commando's overal.
- **Type-consistentie:** `api.dashboard` payload-velden matchen wat `Home.jsx` leest (`running.vo2max/vo2max_trend/weekly_volume/acwr/pace_at_hr(_trend)`, `health.hrv/hrv_trend/sleep{duration_s,score}/body_battery/resting_hr/resting_hr_trend/steps/active_calories`, `today_workout{title,target_pace_s,week_num}`, `last_run{...zones,duiding}`); `StatTile` props (`label/value/unit/trendVals/trendColor/trendDir/onClick/children`) matchen gebruik in Home; week-SQL (`%W`/IW) hergebruikt bestaand patroon uit `/weekly_volume`.

## Openstaande verfijningen (later)
- Detailschermen voor gezondheidstegels; fallback-tekst i.p.v. "–" voor Rowan's VO₂max/ACWR.
- Daarna Werkstroom B (Fase 3): schema adaptief op readiness/load.
