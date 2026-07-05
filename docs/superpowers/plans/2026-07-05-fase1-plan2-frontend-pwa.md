# Fase 1 · Plan 2 — Frontend-herbouw (5 schermen) + PWA

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Het oude panel-dashboard vervangen door een Runna-achtige, mobiel-eerste, gelaagde app met 5 schermen op de nieuwe backend-endpoints, plus PWA-installeerbaarheid, en live zetten op Vercel.

**Architecture:** Vite + React 19 (bestaand). Eén klein API-client-bestand, een set gedeelde UI-primitieven, schermgedreven navigatie via React-state (geen router-lib), en een PWA-laag (manifest + service worker). Backend krijgt één extra endpoint (`/fitness`) om `metrics.pace_at_hr` te ontsluiten.

**Tech Stack:** React 19, Vite, plain CSS met design-tokens (licht+donker), Vitest voor pure helpers, preview-tools voor scherm-verificatie. Deploy: lokaal builden → `dashboard/dist` committen → `npx vercel@latest --prod` (whoami = `sidehustlehqs`).

**Voorwaarden:** Plan 1 is gemerged in `main` (endpoints incl. `/athlete/{id}/home` bestaan; `metrics.py`, `coach_rules.py` aanwezig).

**Design-tokens (uit spec):** grond slate `#EEF1F4` / kaart `#FFFFFF` / inkt `#151B22`; accent safety-orange `#FF5A1F` (tekst-op-tint `#C6410E`, tint `#FFEDE4`); semantisch goed `#1F9E6F`, let-op `#E8A33D`, hard `#E0483F`; HR-zones `#5B8DEF #2FB79A #7CC24B #E8A33D #E0483F`. Mobiel-eerst, tabular-nums voor cijfers.

---

## Bestandsstructuur (dashboard/)

| Bestand | Verantwoordelijkheid | Actie |
|---|---|---|
| `src/api.js` | HTTP-client naar backend | Modify: `home`, `runDetail`, `fitness`, `load` toevoegen |
| `src/format.js` | Pure formatters (pace, duur, datum) | Create + Vitest-tests |
| `src/theme.css` | Design-tokens + basis | Replace: licht+donker, slate + safety-orange |
| `src/ui/Card.jsx` `MetricStat.jsx` `ZoneBar.jsx` `SplitsBar.jsx` `Sparkline.jsx` `CoachNote.jsx` `CountdownChip.jsx` `ReadinessHero.jsx` `VolumeBars.jsx` `TabBar.jsx` `AthleteSwitcher.jsx` | Herbruikbare UI-primitieven | Create |
| `src/screens/Home.jsx` `RunDetail.jsx` `FitnessDetail.jsx` `LoadDetail.jsx` `RunsList.jsx` `Schema.jsx` `Delen.jsx` | Schermen | Create |
| `src/App.jsx` | App-shell: state (scherm/atleet/runId), header, navigatie | Replace |
| `api/routes.py` | Backend | Modify: `/athlete/{id}/fitness` endpoint |
| `dashboard/public/manifest.webmanifest`, icons, `src/sw.js` | PWA | Create |
| `dashboard/index.html`, `src/main.jsx` | PWA-registratie + manifest-link | Modify |
| `dashboard/package.json`, `vite.config.js` | Vitest-dep + config | Modify |

Oude `src/components/*` en de oude `App.jsx`-panellogica worden verwijderd nadat de schermen werken (Task 14).

---

## Task 1: Backend — `/athlete/{id}/fitness` endpoint (ontsluit pace@HR)

**Files:** Modify `api/routes.py`; Test `tests/test_api.py`. (Repo-root, pytest `.venv/bin/python -m pytest`.)

- [ ] **Step 1: Falende test** — voeg toe aan `tests/test_api.py`:

```python
def test_fitness_endpoint_shape():
    client = TestClient(app)
    r = client.get("/api/athlete/vriendin/fitness")
    assert r.status_code == 200
    body = r.json()
    assert set(["vo2max_trend", "resting_hr_trend", "pace_at_hr", "duiding"]).issubset(body.keys())
    assert isinstance(body["pace_at_hr"], list)
```

- [ ] **Step 2: Run — verwacht falen**

Run: `.venv/bin/python -m pytest tests/test_api.py::test_fitness_endpoint_shape -v` → FAIL (404).

- [ ] **Step 3: Implementeer** — voeg bovenaan `api/routes.py` toe: `import metrics`. Voeg endpoint toe (na `get_home`):

```python
@router.get("/athlete/{athlete_id}/fitness")
def get_fitness(athlete_id: str) -> dict[str, Any]:
    conn = _conn()
    try:
        _athlete_or_404(conn, athlete_id)
        vo2 = _exec(conn, "SELECT date, vo2max FROM vo2max WHERE athlete_id=? ORDER BY date", (athlete_id,)).fetchall()
        rest = _exec(conn,
            """SELECT date, resting_hr FROM daily_heart_rates
               WHERE athlete_id=? AND resting_hr IS NOT NULL ORDER BY date""",
            (athlete_id,)).fetchall()
        runs = _exec(conn,
            """SELECT date, distance_m, duration_s, avg_hr FROM activities
               WHERE athlete_id=? AND type_key='running' AND distance_m > 0 ORDER BY date""",
            (athlete_id,)).fetchall()
        pace_trend = metrics.pace_at_hr([dict(r) for r in runs])
        vo2_vals = [r["vo2max"] for r in vo2 if r["vo2max"] is not None]
        trend_up = len(vo2_vals) >= 2 and vo2_vals[-1] > vo2_vals[0]
        duiding = ("Je VO₂max stijgt — je aerobe motor wordt sterker."
                   if trend_up else "Nog te weinig data voor een fitheidstrend."
                   if len(vo2_vals) < 2 else "Je fitheid is stabiel.")
        return {
            "vo2max_trend": [{"date": r["date"], "vo2max": r["vo2max"]} for r in vo2],
            "resting_hr_trend": [{"date": r["date"], "resting_hr": r["resting_hr"]} for r in rest],
            "pace_at_hr": pace_trend,
            "duiding": duiding,
        }
    finally:
        if db_module.use_postgres():
            conn.close()
```

