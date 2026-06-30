function fmtPace(s) {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60).toString().padStart(2, '0')
  return `${m}:${sec}`
}

export default function SplitsPanel({ data }) {
  const splits = data.splits || []

  if (splits.length === 0) {
    return (
      <div className="card">
        <span className="label">Splits (laatste run)</span>
        <p className="no-data">Geen splits beschikbaar</p>
      </div>
    )
  }

  const paces = splits.map(s => s.pace_s_per_km).filter(Boolean)
  const minPace = paces.length ? Math.min(...paces) : null
  const maxPace = paces.length ? Math.max(...paces) : null

  return (
    <div className="card">
      <span className="label">Splits (laatste run)</span>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ color: 'var(--text-3)', fontSize: 11 }}>
            <th style={{ textAlign: 'left', paddingBottom: 6, fontWeight: 500 }}>km</th>
            <th style={{ textAlign: 'right', paddingBottom: 6, fontWeight: 500 }}>afstand</th>
            <th style={{ textAlign: 'right', paddingBottom: 6, fontWeight: 500 }}>pace</th>
            <th style={{ textAlign: 'right', paddingBottom: 6, fontWeight: 500 }}>HR</th>
          </tr>
        </thead>
        <tbody>
          {splits.map((s) => {
            const isFast = s.pace_s_per_km && s.pace_s_per_km === minPace
            const isSlow = s.pace_s_per_km && s.pace_s_per_km === maxPace && paces.length > 1
            const paceColor = isFast ? 'var(--green)' : isSlow ? 'var(--orange)' : 'var(--text-1)'
            return (
              <tr key={s.split_num} style={{ borderTop: '1px solid var(--border)' }}>
                <td style={{ padding: '5px 0', color: 'var(--text-2)' }}>{s.split_num}</td>
                <td style={{ textAlign: 'right', color: 'var(--text-3)' }}>
                  {s.distance_m ? `${(s.distance_m / 1000).toFixed(2)} km` : '—'}
                </td>
                <td style={{ textAlign: 'right', color: paceColor, fontVariantNumeric: 'tabular-nums' }}>
                  {fmtPace(s.pace_s_per_km)}
                </td>
                <td style={{ textAlign: 'right', color: 'var(--text-2)' }}>
                  {s.avg_hr ? `${Math.round(s.avg_hr)}` : '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
