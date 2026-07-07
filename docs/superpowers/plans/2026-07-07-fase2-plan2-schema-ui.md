# Fase 2 · Plan 2 — Schema-UI (frontend) + live

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** De "Schema"-placeholder-tab vervangen door het echte plan-scherm (Optie A: plan-header + week-strip + workout met doel-paces), en de plannen van Rowan + vriendin live op het dashboard krijgen.

**Architecture:** React 19 (Vite). Nieuwe UI-primitieven (`PlanHeader`, `WeekStrip`, `WorkoutCard`) + herbouwde `screens/Schema.jsx` op de Fase 2-endpoints (`/plan`, `/plan/week`, `/workout`, `/register`). Live-bootstrap via het `POST /plan`-endpoint (leest fitheid correct uit Supabase). Deploy via bestaande flow.

**Tech Stack:** React 19, Vite, plain CSS-tokens (bestaand `theme.css`), Vitest (format-helpers), preview/curl-verificatie. Repo `~/garmin-coach`. Deploy: `dashboard/dist` committen → `npx vercel@latest --prod` (whoami=sidehustlehqs).

**Voorwaarden:** Fase 2 Plan 1 is gemerged in `main` (endpoints `/plan`, `/plan/week`, `/workout/{date}`, `/workout/{date}/register` bestaan). Fase 1 frontend-primitieven (`Card`, `CoachNote`, `format.js`) bestaan.

**Design (Optie A, goedgekeurd):** plan-header (race + aftellen + week X/N + geschatte tijd) → horizontale 7-daagse week-strip (type-icoon, geselecteerde dag geaccentueerd) → workout-kaart van de geselecteerde dag (segments met doel-pace + coach-note). Consistent met Fase 1 (donker/licht, safety-orange).

---

## Bestandsstructuur (dashboard/)

| Bestand | Verantwoordelijkheid | Actie |
|---|---|---|
| `src/api.js` | endpoints plan/week/workout/register | Modify |
| `src/format.js` | `hmStr`, `hmRange` (uur:min tijd) | Modify + test |
| `src/ui/PlanHeader.jsx` | race + week + geschatte tijd | Create |
| `src/ui/WeekStrip.jsx` | 7-daagse strip, dag-selectie | Create |
| `src/ui/WorkoutCard.jsx` | workout-detail (segments + coach) | Create |
| `src/screens/Schema.jsx` | het scherm (data + week-nav + selectie) | Replace |
| `src/App.jsx` | `athleteId` doorgeven aan Schema | Modify (1 regel) |

---

## Task 1: API-client + format-helpers (TDD voor format)

**Files:** Modify `dashboard/src/api.js`, `dashboard/src/format.js`, `dashboard/src/format.test.js`.

- [ ] **Step 1: api.js** — voeg toe in het `api`-object (behoud bestaande):
```javascript
  plan:            (id) => get(`/athlete/${id}/plan`),
  planWeek:        (id, week) => get(`/athlete/${id}/plan/week?week=${week}`),
  workout:         (id, date) => get(`/athlete/${id}/workout/${date}`),
```
En een POST-helper + register. Voeg bovenaan `api.js` een `post` toe naast `get`:
```javascript
async function post(path, body) {
  const r = await fetch(BASE + path, { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined })
  if (!r.ok) throw new Error(`${r.status} ${path}`)
  return r.json()
}
```
En in het `api`-object: `registerWorkout: (id, date) => post(`/athlete/${id}/workout/${date}/register`),`

- [ ] **Step 2: format-test** — voeg toe aan `dashboard/src/format.test.js`:
```javascript
import { hmStr, hmRange } from './format'

describe('time format', () => {
  it('hmStr formats seconds as h:mm', () => {
    expect(hmStr(14400)).toBe('4:00')
    expect(hmStr(13920)).toBe('3:52')
    expect(hmStr(null)).toBe('–')
  })
  it('hmRange joins two times', () => {
    expect(hmRange([13920, 14700])).toBe('3:52–4:05')
    expect(hmRange(null)).toBe('–')
  })
})
```

- [ ] **Step 3: Run — faalt** (`cd ~/garmin-coach/dashboard && npm test`) → FAIL (hmStr niet geëxporteerd).

- [ ] **Step 4: format.js** — voeg toe:
```javascript
export function hmStr(sec) {
  if (sec == null) return '–'
  const h = Math.floor(sec / 3600)
  const m = Math.round((sec % 3600) / 60)
  return `${h}:${String(m).padStart(2, '0')}`
}

export function hmRange(r) {
  if (!r || r.length !== 2) return '–'
  return `${hmStr(r[0])}–${hmStr(r[1])}`
}
```

- [ ] **Step 5: Run — slaagt** (`npm test` → alle format-tests groen). Verifieer build: `npx vite build` slaagt.

