function formatTime(s) {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60)
  return `${m}:${String(sec).padStart(2, '0')}`
}

function formatPace(s) {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60)
  return `${m}:${String(sec).padStart(2, '0')}/km`
}

function EffectLabel({ msg, label }) {
  if (!label) return <span style={{ color: 'var(--text-3)' }}>—</span>
  const short = label.replace(/_/g, ' ').toLowerCase()
  return (
    <span style={{ fontSize: 11, color: 'var(--accent2)', textTransform: 'capitalize' }}>
      {short}
    </span>
  )
}

export default function RecentRuns({ data }) {
  const runs = (data.runs || []).slice(0, 10)

  if (runs.length === 0) {
    return (
      <div className="card">
        <span className="label">Recente Runs</span>
        <p className="no-data">Geen runs gevonden</p>
      </div>
    )
  }

  return (
    <div className="card">
      <span className="label">Recente Runs</span>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }} aria-label="Recente hardloopactiviteiten">
          <thead>
            <tr style={{ color: 'var(--text-3)', fontSize: 11 }}>
              <th scope="col" style={{ textAlign: 'left',   padding: '4px 8px' }}>Datum</th>
              <th scope="col" style={{ textAlign: 'right',  padding: '4px 8px' }}>km</th>
              <th scope="col" style={{ textAlign: 'right',  padding: '4px 8px' }}>Pace</th>
              <th scope="col" style={{ textAlign: 'right',  padding: '4px 8px' }}>HR</th>
              <th scope="col" style={{ textAlign: 'right',  padding: '4px 8px' }}>AE</th>
              <th scope="col" style={{ textAlign: 'right',  padding: '4px 8px' }}>Load</th>
              <th scope="col" style={{ textAlign: 'right',  padding: '4px 8px' }}>BB</th>
              <th scope="col" style={{ textAlign: 'left',   padding: '4px 8px' }}>Effect</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r, i) => (
              <tr
                key={i}
                style={{
                  borderTop: '1px solid var(--border)',
                  background: i % 2 === 0 ? 'transparent' : 'var(--bg-card2)',
                }}
              >
                <td style={{ padding: '6px 8px', color: 'var(--text-2)' }}>{r.date}</td>
                <td style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--text-1)' }}>
                  {r.distance_km?.toFixed(1)}
                </td>
                <td style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--text-2)', fontVariantNumeric: 'tabular-nums' }}>
                  {formatPace(r.avg_pace_s_per_km)}
                </td>
                <td style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--text-2)' }}>
                  {r.avg_hr ? Math.round(r.avg_hr) : '—'}
                </td>
                <td style={{ padding: '6px 8px', textAlign: 'right', color: r.aerobic_effect >= 3 ? 'var(--green)' : 'var(--text-2)' }}>
                  {r.aerobic_effect?.toFixed(1) ?? '—'}
                </td>
                <td style={{ padding: '6px 8px', textAlign: 'right', color: 'var(--text-2)' }}>
                  {r.training_load ? Math.round(r.training_load) : '—'}
                </td>
                <td style={{ padding: '6px 8px', textAlign: 'right', color: r.bb_cost < -20 ? 'var(--orange)' : 'var(--text-2)' }}>
                  {r.bb_cost != null ? r.bb_cost : '—'}
                </td>
                <td style={{ padding: '6px 8px' }}>
                  <EffectLabel label={r.training_effect_label} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
