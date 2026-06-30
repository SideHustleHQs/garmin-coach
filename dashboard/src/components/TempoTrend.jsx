import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

function paceLabel(secsPerKm) {
  if (!secsPerKm) return '--'
  const m = Math.floor(secsPerKm / 60)
  const s = Math.floor(secsPerKm % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

export default function TempoTrend({ data }) {
  const rows = data.tempo || []
  if (rows.length === 0) return (
    <div className="card"><div className="label">Tempo-trend</div><div className="no-data">Geen data</div></div>
  )
  const avg = rows.reduce((a, r) => a + r.avg_pace_s_per_km, 0) / rows.length

  return (
    <div className="card">
      <div className="label" style={{ marginBottom: 12 }}>Tempo-trend (min/km)</div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={rows} margin={{ top: 4, right: 8, bottom: 4, left: -16 }}>
          <XAxis dataKey="date" tick={{ fill: 'var(--text-3)', fontSize: 11 }} />
          <YAxis
            reversed
            tickFormatter={paceLabel}
            tick={{ fill: 'var(--text-3)', fontSize: 11 }}
            domain={['dataMin - 10', 'dataMax + 10']}
          />
          <Tooltip
            contentStyle={{ background: 'var(--bg-card2)', border: '1px solid var(--border)', borderRadius: 8 }}
            formatter={(v) => [paceLabel(v) + ' /km', 'Tempo']}
          />
          <ReferenceLine y={avg} stroke="var(--text-3)" strokeDasharray="4 2" />
          <Line
            type="monotone" dataKey="avg_pace_s_per_km"
            stroke="var(--accent)" strokeWidth={2} dot={{ fill: 'var(--accent)', r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
