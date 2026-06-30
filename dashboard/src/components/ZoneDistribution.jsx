import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const ZONE_LABELS = ['Z1 Herstel', 'Z2 Aerob', 'Z3 Tempo', 'Z4 Drempel', 'Z5 Max']
const ZONE_COLORS = ['var(--z1)', 'var(--z2)', 'var(--z3)', 'var(--z4)', 'var(--z5)']

function toMinutes(s) { return Math.round((s || 0) / 60) }

export default function ZoneDistribution({ data }) {
  const z = data.zones || {}
  const entries = [
    { name: ZONE_LABELS[0], value: toMinutes(z.z1) },
    { name: ZONE_LABELS[1], value: toMinutes(z.z2) },
    { name: ZONE_LABELS[2], value: toMinutes(z.z3) },
    { name: ZONE_LABELS[3], value: toMinutes(z.z4) },
    { name: ZONE_LABELS[4], value: toMinutes(z.z5) },
  ].filter(e => e.value > 0)

  const total = entries.reduce((a, e) => a + e.value, 0)
  const easyPct = total > 0 ? Math.round(((toMinutes(z.z1) + toMinutes(z.z2)) / total) * 100) : 0

  if (total === 0) return (
    <div className="card"><div className="label">Intensiteitsverdeling (hartslagzones)</div><div className="no-data">Geen data</div></div>
  )

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div className="label">Intensiteitsverdeling (hartslagzones)</div>
        <div style={{ fontSize: 12, color: easyPct >= 80 ? 'var(--green)' : 'var(--orange)' }}>
          {easyPct}% laag · doel: 80%
        </div>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie data={entries} cx="50%" cy="50%" outerRadius={80} dataKey="value">
            {entries.map((_, i) => <Cell key={i} fill={ZONE_COLORS[i]} />)}
          </Pie>
          <Tooltip
            contentStyle={{ background: 'var(--bg-card2)', border: '1px solid var(--border)', borderRadius: 8 }}
            formatter={(v, name) => [`${v} min`, name]}
          />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12, color: 'var(--text-2)' }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