- [ ] **Step 6: Commit**
```bash
cd ~/garmin-coach
git add dashboard/src/api.js dashboard/src/format.js dashboard/src/format.test.js
git commit -m "feat(ui): plan/week/workout/register api + time format helpers"
```

---

## Task 2: UI-primitieven PlanHeader / WeekStrip / WorkoutCard

**Files:** Create `dashboard/src/ui/PlanHeader.jsx`, `WeekStrip.jsx`, `WorkoutCard.jsx`.

- [ ] **Step 1: PlanHeader.jsx**
```jsx
import Card from './Card'
import { hmRange } from '../format'

export default function PlanHeader({ plan, currentWeek }) {
  const weeksToGo = plan.race_date
    ? Math.max(0, Math.ceil((new Date(plan.race_date) - new Date()) / (7 * 864e5)))
    : null
  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <p style={{ fontSize: 15, fontWeight: 600 }}>{plan.race_name}</p>
          <p style={{ fontSize: 11.5, color: 'var(--faint)', textTransform: 'uppercase', letterSpacing: '.05em', marginTop: 3 }}>
            {plan.race_date}{weeksToGo != null ? ` · nog ${weeksToGo} wk` : ''}
          </p>
        </div>
        <div style={{ background: 'var(--accent)', borderRadius: 11, padding: '5px 9px' }}>
          <span className="tnum" style={{ fontSize: 14, fontWeight: 600, color: '#0F1319' }}>
            {plan.race_distance_km >= 42 ? '42.2' : Math.round(plan.race_distance_km)}
          </span>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 18, marginTop: 12 }}>
        <div><p style={{ fontSize: 11, color: 'var(--faint)', textTransform: 'uppercase' }}>Week</p>
          <p className="tnum" style={{ fontSize: 17, fontWeight: 600 }}>{currentWeek} / {plan.weeks}</p></div>
        <div><p style={{ fontSize: 11, color: 'var(--faint)', textTransform: 'uppercase' }}>Geschatte tijd</p>
          <p className="tnum" style={{ fontSize: 17, fontWeight: 600 }}>{hmRange(plan.estimated_time_s)}</p></div>
      </div>
    </Card>
  )
}
```

- [ ] **Step 2: WeekStrip.jsx** (days = 7 planned_workout rows; selectedDate; onSelect)
```jsx
const ICON = { run: '🏃', strength: '🏋', hyrox: '⚡', rest: '·', race: '🏁' }
const RUNC = { easy: 'var(--z2)', quality: 'var(--accent)', long: 'var(--z4)', race: 'var(--hard)' }
const NL = ['MA', 'DI', 'WO', 'DO', 'VR', 'ZA', 'ZO']

export default function WeekStrip({ days, selectedDate, onSelect }) {
  return (
    <div style={{ display: 'flex', gap: 5, marginBottom: 14 }}>
      {days.map((d, i) => {
        const on = d.date === selectedDate
        const color = d.day_type === 'run' ? (RUNC[d.run_type] || 'var(--z2)') : 'var(--faint)'
        return (
          <button key={d.date} onClick={() => onSelect(d.date)} aria-label={`${NL[i]} ${d.title}`}
            style={{ flex: 1, textAlign: 'center', background: on ? 'var(--accent)' : 'var(--card)',
              border: '1px solid var(--line)', borderRadius: 10, padding: '8px 0', cursor: 'pointer' }}>
            <p style={{ fontSize: 10, fontWeight: 600, margin: 0, color: on ? '#0F1319' : 'var(--faint)' }}>{NL[i]}</p>
            <span style={{ fontSize: 14, color: on ? '#0F1319' : color }}>{ICON[d.day_type] || '·'}</span>
          </button>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 3: WorkoutCard.jsx** (workout = één planned_workout row)
```jsx
import Card from './Card'
import CoachNote from './CoachNote'
import { paceStr } from '../format'