- [ ] **Step 4: Run — verwacht slagen**

Run: `.venv/bin/python -m pytest tests/test_api.py::test_fitness_endpoint_shape -v` → PASS. Dan volledige suite → groen.

- [ ] **Step 5: Commit**

```bash
git add api/routes.py tests/test_api.py
git commit -m "feat(api): /fitness endpoint exposing pace-at-hr trend"
```

---

## Task 2: Vitest-setup + `format.js` formatters (TDD)

**Files:** Modify `dashboard/package.json`, `dashboard/vite.config.js`; Create `dashboard/src/format.js`, `dashboard/src/format.test.js`. Werk vanuit `dashboard/`.

- [ ] **Step 1: Installeer vitest**

Run: `cd ~/Documents/garmin-coach/dashboard && npm i -D vitest`
Voeg aan `package.json` `scripts` toe: `"test": "vitest run"`.

- [ ] **Step 2: Falende test** — Create `dashboard/src/format.test.js`:

```javascript
import { describe, it, expect } from 'vitest'
import { paceStr, durationStr, kmStr, sleepStr } from './format'

describe('format', () => {
  it('paceStr formats s/km as m:ss', () => {
    expect(paceStr(312)).toBe('5:12')
    expect(paceStr(300)).toBe('5:00')
    expect(paceStr(null)).toBe('–')
  })
  it('durationStr formats seconds as h:mm:ss or m:ss', () => {
    expect(durationStr(2558)).toBe('42:38')
    expect(durationStr(4700)).toBe('1:18:20')
    expect(durationStr(null)).toBe('–')
  })
  it('kmStr uses comma decimal', () => {
    expect(kmStr(8.2)).toBe('8,2')
    expect(kmStr(null)).toBe('–')
  })
  it('sleepStr formats seconds as h:mm', () => {
    expect(sleepStr(27720)).toBe('7:42')
    expect(sleepStr(null)).toBe('–')
  })
})
```

- [ ] **Step 3: Run — verwacht falen**

Run: `npm test` → FAIL (kan `./format` niet resolven).

- [ ] **Step 4: Implementeer** — Create `dashboard/src/format.js`:

```javascript
export function paceStr(sPerKm) {
  if (sPerKm == null) return '–'
  const m = Math.floor(sPerKm / 60)
  const s = Math.round(sPerKm % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

export function durationStr(sec) {
  if (sec == null) return '–'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = Math.round(sec % 60)
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

export function kmStr(km) {
  if (km == null) return '–'
  return km.toFixed(1).replace('.', ',')
}

export function sleepStr(sec) {
  if (sec == null) return '–'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  return `${h}:${String(m).padStart(2, '0')}`
}
```

- [ ] **Step 5: Run — verwacht slagen**

Run: `npm test` → 4 PASS.

- [ ] **Step 6: Commit**

```bash
cd ~/Documents/garmin-coach
git add dashboard/package.json dashboard/package-lock.json dashboard/vite.config.js dashboard/src/format.js dashboard/src/format.test.js
git commit -m "feat(ui): format helpers + vitest setup"
```

---

## Task 3: API-client uitbreiden

**Files:** Modify `dashboard/src/api.js`.

- [ ] **Step 1: Voeg endpoints toe** — voeg in het `api`-object toe (behoud bestaande regels):

```javascript
  home:            (id) => get(`/athlete/${id}/home`),
  fitness:         (id) => get(`/athlete/${id}/fitness`),
```

(De bestaande `runs`, `splits`, `trainingLoad`, `weeklyVolume`, `runEfficiency`, `vo2maxTrend` blijven en worden hergebruikt door de detailschermen.)

- [ ] **Step 2: Verifieer build niet breekt**

Run: `cd ~/Documents/garmin-coach/dashboard && npx vite build` → slaagt (geen import-fouten). (Waarschuwing over chunkgrootte is OK.)

- [ ] **Step 3: Commit**

```bash
cd ~/Documents/garmin-coach
git add dashboard/src/api.js
git commit -m "feat(ui): api client home + fitness"
```

---

## Task 4: Theme-tokens (`theme.css`)

**Files:** Replace `dashboard/src/theme.css`.

- [ ] **Step 1: Vervang `theme.css`** met tokens (licht + donker via `prefers-color-scheme`), mobiel-eerst reset:

```css
:root {
  --bg: #EEF1F4; --card: #FFFFFF; --ink: #151B22; --muted: #5B6673; --faint: #8A94A0;
  --line: #E4E8EC; --accent: #FF5A1F; --accent-d: #C6410E; --accent-t: #FFEDE4;
  --good: #1F9E6F; --good-t: #E4F4EE; --caution: #E8A33D; --hard: #E0483F;
  --z1: #5B8DEF; --z2: #2FB79A; --z3: #7CC24B; --z4: #E8A33D; --z5: #E0483F;
  --radius: 12px; --radius-lg: 18px;
  --font: -apple-system, BlinkMacSystemFont, system-ui, "Segoe UI", Roboto, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0F1319; --card: #171C24; --ink: #EEF1F4; --muted: #9AA4B0; --faint: #6B7480;
    --line: #262D38; --accent: #FF6A33; --accent-d: #FFB599; --accent-t: #2A1A12;
    --good: #35C08C; --good-t: #16281F;
  }
}
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--bg); color: var(--ink); font-family: var(--font);
  -webkit-font-smoothing: antialiased; }
#root { max-width: 480px; margin: 0 auto; min-height: 100vh; }
h1, h2, h3, p { margin: 0; }
button { font-family: inherit; cursor: pointer; }
.tnum { font-variant-numeric: tabular-nums; }
```

- [ ] **Step 2: Verifieer build**

