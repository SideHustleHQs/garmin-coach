function pace(secsPerKm) {
  if (!secsPerKm) return '--'
  const m = Math.floor(secsPerKm / 60)
  const s = Math.floor(secsPerKm % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function duration(s) {
  if (!s) return '--'
  const m = Math.floor(s / 60)
  return `${m} min`
}

export default function RecentRuns({ data }) {
  const runs = (data.runs || []).slice(0, 10)
  if (runs.length === 0) return (
    <div className="card"><div className="label">Recente runs</div><div className="no-data">Geen runs gevonden</div></div>
  )

  return (
    <div className="card">
      <div className="label" style={{ marginBottom: 12 }}>Recente runs</div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ color: 'var(--text-3)', borderBottom: '1px solid var(--border)' }}>
              {['Datum', 'Naam', 'Afstand', 'Duur', 'Tempo', 'Gem HR', 'Aerob.'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 500 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {runs.map((r, i) => (
              <tr key={i} style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-1)' }}>
                <td style={{ padding: '8px 8px', color: 'var(--text-2)' }}>{r.date}</td>
                <td style={{ padding: '8px 8px' }}>{r.name || '—'}</td>
                <td style={{ padding: '8px 8px' }}>{r.distance_km?.toFixed(1)} km</td>
                <td style={{ padding: '8px 8px' }}>{duration(r.duration_s)}</td>
                <td style={{ padding: '8px 8px', color: 'var(--accent)' }}>{pace(r.avg_pace_s_per_km)}</td>
                <td style={{ padding: '8px 8px' }}>{r.avg_hr ? `${Math.round(r.avg_hr)} bpm` : '—'}</td>
                <td style={{ padding: '8px 8px' }}>
                  {r.aerobic_effect != null
                    ? <span style={{ color: r.aerobic_effect >= 3 ? 'var(--green)' : 'var(--text-2)' }}>{r.aerobic_effect.toFixed(1)}</span>
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