export default function WorkoutCard({ workout }) {
  if (!workout) return null
  const w = workout
  const isRun = w.day_type === 'run' || w.day_type === 'race'
  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.05em' }}>
          {w.run_type || w.day_type}
        </span>
        <span style={{ fontSize: 11, color: 'var(--faint)' }}>{w.date}</span>
      </div>
      <p style={{ fontSize: 18, fontWeight: 600, margin: '0 0 12px' }}>{w.title}</p>
      {isRun && w.segments && w.segments.map((s, i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', background: 'var(--bg)',
          borderRadius: 9, padding: '8px 11px', marginBottom: 5,
          borderLeft: s.target_pace_s === w.target_pace_s ? '3px solid var(--accent)' : 'none' }}>
          <span style={{ fontSize: 12.5, color: 'var(--muted)' }}>{s.label}</span>
          <span className="tnum" style={{ fontSize: 12.5, fontWeight: 600 }}>{paceStr(s.target_pace_s)} /km</span>
        </div>
      ))}
      {!isRun && <p style={{ fontSize: 13, color: 'var(--muted)' }}>Eigen sessie — geen loopplan vandaag.</p>}
      {w.coach_note ? <div style={{ marginTop: 12 }}><CoachNote>{w.coach_note}</CoachNote></div> : null}
    </Card>
  )
}
```

- [ ] **Step 4: Verifieer build** — `cd ~/garmin-coach/dashboard && npx vite build` slaagt (primitieven nog ongebruikt).

- [ ] **Step 5: Commit**
```bash
cd ~/garmin-coach
git add dashboard/src/ui/PlanHeader.jsx dashboard/src/ui/WeekStrip.jsx dashboard/src/ui/WorkoutCard.jsx
git commit -m "feat(ui): plan header, week strip, workout card primitives"
```

---

## Task 3: Schema-scherm (vervangt placeholder)

**Files:** Replace `dashboard/src/screens/Schema.jsx`; Modify `dashboard/src/App.jsx` (geef `athleteId` door).

- [ ] **Step 1: App.jsx** — vervang de Schema-render-regel. Zoek `{screen === 'schema' && <Schema />}` en vervang door:
```jsx
        {screen === 'schema' && <Schema athleteId={athleteId} />}
```

- [ ] **Step 2: Vervang `dashboard/src/screens/Schema.jsx`** volledig:
```jsx
import { useState, useEffect } from 'react'
import { api } from '../api'
import PlanHeader from '../ui/PlanHeader'
import WeekStrip from '../ui/WeekStrip'
import WorkoutCard from '../ui/WorkoutCard'

function currentWeekOf(plan) {
  if (!plan?.start_date) return 1
  const wk = Math.floor((new Date() - new Date(plan.start_date)) / (7 * 864e5)) + 1
  return Math.min(Math.max(wk, 1), plan.weeks)
}

