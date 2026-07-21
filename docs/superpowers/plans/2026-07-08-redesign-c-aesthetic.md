# Redesign — C Aesthetic (Bold & Athletic) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vervang de huidige slate/safety-orange stijl door een Bold & Athletic donker design: #111827 achtergrond, grote getallen, en kleurgecodeerde metrics per categorie (groen=readiness/HRV, blauw=hardlopen/VO₂max, geel=schema/training, rood=waarschuwing).

**Architecture:** Alleen frontend. Alle kleuren via CSS custom properties in `theme.css`. Componenten krijgen een `borderTop` of ring-indicator op basis van categorie-kleur. Geen nieuwe API-calls. Geen nieuwe bestanden — alleen bestaande UI-bestanden.

**Tech Stack:** React 19, Vite, CSS custom properties. Repo `~/garmin-coach`. Frontend in `dashboard/`.

---

## Bestandsstructuur

| Bestand | Wijziging |
|---|---|
| `dashboard/src/theme.css` | Nieuwe kleur-tokens (donker + C-palet) |
| `dashboard/src/ui/ReadinessHero.jsx` | Groot getal + ring-indicator groen/geel/rood |
| `dashboard/src/ui/StatTile.jsx` | Groter getal, colored border-top, bolder |
| `dashboard/src/ui/Card.jsx` | Donkerdere achtergrond-variant via prop |
| `dashboard/src/screens/Home.jsx` | Section-headers met categorie-kleur |
| `dashboard/src/App.jsx` | Header donker, geen witte balk |
| `dashboard/dist/` | Herbouwen na alle wijzigingen |

Tests: vitest (`cd dashboard && npm test`). Visueel verifiëren op http://localhost:5173.

---

## Task 1: Nieuwe design tokens in theme.css

**Files:** Modify `dashboard/src/theme.css`

- [ ] **Step 1:** Vervang de volledige inhoud van `dashboard/src/theme.css`:

```css
:root {
  /* Basis */
  --bg: #111827; --card: #1F2937; --ink: #F9FAFB; --muted: #9CA3AF; --faint: #6B7280;
  --line: #374151; --radius: 12px; --radius-lg: 18px;
  --font: -apple-system, BlinkMacSystemFont, system-ui, "Segoe UI", Roboto, sans-serif;

  /* Categorie-kleuren */
  --green: #10B981; --green-t: #064E3B; --green-d: #059669;
  --blue: #3B82F6;  --blue-t: #1E3A5F;  --blue-d: #2563EB;
  --amber: #F59E0B; --amber-t: #451A03;  --amber-d: #D97706;
  --red: #EF4444;   --red-t: #450A0A;    --red-d: #DC2626;
  --purple: #8B5CF6;

  /* Semantisch (worden gebruikt door bestaande componenten) */
  --accent: var(--amber); --accent-d: var(--amber-d); --accent-t: var(--amber-t);
  --good: var(--green); --good-t: var(--green-t);
  --caution: var(--amber); --hard: var(--red);
  --z1: var(--blue); --z2: var(--green); --z3: #7CC24B; --z4: var(--amber); --z5: var(--red);
}

/* Lichte modus: behoud leesbaar contrast, gebruik dezelfde categorie-kleuren */
@media (prefers-color-scheme: light) {
  :root {
    --bg: #F3F4F6; --card: #FFFFFF; --ink: #111827; --muted: #4B5563; --faint: #9CA3AF;
    --line: #E5E7EB;
    --green-t: #D1FAE5; --blue-t: #DBEAFE; --amber-t: #FEF3C7; --red-t: #FEE2E2;
    --good-t: #D1FAE5;
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

- [ ] **Step 2:** Start dev server, controleer dat achtergrond donker is:
```bash
cd ~/garmin-coach/dashboard && npm run dev
```
Open http://localhost:5173. Achtergrond moet #111827 zijn. Geen broken layout.

- [ ] **Step 3: Commit**
```bash
cd ~/garmin-coach
git add dashboard/src/theme.css
git commit -m "design: C-aesthetic tokens — dark #111827, green/blue/amber/red categorie-kleuren"
```

---

## Task 2: ReadinessHero — groot getal + kleur-ring

**Files:** Modify `dashboard/src/ui/ReadinessHero.jsx`

- [ ] **Step 1:** Vervang `ReadinessHero.jsx` volledig:

```jsx
import Card from './Card'
import MetricStat from './MetricStat'
import CoachNote from './CoachNote'
import { sleepStr } from '../format'

