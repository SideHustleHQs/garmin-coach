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
