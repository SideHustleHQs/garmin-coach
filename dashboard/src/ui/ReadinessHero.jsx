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
        <div>
          <p style={{ fontSize: 11, color: 'var(--faint)', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 2 }}>Readiness</p>
          <span className="tnum" style={{ fontSize: 52, fontWeight: 900, lineHeight: 1, color: t.color }}>
            {r.score ?? '–'}
          </span>
        </div>
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

      <div style={{ display: 'flex', gap: 8, marginBottom: r.duiding ? 12 : 0 }}>
        <MetricStat label="HRV" value={r.hrv ?? '–'} color="var(--green)" />
        <MetricStat label="Slaap" value={sleepStr(r.sleep_s)} />
        <MetricStat label="Body" value={r.body_battery ?? '–'} />
      </div>
      {r.duiding ? <CoachNote>{r.duiding}</CoachNote> : null}
    </Card>
  )
}
