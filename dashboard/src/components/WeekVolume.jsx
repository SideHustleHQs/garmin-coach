import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

export default function WeekVolume({ data }) {
  const rows = data.weekVol || []
  if (rows.length === 0) return (
    <div className="card"><div className="label">Weekvolume (km)</div><div className="no-data">Geen data</div></div>
  )
  const max = Math.max(...rows.map(r => r.km))

  return (
    <div className="card">
      <div className="label" style={{ marginBottom: 12 }}>Weekvolume (km)</div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={rows} margin={{ top: 4, right: 8, bottom: 4, left: -16 }}>
          <XAxis dataKey="week" tick={{ fill: 'var(--text-3)', fontSize: 11 }} />
          <YAxis tick={{ fill: 'var(--text-3)', fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: 'var(--bg-card2)', border: '1px solid var(--border)', borderRadius: 8 }}
            labelStyle={{ color: 'var(--text-2)' }}
            formatter={v => [`${v.toFixed(1)} km`]}
          />
          <Bar dataKey="km" radius={[4, 4, 0, 0]}>
            {rows.map((r, i) => (
              <Cell key={i} fill={r.km === max ? 'var(--accent)' : 'var(--bg-card2)'} stroke="var(--border)" />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