function tone(score) {
  if (score == null) return { color: 'var(--faint)', bg: 'var(--line)', label: '' }
  if (score >= 75) return { color: 'var(--green)', bg: 'var(--green-t)', label: 'Goed' }
  if (score >= 50) return { color: 'var(--amber)', bg: 'var(--amber-t)', label: 'Matig' }
  return { color: 'var(--red)', bg: 'var(--red-t)', label: 'Rust' }
}

export default function ReadinessHero({ readiness }) {
  const r = readiness || {}
  const t = tone(r.score)

  return (
    <Card style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        {/* Groot getal */}
        <div>
          <p style={{ fontSize: 11, color: 'var(--faint)', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 2 }}>Readiness</p>
          <span className="tnum" style={{ fontSize: 52, fontWeight: 900, lineHeight: 1, color: t.color }}>
            {r.score ?? '–'}
          </span>
        </div>
        {/* Ring-indicator */}
        <div style={{
          width: 68, height: 68, borderRadius: '50%',
          border: `4px solid ${t.color}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: t.bg,
        }}>
          {t.label ? (
            <span style={{ fontSize: 10, fontWeight: 700, color: t.color, textTransform: 'uppercase', letterSpacing: '.04em' }}>
              {t.label}
            </span>
          ) : null}
        </div>
      </div>

      {/* HRV / Slaap / Body */}
      <div style={{ display: 'flex', gap: 8, marginBottom: r.duiding ? 12 : 0 }}>
        <MetricStat label="HRV" value={r.hrv ?? '–'} color="var(--green)" />
        <MetricStat label="Slaap" value={sleepStr(r.sleep_s)} />
        <MetricStat label="Body" value={r.body_battery ?? '–'} />
      </div>
      {r.duiding ? <CoachNote>{r.duiding}</CoachNote> : null}
    </Card>
  )
}
```

- [ ] **Step 2:** Check `MetricStat.jsx` accepteert een `color` prop — als niet:
```bash
grep -n "color" ~/garmin-coach/dashboard/src/ui/MetricStat.jsx
```
Voeg `color` prop toe als hij er niet in zit:
```jsx
export default function MetricStat({ label, value, color }) {
  return (
    <div style={{ flex: 1, background: 'var(--line)', borderRadius: 8, padding: '8px 10px' }}>
      <p style={{ fontSize: 10, color: 'var(--faint)', textTransform: 'uppercase', marginBottom: 2 }}>{label}</p>
      <p className="tnum" style={{ fontSize: 15, fontWeight: 700, color: color || 'var(--ink)' }}>{value ?? '–'}</p>
    </div>
  )
}
```

- [ ] **Step 3:** Controleer in browser: groot getal (52px) in groene/gele/rode kleur, ring ernaast.

- [ ] **Step 4: Commit**
```bash
git add dashboard/src/ui/ReadinessHero.jsx dashboard/src/ui/MetricStat.jsx
git commit -m "design: ReadinessHero groot getal + kleur-ring (C-aesthetic)"
```

---

## Task 3: StatTile — colored border-top per categorie

**Files:** Modify `dashboard/src/ui/StatTile.jsx`

- [ ] **Step 1:** Vervang `StatTile.jsx`:

```jsx
import Sparkline from './Sparkline'

export default function StatTile({ label, value, unit, trendVals, trendColor, trendDir, onClick, children, accentColor }) {
  // accentColor = CSS var string, bijv. 'var(--blue)' of 'var(--green)'
  const top = accentColor ? `3px solid ${accentColor}` : '3px solid var(--line)'
  return (
    <div onClick={onClick} style={{
      background: 'var(--card)', borderRadius: 13, padding: '10px 11px',
      cursor: onClick ? 'pointer' : 'default',
      borderTop: top,
    }}>
      <p style={{ fontSize: 10, color: 'var(--faint)', textTransform: 'uppercase', letterSpacing: '.04em', margin: 0 }}>{label}</p>
      <p className="tnum" style={{ fontSize: 22, fontWeight: 800, margin: '4px 0 0', lineHeight: 1.1 }}>
        {value ?? '–'}
        {unit ? <span style={{ fontSize: 11, color: 'var(--faint)', fontWeight: 500 }}> {unit}</span> : null}
        {trendDir ? <span style={{ fontSize: 12, color: trendDir === 'up' ? 'var(--green)' : 'var(--red)' }}> {trendDir === 'up' ? '↑' : '↓'}</span> : null}
      </p>
      {trendVals && trendVals.filter(v => v != null).length >= 2
        ? <Sparkline vals={trendVals} color={trendColor || accentColor || 'var(--green)'} height={22} />
        : null}
      {children}
    </div>
  )
}
```

- [ ] **Step 2:** Update `Home.jsx` — voeg `accentColor` prop toe aan elke StatTile:

Hardlopen-sectie (blauw):
```jsx
<StatTile label="VO₂max" value={r.vo2max} accentColor="var(--blue)"
  trendVals={(r.vo2max_trend || []).map(x => x.vo2max)} trendColor="var(--blue)"
  onClick={() => onNav && onNav('fitness')} />
<StatTile label="Weekvolume" accentColor="var(--blue)"
  value={r.weekly_volume?.length ? Math.round(r.weekly_volume[r.weekly_volume.length - 1].km) : null}
  unit="km" onClick={() => onNav && onNav('load')}>
  <VolumeBars vals={(r.weekly_volume || []).map(w => w.km)} height={22} />
</StatTile>
<StatTile label="Belasting (ACWR)" accentColor="var(--blue)" value={r.acwr}
  onClick={() => onNav && onNav('load')} />
<StatTile label="Tempo @150bpm" accentColor="var(--blue)" value={paceStr(r.pace_at_hr)} unit="/km"
  trendVals={(r.pace_at_hr_trend || []).map(x => x.pace_s_per_km)} trendColor="var(--blue)"
  onClick={() => onNav && onNav('fitness')} />
```

Gezondheid-sectie (groen):
```jsx
<StatTile label="HRV" accentColor="var(--green)" value={h.hrv}
  trendVals={(h.hrv_trend || []).map(x => x.hrv)} trendColor="var(--green)" />
<StatTile label="Slaap" accentColor="var(--green)" value={sleepStr(h.sleep?.duration_s)}>
  {h.sleep?.score != null ? <p style={{ fontSize: 10, color: 'var(--faint)', margin: '2px 0 0' }}>score {h.sleep.score}</p> : null}
</StatTile>
<StatTile label="Body" accentColor="var(--green)" value={h.body_battery} />
<StatTile label="Rust-HR" accentColor="var(--green)" value={h.resting_hr} unit="bpm"
  trendVals={(h.resting_hr_trend || []).map(x => x.resting_hr)} trendColor="var(--green)" />
<StatTile label="Stappen" accentColor="var(--green)" value={h.steps != null ? Math.round(h.steps / 100) / 10 + 'k' : null} />
<StatTile label="Kcal" accentColor="var(--green)" value={h.active_calories} unit="kcal" />
```

- [ ] **Step 3:** Controleer in browser: blauwe top-borders voor hardlopen, groene voor gezondheid.

- [ ] **Step 4: Commit**
```bash
git add dashboard/src/ui/StatTile.jsx dashboard/src/screens/Home.jsx
git commit -m "design: StatTile colored border-top per categorie (blauw=hardlopen, groen=gezondheid)"
```

---

## Task 4: Training vandaag kaart — amber accent + SectionHeaders

**Files:** Modify `dashboard/src/screens/Home.jsx`, `dashboard/src/ui/SectionHeader.jsx`

- [ ] **Step 1:** Update de "Training vandaag" Card in `Home.jsx` — amber top-border:
```jsx
<Card onClick={() => onNav && onNav('schema')}
  style={{ borderTop: '3px solid var(--amber)', marginBottom: 12 }}>
  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
    <span style={{ fontSize: 10, color: 'var(--amber)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em' }}>
      Training vandaag{tw?.week_num ? ` · week ${tw.week_num}` : ''}
    </span>
  </div>
  {tw ? (
    <>
      <p style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>{tw.title}</p>
      {tw.target_pace_s ? <p style={{ fontSize: 12, color: 'var(--muted)', margin: '4px 0 0' }}>doel {paceStr(tw.target_pace_s)} /km</p> : null}
    </>
  ) : <p style={{ fontSize: 14, color: 'var(--muted)', margin: 0 }}>Geen training gepland vandaag.</p>}
</Card>
```

- [ ] **Step 2:** Update `dashboard/src/ui/SectionHeader.jsx` — categorie-kleur via prop:
```jsx
export default function SectionHeader({ children, color }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      margin: '18px 0 10px',
    }}>
      {color && <div style={{ width: 3, height: 16, borderRadius: 2, background: color }} />}
      <p style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase',
        letterSpacing: '.08em', color: color || 'var(--muted)' }}>{children}</p>
    </div>
  )
}
```

- [ ] **Step 3:** Pas `Home.jsx` aan — geef kleur mee aan SectionHeaders:
```jsx
<SectionHeader color="var(--blue)">Hardlopen</SectionHeader>
// ...
<SectionHeader color="var(--green)">Gezondheid</SectionHeader>
```

- [ ] **Step 4:** Controleer in browser: amber trainings-kaart, gekleurde section headers met linkerbalkje.

- [ ] **Step 5: Commit**
```bash
git add dashboard/src/screens/Home.jsx dashboard/src/ui/SectionHeader.jsx
git commit -m "design: amber training-kaart, gekleurde section headers"
```

---

## Task 5: App header + build + deploy

**Files:** Modify `dashboard/src/App.jsx`, build `dashboard/dist/`

- [ ] **Step 1:** Update header in `App.jsx` — verwijder witte achtergrond, gebruik donker:
```jsx
<div style={{ padding: '18px 16px 12px', borderBottom: '1px solid var(--line)', background: 'var(--card)' }}>
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 800, letterSpacing: '-.02em' }}>Hoi, {athlete.display_name}</h1>
      <p style={{ fontSize: 11, color: 'var(--faint)', marginTop: 2, textTransform: 'uppercase', letterSpacing: '.06em' }}>marathon-coach</p>
    </div>
    <CountdownChip weeks={null} label="wk tot race" />
  </div>
  <AthleteSwitcher athletes={athletes} current={athleteId} onSwitch={setAthleteId} />
</div>
```

- [ ] **Step 2:** Run vitest — alle tests groen:
```bash
cd ~/garmin-coach/dashboard && npm test -- --run
```
Verwacht: alle tests pass (geen logica gewijzigd).

- [ ] **Step 3:** Build voor productie:
```bash
cd ~/garmin-coach/dashboard && npm run build
```
Verwacht: geen errors. `dist/` gevuld.

- [ ] **Step 4:** Deploy:
```bash
cd ~/garmin-coach
# Verifieer account
npx vercel@latest whoami
# Moet tonen: sidehustlehqs
git add dashboard/dist dashboard/src/App.jsx
git commit -m "design: C-aesthetic compleet — donker, bold, kleurgecodeerd"
git push
npx vercel@latest --prod
```

- [ ] **Step 5:** Open https://garmin-coach-phi.vercel.app — controleer donker design, grote getallen, gekleurde accenten.
