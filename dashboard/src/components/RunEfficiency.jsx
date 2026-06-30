import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

const METRICS = [
  { key: 'cadence_spm',   label: 'Cadans',             unit: 'spm',  color: 'var(--accent)',  target: 180 },
  { key: 'gct_ms',        label: 'Grondcontact',        unit: 'ms',   color: 'var(--accent2)', target: null },
  { key: 'vert_osc_mm',   label: 'Vert. oscillatie',    unit: 'mm',   color: 'var(--green)',   target: null },
]

function MiniChart({ data, metric }) {
  const filtered = data.filter(d => d[metric.key] != null)
  if (filtered.length < 2) {
    return <p className="no-data" style={{ fontSize: 11 }}>Geen data</p>
  }

  const formatted = filtered.map(d => ({
    ...d,
    dateShort: d.date?.slice(5) ?? '',
  }))

  return (
    <ResponsiveContainer width="100%" height={80}>
      <LineChart data={formatted} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
        <XAxis dataKey="dateShort" tick={{ fontSize: 9, fill: 'var(--text-3)' }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 9, fill: 'var(--text-3)' }} tickLine={false} axisLine={false} width={40} />
        <Tooltip
          contentStyle={{ background: 'var(--bg-card2)', border: '1px solid var(--border)', fontSize: 11 }}
          formatter={(v) => [`${v} ${metric.unit}`, metric.label]}
          labelStyle={{ color: 'var(--text-3)' }}
        />
        <Line
          type="monotone" dataKey={metric.key}
          stroke={metric.color} strokeWidth={2} dot={false}
          connectNulls={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

export default function RunEfficiency({ data }) {
  const efficiency = data.runEfficiency || []

  if (efficiency.length === 0) {
    return (
      <div className="card">
        <span className="label">Loopefficiëntie</span>
        <p className="no-data">Geen efficiëntiedata beschikbaar</p>
      </div>
    )
  }

  return (
    <div className="card">
      <span className="label">Loopefficiëntie</span>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
        {METRICS.map(m => (
          <div key={m.key}>
            <span style={{ fontSize: 11, color: 'var(--text-2)', display: 'block', marginBottom: 4 }}>
              {m.label}
              {m.target && (
                <span style={{ color: 'var(--text-3)', marginLeft: 6 }}>doel: {m.target} {m.unit}</span>
              )}
            </span>
            <MiniChart data={efficiency} metric={m} />
          </div>
        ))}
      </div>
    </div>
  )
}