Run: `cd ~/Documents/garmin-coach/dashboard && npx vite build` → slaagt.

- [ ] **Step 3: Commit**

```bash
cd ~/Documents/garmin-coach
git add dashboard/src/theme.css
git commit -m "feat(ui): slate + safety-orange theme tokens, light and dark"
```

---

## Task 5: UI-primitieven

**Files:** Create in `dashboard/src/ui/`: `Card.jsx`, `MetricStat.jsx`, `ZoneBar.jsx`, `SplitsBar.jsx`, `Sparkline.jsx`, `CoachNote.jsx`, `CountdownChip.jsx`, `ReadinessHero.jsx`, `VolumeBars.jsx`, `TabBar.jsx`, `AthleteSwitcher.jsx`.

- [ ] **Step 1: Maak de primitieven** (elk één bestand, inline styles op tokens):

`Card.jsx`:
```jsx
export default function Card({ children, onClick, style }) {
  return (
    <div onClick={onClick}
      style={{ background: 'var(--card)', border: '1px solid var(--line)',
        borderRadius: 'var(--radius-lg)', padding: 16, marginBottom: 12,
        cursor: onClick ? 'pointer' : 'default', ...style }}>
      {children}
    </div>
  )
}
```

`MetricStat.jsx`:
```jsx
export default function MetricStat({ label, value, unit }) {
  return (
    <div style={{ background: 'var(--bg)', borderRadius: 'var(--radius)', padding: 10, flex: 1 }}>
      <p style={{ fontSize: 11, color: 'var(--faint)', textTransform: 'uppercase', letterSpacing: '.05em' }}>{label}</p>
      <p className="tnum" style={{ fontSize: 16, fontWeight: 500, marginTop: 3 }}>
        {value}{unit ? <span style={{ fontSize: 11, color: 'var(--faint)' }}> {unit}</span> : null}
      </p>
    </div>
  )
}
```

`ZoneBar.jsx` (zones = {z1..z5} seconden):
```jsx
const C = ['var(--z1)', 'var(--z2)', 'var(--z3)', 'var(--z4)', 'var(--z5)']
export default function ZoneBar({ zones, height = 8 }) {
  const vals = [zones?.z1, zones?.z2, zones?.z3, zones?.z4, zones?.z5].map(v => v || 0)
  const total = vals.reduce((a, b) => a + b, 0) || 1
  return (
    <div style={{ display: 'flex', height, borderRadius: 5, overflow: 'hidden' }}>
      {vals.map((v, i) => <div key={i} style={{ width: `${(v / total) * 100}%`, background: C[i] }} />)}
    </div>
  )
}
```

`SplitsBar.jsx` (splits = [{split_num, pace_s_per_km}]):
```jsx
import { paceStr } from '../format'
export default function SplitsBar({ splits }) {
  const paces = splits.map(s => s.pace_s_per_km).filter(Boolean)
  const max = Math.max(...paces, 1)
  return (
    <div>
      {splits.map((s, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <span className="tnum" style={{ width: 16, fontSize: 11, color: 'var(--faint)' }}>{s.split_num ?? i + 1}</span>
          <div style={{ flex: 1, background: 'var(--bg)', borderRadius: 5, overflow: 'hidden', height: 14 }}>
            <div style={{ width: `${((s.pace_s_per_km || 0) / max) * 100}%`, height: '100%', background: 'var(--accent)' }} />
          </div>
          <span className="tnum" style={{ width: 40, textAlign: 'right', fontSize: 11.5, color: 'var(--muted)' }}>{paceStr(s.pace_s_per_km)}</span>
        </div>
      ))}
    </div>
  )
}
```

`Sparkline.jsx` (vals = number[]):
```jsx
export default function Sparkline({ vals, color = 'var(--good)', height = 30 }) {
  const clean = (vals || []).filter(v => v != null)
  if (clean.length < 2) return null
  const w = 110, min = Math.min(...clean), max = Math.max(...clean), r = (max - min) || 1
  const pts = clean.map((v, i) => `${(i / (clean.length - 1) * w).toFixed(1)},${(height - 2 - (v - min) / r * (height - 6)).toFixed(1)}`).join(' ')
  const lx = w, ly = (height - 2 - (clean[clean.length - 1] - min) / r * (height - 6))
  return (
    <svg viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" style={{ width: '100%', height, display: 'block', marginTop: 6 }} aria-hidden="true">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={lx} cy={ly.toFixed(1)} r="2.6" fill={color} />
    </svg>
  )
}
```

`CoachNote.jsx`:
```jsx
export default function CoachNote({ children, dark }) {
  return (
    <div style={{ background: dark ? 'var(--ink)' : 'var(--accent-t)', borderRadius: 'var(--radius)', padding: 12 }}>
      <p style={{ fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.07em',
        color: dark ? 'var(--accent)' : 'var(--accent-d)', marginBottom: 4 }}>Coach</p>
      <p style={{ fontSize: 12.5, lineHeight: 1.5, color: dark ? 'rgba(238,241,244,.86)' : 'var(--accent-d)' }}>{children}</p>
    </div>
  )
}
```

`CountdownChip.jsx`:
```jsx
export default function CountdownChip({ weeks, label }) {
  if (weeks == null) return null
  return (
    <div style={{ textAlign: 'center', background: 'var(--ink)', color: 'var(--bg)', borderRadius: 14, padding: '7px 11px' }}>
      <p className="tnum" style={{ fontSize: 18, fontWeight: 500, lineHeight: 1 }}>{weeks}</p>
      <p style={{ fontSize: 9.5, marginTop: 3, opacity: .7, textTransform: 'uppercase', letterSpacing: '.08em' }}>{label}</p>
    </div>
  )
}
```

