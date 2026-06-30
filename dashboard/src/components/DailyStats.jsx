import { ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'

export default function DailyStats({ data }) {
  const rows = [...(data.daily || [])].reverse()
  if (rows.length === 0) return (
    <div className="card"><div className="label">Stappen & calorieën</div><div className="no-data">Geen data</div></div>
  )

  return (
    <div className="card">
      <div className="label" style={{ marginBottom: 12 }}>Dagelijkse stappen & actieve calorieën</div>
      <ResponsiveContainer width="100%" height={200}>
        <ComposedChart data={rows} margin={{ top: 4, right: 8, bottom: 4, left: -16 }}>
          <XAxis dataKey="date" tick={{ fill: 'var(--text-3)', fontSize: 11 }} />
          <YAxis yAxisId="steps" tick={{ fill: 'var(--text-3)', fontSize: 11 }} />
          <YAxis yAxisId="cal" orientation="right" tick={{ fill: 'var(--text-3)', fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: 'var(--bg-card2)', border: '1px solid var(--border)', borderRadius: 8 }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-2)' }} />
          <Bar yAxisId="steps" dataKey="steps" name="Stappen" fill="var(--accent)" opacity={0.7} radius={[3,3,0,0]} />
          <Line yAxisId="cal" type="monotone" dataKey="active_calories" name="Act. kcal"
            stroke="var(--orange)" strokeWidth={2} dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