export default function Schema({ athleteId }) {
  const [plan, setPlan] = useState(undefined)   // undefined=laden, null=geen plan
  const [week, setWeek] = useState(1)
  const [days, setDays] = useState([])
  const [selected, setSelected] = useState(null)
  const [err, setErr] = useState(false)

  useEffect(() => {
    setPlan(undefined); setErr(false)
    api.plan(athleteId).then(p => {
      if (!p || p.plan === null) { setPlan(null); return }
      setPlan(p); setWeek(currentWeekOf(p))
    }).catch(() => setErr(true))
  }, [athleteId])

  useEffect(() => {
    if (!plan) return
    api.planWeek(athleteId, week).then(ds => {
      setDays(ds)
      const today = new Date().toISOString().slice(0, 10)
      const pick = ds.find(d => d.date === today) || ds.find(d => d.day_type === 'run') || ds[0]
      setSelected(pick ? pick.date : null)
    }).catch(() => setErr(true))
  }, [plan, week, athleteId])

  if (err) return <p style={{ color: 'var(--hard)' }}>Kon plan niet laden.</p>
  if (plan === undefined) return <p style={{ color: 'var(--faint)' }}>Laden…</p>
  if (plan === null) return (
    <div style={{ textAlign: 'center', color: 'var(--faint)', padding: '60px 20px' }}>
      <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--ink)' }}>Nog geen plan</p>
      <p style={{ fontSize: 13, marginTop: 8 }}>Er is nog geen trainingsplan aangemaakt voor deze atleet.</p>
    </div>
  )

  const selectedWorkout = days.find(d => d.date === selected)
  return (
    <div>
      <PlanHeader plan={plan} currentWeek={week} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '4px 2px 8px' }}>
        <button onClick={() => setWeek(w => Math.max(1, w - 1))} disabled={week <= 1}
          style={{ background: 'none', border: 'none', color: week <= 1 ? 'var(--faint)' : 'var(--muted)', fontSize: 18 }}>‹</button>
        <span style={{ fontSize: 12, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.06em' }}>Week {week} / {plan.weeks}</span>
        <button onClick={() => setWeek(w => Math.min(plan.weeks, w + 1))} disabled={week >= plan.weeks}
          style={{ background: 'none', border: 'none', color: week >= plan.weeks ? 'var(--faint)' : 'var(--muted)', fontSize: 18 }}>›</button>
      </div>
      <WeekStrip days={days} selectedDate={selected} onSelect={setSelected} />
      <WorkoutCard workout={selectedWorkout} />
    </div>
  )
}
```

- [ ] **Step 3: Verifieer build** — `cd ~/garmin-coach/dashboard && npx vite build` slaagt.

- [ ] **Step 4: Lokale preview-verificatie** — start API + Vite lokaal (SQLite met de al-gebootstrapte plannen uit Plan 1):
`cd ~/garmin-coach && DATABASE_URL= ./start.sh` (of API op 8000 + vite op 5173). Open localhost:5173, tab **Schema**. Controleer (preview-tools of handmatig): plan-header (Rowan Marathon, week X/14, geschatte tijd), week-strip met dag-iconen, klik op ma → tempo-workout met doel-paces, klik andere dagen. Wissel atleet → vriendin's plan. Geen console-errors. Stop de servers.

- [ ] **Step 5: Commit**
```bash
cd ~/garmin-coach
git add dashboard/src/screens/Schema.jsx dashboard/src/App.jsx
git commit -m "feat(ui): schema screen — plan header, week nav, workout with target paces"
```

---

## Task 4: Build, deploy, live-bootstrap, verificatie

**Files:** `dashboard/dist/**` (gebouwde output).

- [ ] **Step 1: Productie-build + commit dist**
```bash
cd ~/garmin-coach/dashboard && npm run build
cd ~/garmin-coach && git add dashboard/dist && git commit -m "build: schema-tab bundle (fase 2)" && git push
```

- [ ] **Step 2: Deploy** — account-check, dan prod:
```bash
npx vercel@latest whoami   # MOET sidehustlehqs zijn — zo niet STOP
npx vercel@latest --prod --yes
```

- [ ] **Step 3: Live-bootstrap de plannen naar Supabase via het endpoint** (leest fitheid correct uit Supabase; `create_plans.py` NIET gebruiken — die geeft op Postgres lege fitheid). Rowan:
```bash
curl -s -X POST https://garmin-coach-phi.vercel.app/api/athlete/rowan/plan \
  -H 'Content-Type: application/json' \
  -d '{"race_name":"Marathon van Amsterdam","race_date":"2026-10-18","race_distance_km":42.195,"goal_time_s":14400,"start_date":"2026-07-13","weeks":14,"run_days":["mon","thu","sat"],"fixed_days":{"tue":"strength","wed":"hyrox","fri":"strength"}}'
```
Vriendin:
```bash
curl -s -X POST https://garmin-coach-phi.vercel.app/api/athlete/vriendin/plan \
  -H 'Content-Type: application/json' \
  -d '{"race_name":"NN Dam tot Damloop","race_date":"2026-09-20","race_distance_km":16.1,"start_date":"2026-07-13","weeks":10,"run_days":["wed","sun"],"fixed_days":{}}'
```
Expected: elk `{"ok": true, "days": ...}` (98 resp. 70).

- [ ] **Step 4: Live-verificatie**
```bash
curl -s "https://garmin-coach-phi.vercel.app/api/athlete/rowan/plan" | .venv/bin/python -m json.tool | head -15
curl -s "https://garmin-coach-phi.vercel.app/api/athlete/rowan/plan/week?week=1" | .venv/bin/python -m json.tool | head -30
```
Expected: plan-header (Marathon, weeks 14, estimated_time_s) + week-1 met 7 dagen incl. runs met segments. Open daarna https://garmin-coach-phi.vercel.app → tab **Schema** in de browser en bevestig dat het plan rendert voor beide atleten (via de switcher). Geen console-errors.

- [ ] **Step 5: Klaar** — geen extra commit nodig (dist al gecommit). Meld resultaat.

---

## Zelf-review (uitgevoerd)

- **Spec-dekking:** Schema-tab Optie A (plan-header + week-strip + workout met doel-paces) ✓ (T2/T3); endpoints geconsumeerd (`/plan`, `/plan/week`, `/workout` via week-data) ✓; per-atleet via `athleteId`-prop + bestaande switcher ✓ (T3); geschatte tijd geformatteerd ✓ (T1); lege/laad/fout-staten ✓ (T3); live via deploy + bootstrap ✓ (T4). "register" API-helper toegevoegd (T1) maar UI-knop "training registreren" is optioneel in dit plan — de sync koppelt runs later automatisch; een expliciete knop kan een fast-follow zijn (genoteerd).
- **Placeholders:** geen; alle stappen bevatten echte code/commando's.
- **Type-consistentie:** `api.plan/planWeek/workout/registerWorkout` matchen Plan 1-endpoints; `plan`-velden (`race_name/race_date/race_distance_km/weeks/estimated_time_s/start_date`) matchen `GET /plan`; `days`-velden (`date/day_type/run_type/title/segments/target_pace_s/coach_note`) matchen `_wo_dict`; `WeekStrip`/`WorkoutCard` props matchen `Schema.jsx`.

## Fast-follow (niet-blokkerend)
- Expliciete "training registreren"-knop in WorkoutCard (POST register) — nu alleen API-helper.
- Auto-match gesyncte run → planned_workout op datum, meenemen in de dagelijkse sync.
- Fase 3: plan herberekent na elke run.
