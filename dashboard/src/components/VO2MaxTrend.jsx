import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export default function VO2MaxTrend({ data }) {
  const rows = data.vo2 || []
  if (rows.length === 0) return (
    <div className="card"><div className="label">VO₂max trend</div><div className="no-data">Geen data</div></div>
  )
  const latest = rows[rows.length - 1]?.vo2max

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <div className="label">VO₂max trend</div>
        <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--accent2)' }}>{latest}</div>
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={rows} margin={{ top: 4, right: 8, bottom: 4, left: -16 }}>
          <XAxis dataKey="date" tick={{ fill: 'var(--text-3)', fontSize: 11 }} />
          <YAxis domain={['dataMin - 2', 'dataMax + 2']} tick={{ fill: 'var(--text-3)', fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: 'var(--bg-card2)', border: '1px solid var(--border)', borderRadius: 8 }}
            formatter={(v) => [v, 'VO₂max']}
          />
          <Line type="monotone" dataKey="vo2max" stroke="var(--accent2)" strokeWidth={2} dot={{ fill: 'var(--accent2)', r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