`ReadinessHero.jsx` (readiness payload from /home):
```jsx
import Card from './Card'
import MetricStat from './MetricStat'
import CoachNote from './CoachNote'
import { sleepStr } from '../format'
export default function ReadinessHero({ readiness }) {
  const r = readiness || {}
  const tone = r.score == null ? 'faint' : r.score >= 75 ? 'good' : r.score >= 50 ? 'caution' : 'hard'
  const toneColor = { good: 'var(--good)', caution: 'var(--caution)', hard: 'var(--hard)', faint: 'var(--faint)' }[tone]
  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 13, color: 'var(--muted)' }}>Klaar om te trainen?</span>
        {r.level ? <span style={{ fontSize: 11, fontWeight: 500, background: 'var(--good-t)', color: toneColor, padding: '3px 9px', borderRadius: 20 }}>{r.level}</span> : null}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 14 }}>
        <span className="tnum" style={{ fontSize: 40, fontWeight: 500, lineHeight: 1 }}>{r.score ?? '–'}</span>
        <span style={{ fontSize: 15, color: 'var(--faint)' }}>/ 100</span>
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <MetricStat label="HRV" value={r.hrv ?? '–'} />
        <MetricStat label="Slaap" value={sleepStr(r.sleep_s)} />
        <MetricStat label="Body" value={r.body_battery ?? '–'} />
      </div>
      {r.duiding ? <CoachNote>{r.duiding}</CoachNote> : null}
    </Card>
  )
}
```

`VolumeBars.jsx` (vals = number[], laatste geaccentueerd):
```jsx
export default function VolumeBars({ vals, height = 30 }) {
  const max = Math.max(...(vals || [1]), 1)
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height, marginTop: 6 }}>
      {(vals || []).map((v, i) => (
        <div key={i} style={{ flex: 1, height: `${Math.round((v / max) * 100)}%`,
          background: i === vals.length - 1 ? 'var(--accent)' : 'var(--line)', borderRadius: 3 }} />
      ))}
    </div>
  )
}
```

`TabBar.jsx`:
```jsx
const TABS = [['home', 'Vandaag'], ['runs', 'Runs'], ['schema', 'Schema'], ['delen', 'Delen']]
export default function TabBar({ current, onNav }) {
  const active = ['run', 'fitness', 'load'].includes(current) ? 'home' : current
  return (
    <div style={{ position: 'sticky', bottom: 0, display: 'flex', justifyContent: 'space-around',
      background: 'var(--card)', borderTop: '1px solid var(--line)', padding: '10px 6px 14px' }}>
      {TABS.map(([id, label]) => (
        <button key={id} onClick={() => onNav(id)} aria-label={label}
          style={{ background: 'none', border: 'none', color: active === id ? 'var(--accent)' : 'var(--faint)',
            fontSize: 11, fontWeight: 600 }}>{label}</button>
      ))}
    </div>
  )
}
```

