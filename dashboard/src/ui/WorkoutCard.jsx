import Card from './Card'
import CoachNote from './CoachNote'
import { paceStr } from '../format'

export default function WorkoutCard({ workout, onRevert }) {
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
      {w.is_adjusted ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8,
          background: 'var(--bg)', borderRadius: 9, padding: '7px 10px', margin: '0 0 10px' }}>
          <span style={{ fontSize: 11.5, color: 'var(--amber, #E8A33D)' }}>aangepast · {w.adjustment_reason}</span>
          {onRevert ? <button onClick={() => onRevert(w.date)} style={{ background: 'none', border: 'none', color: 'var(--accent)', fontSize: 11.5, fontWeight: 600, whiteSpace: 'nowrap' }}>← origineel</button> : null}
        </div>
      ) : null}
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
