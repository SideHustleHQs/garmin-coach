import { paceStr } from '../format'
export default function SplitsBar({ splits = [] }) {
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