`AthleteSwitcher.jsx`:
```jsx
export default function AthleteSwitcher({ athletes, current, onSwitch }) {
  return (
    <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
      {athletes.map(a => (
        <button key={a.id} onClick={() => onSwitch(a.id)}
          style={{ border: '1px solid var(--line)', borderRadius: 20, padding: '5px 13px', fontSize: 12.5, fontWeight: 500,
            background: current === a.id ? 'var(--ink)' : 'var(--card)',
            color: current === a.id ? 'var(--bg)' : 'var(--muted)' }}>
          {a.display_name}
        </button>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Verifieer build** — `cd ~/Documents/garmin-coach/dashboard && npx vite build` → slaagt (primitieven zijn nog niet gebruikt; build mag ongebruikte modules hebben).

- [ ] **Step 3: Commit**

```bash
cd ~/Documents/garmin-coach
git add dashboard/src/ui
git commit -m "feat(ui): shared primitives (card, metric, zonebar, splits, sparkline, coachnote, hero, tabbar, athlete switcher)"
```

---

## Task 6: App-shell + navigatie

**Files:** Replace `dashboard/src/App.jsx`. Create `dashboard/src/screens/Schema.jsx` en `Delen.jsx` (placeholders).

- [ ] **Step 1: Placeholder-schermen** — `screens/Schema.jsx`:
```jsx
export default function Schema() {
  return (
    <div style={{ textAlign: 'center', color: 'var(--faint)', padding: '60px 20px' }}>
      <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--ink)' }}>Jouw marathon-schema</p>
      <p style={{ fontSize: 13, marginTop: 8 }}>In Fase 2 stippelt de app hier het volledige pad naar je marathon uit en past het na elke run aan.</p>
      <p style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 600, marginTop: 16, textTransform: 'uppercase', letterSpacing: '.06em' }}>binnenkort</p>
    </div>
  )
}
```
`screens/Delen.jsx`:
```jsx
export default function Delen({ athlete }) {
  return (
    <div style={{ padding: '8px 0' }}>
      <div style={{ background: 'var(--ink)', color: 'var(--bg)', borderRadius: 'var(--radius-lg)', padding: 18 }}>
        <h3 style={{ fontSize: 17, fontWeight: 600, marginBottom: 4 }}>Deel je reis</h3>
        <p style={{ fontSize: 12.5, opacity: .75, lineHeight: 1.5 }}>Een schone, publieke weergave van je fitheid en runs — om aan anderen te laten zien waar je staat. Deel simpelweg de URL van deze pagina.</p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Vervang `App.jsx`** met schermgedreven shell:

```jsx
import { useState, useEffect } from 'react'
import './theme.css'
import { api } from './api'
import TabBar from './ui/TabBar'
import AthleteSwitcher from './ui/AthleteSwitcher'
import CountdownChip from './ui/CountdownChip'
import Home from './screens/Home'
import RunDetail from './screens/RunDetail'
import FitnessDetail from './screens/FitnessDetail'
import LoadDetail from './screens/LoadDetail'
import RunsList from './screens/RunsList'
import Schema from './screens/Schema'
import Delen from './screens/Delen'

export default function App() {
  const [athletes, setAthletes] = useState([])
  const [athleteId, setAthleteId] = useState(null)
  const [screen, setScreen] = useState('home')
  const [runId, setRunId] = useState(null)

  useEffect(() => {
    api.athletes().then(list => {
      setAthletes(list)
      if (list.length) setAthleteId(list.find(a => a.id === 'rowan')?.id || list[0].id)
    }).catch(() => setAthletes([]))
  }, [])

  function nav(s) { setScreen(s); setRunId(null) }
  function openRun(id) { setRunId(id); setScreen('run') }

  if (!athleteId) return <div style={{ padding: 24, color: 'var(--faint)' }}>Laden…</div>
  const athlete = athletes.find(a => a.id === athleteId) || {}

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <div style={{ padding: '18px 16px 12px', borderBottom: '1px solid var(--line)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 style={{ fontSize: 18, fontWeight: 600 }}>Hoi, {athlete.display_name}</h1>
            <p style={{ fontSize: 12, color: 'var(--faint)', marginTop: 2 }}>marathon-coach</p>
          </div>
          <CountdownChip weeks={null} label="wk tot race" />
        </div>
        <AthleteSwitcher athletes={athletes} current={athleteId} onSwitch={setAthleteId} />
      </div>

      <div style={{ flex: 1, padding: 16 }}>
        {screen === 'home' && <Home athleteId={athleteId} onOpenRun={openRun} onNav={nav} />}
        {screen === 'run' && <RunDetail athleteId={athleteId} runId={runId} onBack={() => nav('home')} />}
        {screen === 'fitness' && <FitnessDetail athleteId={athleteId} onBack={() => nav('home')} />}
        {screen === 'load' && <LoadDetail athleteId={athleteId} onBack={() => nav('home')} />}
        {screen === 'runs' && <RunsList athleteId={athleteId} onOpenRun={openRun} />}
        {screen === 'schema' && <Schema />}
        {screen === 'delen' && <Delen athlete={athlete} />}
      </div>

      <TabBar current={screen} onNav={nav} />
    </div>
  )
}
```

- [ ] **Step 3: Verifieer build faalt op ontbrekende schermen** — `npx vite build` faalt nu (Home/RunDetail etc. bestaan nog niet). Dat is verwacht; ze komen in Task 7–11. (Committen na Task 11 wanneer build weer slaagt, óf commit shell + placeholders nu en accepteer dat build pas groen is na de schermen. Kies: commit nu shell+placeholders, bouw schermen daarna.)

- [ ] **Step 4: Commit shell + placeholders**

```bash
cd ~/Documents/garmin-coach
git add dashboard/src/App.jsx dashboard/src/screens/Schema.jsx dashboard/src/screens/Delen.jsx
git commit -m "feat(ui): app shell with screen nav, athlete switcher, schema/delen placeholders"
```

---

## Task 7: Home-scherm

**Files:** Create `dashboard/src/screens/Home.jsx`.

- [ ] **Step 1: Implementeer** — consumeert `api.home` + `api.weeklyVolume` + `api.vo2maxTrend`:

```jsx
import { useState, useEffect } from 'react'
import { api } from '../api'
import Card from '../ui/Card'
import ReadinessHero from '../ui/ReadinessHero'
import Sparkline from '../ui/Sparkline'
import VolumeBars from '../ui/VolumeBars'
import ZoneBar from '../ui/ZoneBar'
import CoachNote from '../ui/CoachNote'
import { paceStr, kmStr } from '../format'

export default function Home({ athleteId, onOpenRun, onNav }) {
  const [home, setHome] = useState(null)
  const [vol, setVol] = useState([])
  const [vo2, setVo2] = useState([])
  const [err, setErr] = useState(false)

  useEffect(() => {
    setHome(null); setErr(false)
    Promise.all([api.home(athleteId), api.weeklyVolume(athleteId), api.vo2maxTrend(athleteId)])
      .then(([h, v, t]) => { setHome(h); setVol(v.slice().reverse().map(w => w.km)); setVo2(t.map(x => x.vo2max)) })
      .catch(() => setErr(true))
  }, [athleteId])

  if (err) return <p style={{ color: 'var(--hard)' }}>Kon data niet laden.</p>
  if (!home) return <p style={{ color: 'var(--faint)' }}>Laden…</p>

  const { readiness, fitness, load, last_run } = home
  return (
    <div>
      <ReadinessHero readiness={readiness} />
      <div style={{ display: 'flex', gap: 12 }}>
        <Card onClick={() => onNav('fitness')} style={{ flex: 1 }}>
          <p style={{ fontSize: 12, color: 'var(--muted)' }}>Waar sta ik</p>
          <p className="tnum" style={{ fontSize: 24, fontWeight: 500 }}>{fitness?.vo2max ?? '–'} <span style={{ fontSize: 11, color: 'var(--faint)' }}>VO₂max</span></p>
          <Sparkline vals={vo2} />
        </Card>
        <Card onClick={() => onNav('load')} style={{ flex: 1 }}>
          <p style={{ fontSize: 12, color: 'var(--muted)' }}>Belasting</p>
          <p className="tnum" style={{ fontSize: 24, fontWeight: 500 }}>{load?.acwr ?? '–'}</p>
          <VolumeBars vals={vol} />
        </Card>
      </div>
      {last_run && (
        <Card onClick={() => onOpenRun(last_run.activity_id)}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Laatste run</span>
            <span style={{ fontSize: 11, color: 'var(--faint)' }}>{last_run.date}</span>
          </div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 10 }}>
            <span className="tnum" style={{ fontSize: 18, fontWeight: 500 }}>{kmStr(last_run.distance_km)} km</span>
            <span className="tnum" style={{ fontSize: 18, fontWeight: 500 }}>{paceStr(last_run.avg_pace_s_per_km)} /km</span>
            <span className="tnum" style={{ fontSize: 18, fontWeight: 500 }}>{last_run.avg_hr ?? '–'} bpm</span>
          </div>
          <div style={{ marginBottom: 8 }}><ZoneBar zones={last_run.zones} /></div>
          {last_run.duiding ? <CoachNote>{last_run.duiding}</CoachNote> : null}
        </Card>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verifieer via preview** — start de dev-servers en controleer Home rendert met echte data:

Run: `cd ~/Documents/garmin-coach && ./start.sh` (start API :8000 + Vite :5173). Gebruik daarna de preview-tools: open `http://localhost:5173`, `preview_snapshot` → bevestig readiness-getal, VO₂max, belasting, laatste-run zichtbaar. `preview_console_logs level:error` → geen errors. Stop `start.sh` na de check.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/screens/Home.jsx
git commit -m "feat(ui): home coach-brief screen"
```

---

## Task 8: Run-detail-scherm

**Files:** Create `dashboard/src/screens/RunDetail.jsx`.

- [ ] **Step 1: Implementeer** — combineert `api.runs` (voor kernstats van deze run), `api.splits`, `api.runEfficiency`:

```jsx
import { useState, useEffect } from 'react'
import { api } from '../api'
import Card from '../ui/Card'
import SplitsBar from '../ui/SplitsBar'
import ZoneBar from '../ui/ZoneBar'
import MetricStat from '../ui/MetricStat'
import { paceStr, durationStr, kmStr } from '../format'

export default function RunDetail({ athleteId, runId, onBack }) {
  const [run, setRun] = useState(null)
  const [splits, setSplits] = useState([])
  const [eff, setEff] = useState(null)

  useEffect(() => {
    Promise.all([api.runs(athleteId), api.splits(athleteId, runId), api.runEfficiency(athleteId)])
      .then(([runs, sp, effs]) => {
        setRun(runs.find(r => r.activity_id === runId) || null)
        setSplits(sp)
        setEff((effs || []).find(e => e.activity_id === runId) || null)
      }).catch(() => setRun(null))
  }, [athleteId, runId])

  return (
    <div>
      <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--muted)', fontSize: 13, fontWeight: 500, marginBottom: 14 }}>‹ terug</button>
      {!run ? <p style={{ color: 'var(--faint)' }}>Laden…</p> : (
        <>
          <h2 style={{ fontSize: 16, fontWeight: 600 }}>{run.name || 'Run'}</h2>
          <p style={{ fontSize: 12, color: 'var(--faint)', margin: '2px 0 14px' }}>{run.date}</p>
          <Card>
            <div style={{ display: 'flex', gap: 8 }}>
              <MetricStat label="Afstand" value={kmStr(run.distance_km)} unit="km" />
              <MetricStat label="Tijd" value={durationStr(run.duration_s)} />
              <MetricStat label="Pace" value={paceStr(run.avg_pace_s_per_km)} />
              <MetricStat label="Ø HR" value={run.avg_hr ?? '–'} />
            </div>
          </Card>
          {splits.length > 0 && <Card><h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Splits per km</h3><SplitsBar splits={splits} /></Card>}
          <Card>
            <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Tijd in HR-zones</h3>
            <ZoneBar zones={run.zones} height={10} />
          </Card>
          {eff && (
            <Card>
              <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Loopdynamiek</h3>
              <div style={{ display: 'flex', gap: 8 }}>
                <MetricStat label="Cadans" value={eff.cadence_spm ?? '–'} />
                <MetricStat label="Grondcontact" value={eff.gct_ms ?? '–'} unit="ms" />
                <MetricStat label="Vert. osc." value={eff.vert_osc_mm ?? '–'} unit="mm" />
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verifieer via preview** — met dev-servers actief: navigeer naar Home → klik "Laatste run" (of via Runs). `preview_snapshot` → splits, zones, loopdynamiek zichtbaar. Geen console-errors.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/screens/RunDetail.jsx
git commit -m "feat(ui): run detail screen (splits, zones, dynamics)"
```

---

## Task 9: Fitheid-detail-scherm

**Files:** Create `dashboard/src/screens/FitnessDetail.jsx`.

- [ ] **Step 1: Implementeer** — consumeert `api.fitness`:

```jsx
import { useState, useEffect } from 'react'
import { api } from '../api'
import Card from '../ui/Card'
import Sparkline from '../ui/Sparkline'
import CoachNote from '../ui/CoachNote'
import { paceStr } from '../format'

export default function FitnessDetail({ athleteId, onBack }) {
  const [f, setF] = useState(null)
  useEffect(() => { api.fitness(athleteId).then(setF).catch(() => setF(null)) }, [athleteId])
  return (
    <div>
      <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--muted)', fontSize: 13, fontWeight: 500, marginBottom: 14 }}>‹ terug</button>
      <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Waar sta ik</h2>
      {!f ? <p style={{ color: 'var(--faint)' }}>Laden…</p> : (
        <>
          <Card>
            <p style={{ fontSize: 12, color: 'var(--muted)' }}>VO₂max</p>
            <p className="tnum" style={{ fontSize: 40, fontWeight: 500 }}>{f.vo2max_trend.at(-1)?.vo2max ?? '–'}</p>
            <Sparkline vals={f.vo2max_trend.map(x => x.vo2max)} />
          </Card>
          <div style={{ display: 'flex', gap: 12 }}>
            <Card style={{ flex: 1 }}>
              <p style={{ fontSize: 12, color: 'var(--muted)' }}>Tempo bij vaste HR</p>
              <p className="tnum" style={{ fontSize: 22, fontWeight: 500 }}>{paceStr(f.pace_at_hr.at(-1)?.pace_s_per_km)}</p>
              <p style={{ fontSize: 11, color: 'var(--faint)', marginTop: 4 }}>aerobe efficiëntie</p>
            </Card>
            <Card style={{ flex: 1 }}>
              <p style={{ fontSize: 12, color: 'var(--muted)' }}>Rust-HR</p>
              <p className="tnum" style={{ fontSize: 22, fontWeight: 500 }}>{f.resting_hr_trend.at(-1)?.resting_hr ?? '–'} <span style={{ fontSize: 11, color: 'var(--faint)' }}>bpm</span></p>
              <Sparkline vals={f.resting_hr_trend.map(x => x.resting_hr)} color="var(--z1)" />
            </Card>
          </div>
          {f.duiding ? <CoachNote>{f.duiding}</CoachNote> : null}
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verifieer via preview** — Home → klik "Waar sta ik" → snapshot toont VO₂max-trend, tempo@HR, rust-HR. Geen errors.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/screens/FitnessDetail.jsx
git commit -m "feat(ui): fitness detail screen"
```

---

## Task 10: Belasting-detail-scherm

**Files:** Create `dashboard/src/screens/LoadDetail.jsx`.

- [ ] **Step 1: Implementeer** — consumeert `api.trainingLoad` + `api.weeklyVolume`:

```jsx
import { useState, useEffect } from 'react'
import { api } from '../api'
import Card from '../ui/Card'
import VolumeBars from '../ui/VolumeBars'
import CoachNote from '../ui/CoachNote'

export default function LoadDetail({ athleteId, onBack }) {
  const [load, setLoad] = useState(null)
  const [vol, setVol] = useState([])
  useEffect(() => {
    Promise.all([api.trainingLoad(athleteId), api.weeklyVolume(athleteId)])
      .then(([l, v]) => { setLoad(l); setVol(v.slice().reverse()) }).catch(() => setLoad(null))
  }, [athleteId])
  const latest = load?.latest
  return (
    <div>
      <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--muted)', fontSize: 13, fontWeight: 500, marginBottom: 14 }}>‹ terug</button>
      <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Bouw ik veilig op</h2>
      {!load ? <p style={{ color: 'var(--faint)' }}>Laden…</p> : (
        <>
          <Card>
            <p style={{ fontSize: 12, color: 'var(--muted)' }}>Acute : chronische belasting (ACWR)</p>
            <p className="tnum" style={{ fontSize: 40, fontWeight: 500 }}>{latest?.acwr ?? '–'}</p>
            <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>optimaal 0,8–1,3</p>
          </Card>
          <Card>
            <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Weekvolume</h3>
            <VolumeBars vals={vol.map(w => w.km)} height={70} />
            <p style={{ fontSize: 11, color: 'var(--faint)', marginTop: 8 }}>laatste weken, km per week</p>
          </Card>
          {latest?.status_feedback ? <CoachNote>{latest.status_feedback}</CoachNote> : null}
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verifieer via preview** — Home → klik "Belasting" → snapshot toont ACWR + weekvolume-bars. Geen errors.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/screens/LoadDetail.jsx
git commit -m "feat(ui): load detail screen"
```

---

## Task 11: Runs-lijst-scherm

**Files:** Create `dashboard/src/screens/RunsList.jsx`.

- [ ] **Step 1: Implementeer** — consumeert `api.runs`:

```jsx
import { useState, useEffect } from 'react'
import { api } from '../api'
import Card from '../ui/Card'
import { paceStr, kmStr } from '../format'

export default function RunsList({ athleteId, onOpenRun }) {
  const [runs, setRuns] = useState(null)
  useEffect(() => { api.runs(athleteId).then(setRuns).catch(() => setRuns([])) }, [athleteId])
  if (!runs) return <p style={{ color: 'var(--faint)' }}>Laden…</p>
  return (
    <div>
      <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Runs</h2>
      <Card style={{ padding: '4px 14px' }}>
        {runs.map(r => (
          <div key={r.activity_id} onClick={() => onOpenRun(r.activity_id)}
            style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 4px', borderBottom: '1px solid var(--line)', cursor: 'pointer' }}>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: 14, fontWeight: 600 }}>{r.name || 'Run'}</p>
              <p style={{ fontSize: 11.5, color: 'var(--faint)', marginTop: 2 }}>{r.date}</p>
            </div>
            <div className="tnum" style={{ textAlign: 'right', fontSize: 13, fontWeight: 600 }}>
              {kmStr(r.distance_km)} km<br /><span style={{ color: 'var(--faint)', fontWeight: 500, fontSize: 11 }}>{paceStr(r.avg_pace_s_per_km)} /km</span>
            </div>
          </div>
        ))}
      </Card>
    </div>
  )
}
```

- [ ] **Step 2: Verifieer build + preview** — `npx vite build` slaagt nu (alle schermen bestaan). Preview: Runs-tab toont lijst; klik → run-detail.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/screens/RunsList.jsx
git commit -m "feat(ui): runs list screen"
```

---

## Task 12: PWA — manifest, icoon, service worker

**Files:** Create `dashboard/public/manifest.webmanifest`, `dashboard/public/icon-192.png`, `dashboard/public/icon-512.png`, `dashboard/public/sw.js`; Modify `dashboard/index.html`, `dashboard/src/main.jsx`.

- [ ] **Step 1: Manifest** — `dashboard/public/manifest.webmanifest`:
```json
{
  "name": "Marathon Coach",
  "short_name": "Coach",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0F1319",
  "theme_color": "#FF5A1F",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable" }
  ]
}
```

- [ ] **Step 2: Iconen** — genereer twee PNG-iconen (safety-orange achtergrond, wit hardloop-glyph) op 192 en 512 px. Maak ze met een klein script (Pillow) of een bestaande tool; plaats in `dashboard/public/`. Verifieer met `file dashboard/public/icon-192.png` dat het geldige PNG's zijn met juiste afmetingen.

- [ ] **Step 3: Service worker** — `dashboard/public/sw.js` (app-shell cache, network-first voor `/api`):
```javascript
const CACHE = 'mc-shell-v1'
self.addEventListener('install', e => { self.skipWaiting() })
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))))
})
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url)
  if (url.pathname.startsWith('/api')) return
  e.respondWith(
    caches.open(CACHE).then(cache =>
      cache.match(e.request).then(hit =>
        hit || fetch(e.request).then(res => { cache.put(e.request, res.clone()); return res })
          .catch(() => hit)))
  )
})
```

- [ ] **Step 4: Koppel manifest + registreer sw** — in `dashboard/index.html` `<head>` toevoegen:
```html
    <link rel="manifest" href="/manifest.webmanifest" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
```
Onderaan `dashboard/src/main.jsx` toevoegen:
```javascript
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => {}))
}
```

- [ ] **Step 5: Verifieer build + PWA** — `cd ~/Documents/garmin-coach/dashboard && npx vite build` → `dist/manifest.webmanifest`, `dist/sw.js`, iconen aanwezig in `dist/`. Preview: `preview_snapshot`; in de browser-devtools/Application zou de manifest geldig moeten zijn. (Installeerbaarheid op iOS via "Zet op beginscherm" wordt handmatig door Rowan getest na deploy.)

- [ ] **Step 6: Commit**

```bash
cd ~/Documents/garmin-coach
git add dashboard/public/manifest.webmanifest dashboard/public/icon-192.png dashboard/public/icon-512.png dashboard/public/sw.js dashboard/index.html dashboard/src/main.jsx
git commit -m "feat(pwa): manifest, icons, service worker, install support"
```

---

## Task 13: `vercel.json` controle voor PWA-assets

**Files:** Read/Modify `vercel.json` (repo-root).

- [ ] **Step 1: Controleer routes** — lees `vercel.json`. De statische route (`/(.*\..*)` → dist) moet `/manifest.webmanifest`, `/sw.js`, `/icon-*.png` serveren vanaf `dashboard/dist`. `sw.js` moet vanaf de site-root geserveerd worden (staat het in `dist/` na build → OK). Als een route dit blokkeert, voeg een expliciete route toe zodat deze bestanden vanaf root laden. Als alles al klopt: geen wijziging, noteer dat.

- [ ] **Step 2: Commit (indien gewijzigd)**

```bash
git add vercel.json && git commit -m "chore(deploy): serve pwa assets from root" || echo "geen wijziging nodig"
```

---

## Task 14: Oude componenten verwijderen

**Files:** Delete `dashboard/src/components/*`, oude `App.css` indien ongebruikt.

- [ ] **Step 1: Verwijder** — `git rm dashboard/src/components/*.jsx`. Controleer met `grep -rn "components/" dashboard/src` dat niets meer ernaar verwijst. Verwijder `dashboard/src/App.css` alleen als geen enkel bestand het importeert (`grep -rn "App.css" dashboard/src`).

- [ ] **Step 2: Verifieer build** — `cd ~/Documents/garmin-coach/dashboard && npx vite build` → slaagt zonder de oude componenten.

- [ ] **Step 3: Commit**

```bash
cd ~/Documents/garmin-coach
git add -A dashboard/src
git commit -m "chore(ui): remove old panel components"
```

---

## Task 15: Build, commit dist, deploy, live-verificatie

**Files:** `dashboard/dist/**` (gebouwde output — wordt gecommit, bestaande deploy-conventie).

- [ ] **Step 1: Productie-build** — `cd ~/Documents/garmin-coach/dashboard && npm run build`.

- [ ] **Step 2: Commit dist**

```bash
cd ~/Documents/garmin-coach
git add dashboard/dist
git commit -m "build: production dashboard bundle (fase 1 frontend)"
git push
```

- [ ] **Step 3: Deploy** — controleer account, dan deploy:

```bash
npx vercel@latest whoami   # MOET tonen: sidehustlehqs — zo niet: STOP
npx vercel@latest --prod --yes
```

- [ ] **Step 4: Live-verificatie** — na deploy:
```bash
curl -s https://garmin-coach-phi.vercel.app/api/athlete/rowan/home | .venv/bin/python -m json.tool | head -30
```
Verwacht: JSON met readiness/fitness/load/last_run. Open daarna https://garmin-coach-phi.vercel.app in de browser (preview-tools of handmatig) en bevestig dat het nieuwe dashboard laadt met beide atleten in de switcher, en dat detailschermen werken.

- [ ] **Step 5: PWA op telefoon (handmatig, door Rowan)** — open de URL op iPhone → deel-knop → "Zet op beginscherm" → app opent full-screen met eigen icoon. (Dit is de enige handmatige stap; de rest is geverifieerd.)

---

## Zelf-review (uitgevoerd)

- **Spec-dekking:** 5 schermen ✓ (Home T7, RunDetail T8, Fitness T9, Load T10, RunsList T11); tabs + placeholders (Schema/Delen) ✓ (T6); atleet-switcher ✓ (T6); mobiel-eerst tokens ✓ (T4); gelaagd (home → drill-down) ✓; duiding zichtbaar (CoachNote gevoed door backend-duiding) ✓; PWA installeerbaar ✓ (T12); deelbare weergave = Delen + publieke URL ✓; Vercel-redeploy + live-verificatie ✓ (T15). Follow-up `pace_at_hr` via API ✓ (T1). `weekly_volume_km` (ISO) vs bestaand `/weekly_volume` (`%W`): het Home- en Load-scherm gebruiken het bestaande `/weekly_volume`-endpoint (SQL), niet `metrics.weekly_volume_km`; deze blijven dus consistent met elkaar — `metrics.weekly_volume_km` blijft ongebruikt tot een latere fase (bewust, genoteerd).
- **Placeholders:** geen TBD; iedere stap heeft echte code/commando's. (De PNG-iconen in T12 zijn een genereer-stap, geen code-placeholder.)
- **Type-consistentie:** `api.home` payload-velden (`readiness`, `fitness`, `load`, `last_run`) matchen `/home` uit Plan 1 T9; `api.fitness` (`vo2max_trend`, `resting_hr_trend`, `pace_at_hr`, `duiding`) matcht T1; primitieven-props (`ZoneBar zones={z1..z5}`, `SplitsBar splits[].pace_s_per_km`, `Sparkline vals`) matchen het gebruik in de schermen.

## Volgende (na Plan 2)
Fase 1 is dan af (data-fundament + volledige app, live + installeerbaar). Daarna Fase 2: marathon-planningsengine (doel + datum → schema).
