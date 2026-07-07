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
