function AcwrGauge({ acwr }) {
  const ratio = acwr ?? 0
  const clamped = Math.min(Math.max(ratio, 0), 2)
  // Map 0-2 ratio to -90° to +90° (half circle, left to right)
  const angle = (clamped / 2) * 180 - 90
  const rad = (angle * Math.PI) / 180
  const r = 60
  const cx = 80
  const cy = 80
  const nx = cx + r * Math.cos(rad)
  const ny = cy + r * Math.sin(rad)

  const zoneColor =
    ratio > 1.5 ? 'var(--red)'
    : ratio > 1.3 ? 'var(--orange)'
    : ratio >= 0.8 ? 'var(--green)'
    : 'var(--accent2)'

  // Zone arcs: angles are in degrees from center, mapped to SVG
  // Full arc is -180 to 0 (top half of circle, going left to right)
  const zones = [
    { startDeg: -180, endDeg: -108, color: 'var(--accent2)' }, // 0.0–0.8 underload
    { startDeg: -108, endDeg:   27, color: 'var(--green)' },   // 0.8–1.3 optimal
    { startDeg:   27, endDeg:   54, color: 'var(--orange)' },  // 1.3–1.5 high
    { startDeg:   54, endDeg:   90, color: 'var(--red)' },     // 1.5–2.0 overload
  ]

  function arcPath(startDeg, endDeg) {
    const r1 = (startDeg * Math.PI) / 180
    const r2 = (endDeg * Math.PI) / 180
    const x1 = cx + r * Math.cos(r1)
    const y1 = cy + r * Math.sin(r1)
    const x2 = cx + r * Math.cos(r2)
    const y2 = cy + r * Math.sin(r2)
    const large = Math.abs(endDeg - startDeg) > 90 ? 1 : 0
    return `M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${large},1 ${x2},${y2} Z`
  }

  return (
    <svg width={160} height={100} viewBox="0 0 160 100" role="img" aria-label={`ACWR gauge: ${ratio.toFixed(2)}`}>
      {zones.map((z, i) => (
        <path key={i} d={arcPath(z.startDeg, z.endDeg)} fill={z.color} opacity={0.25} />
      ))}
      <line
        x1={cx} y1={cy}
        x2={Math.round(nx)} y2={Math.round(ny)}
        stroke={zoneColor} strokeWidth={3} strokeLinecap="round"
      />
      <circle cx={cx} cy={cy} r={5} fill={zoneColor} />
      <text x={cx} y={cy - 14} textAnchor="middle" fill="var(--text-1)" fontSize={15} fontWeight={700}>
        {ratio.toFixed(2)}
      </text>
      <text x={cx} y={cy - 2} textAnchor="middle" fill="var(--text-3)" fontSize={9}>
        ACWR
      </text>
    </svg>
  )
}

const ZONE_LABELS = {
  aerobic_low:  'Aëroob Laag (Z1/Z2)',
  aerobic_high: 'Aëroob Hoog (Z3/Z4)',
  anaerobic:    'Anaëroob (Z5)',
}

export default function TrainingLoad({ data }) {
  const tl = data.trainingLoad || {}
  const latest = tl.latest
  const balance = tl.balance

  if (!latest) {
    return (
      <div className="card">
        <span className="label">Training Load</span>
        <p className="no-data">Geen training load data</p>
      </div>
    )
  }

  const barData = balance
    ? Object.entries(ZONE_LABELS).map(([key, label]) => {
        const z = balance[key] || {}
        const actual = Math.round(z.actual ?? 0)
        const tmin = z.target_min ?? 0
        const tmax = z.target_max ?? 0
        const inTarget = actual >= tmin && actual <= tmax
        return { key, label, actual, tmin, tmax, inTarget }
      })
    : []

  return (
    <div className="card">
      <span className="label">Training Load</span>
      <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* Left: ACWR gauge */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
          <AcwrGauge acwr={latest.acwr} />
          <span style={{ fontSize: 11, color: 'var(--text-3)' }}>
            Status:{' '}
            <span style={{ color: latest.acwr >= 0.8 && latest.acwr <= 1.3 ? 'var(--green)' : 'var(--orange)' }}>
              {latest.acwr_status || '—'}
            </span>
          </span>
          <span style={{ fontSize: 11, color: 'var(--text-3)' }}>
            Acuut {Math.round(latest.acute_load ?? 0)} / Chronisch {Math.round(latest.chronic_load ?? 0)}
          </span>
        </div>

        {/* Right: monthly balance bars */}
        <div style={{ flex: 1, minWidth: 220 }}>
          <span style={{ fontSize: 12, color: 'var(--text-2)', display: 'block', marginBottom: 8 }}>
            Maandelijks trainingsbalans
          </span>
          {barData.map((d) => {
            const pct = d.tmax > 0 ? Math.min((d.actual / d.tmax) * 100, 130) : 0
            const targetPct = d.tmax > 0 ? (d.tmin / d.tmax) * 100 : 0
            return (
              <div key={d.key} style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-3)', marginBottom: 3 }}>
                  <span>{d.label}</span>
                  <span style={{ color: d.inTarget ? 'var(--green)' : 'var(--orange)' }}>
                    {d.actual} / {d.tmin}–{d.tmax}
                  </span>
                </div>
                <div style={{ height: 8, background: 'var(--bg-card2)', borderRadius: 4, position: 'relative', overflow: 'hidden' }}>
                  <div style={{
                    position: 'absolute', left: 0, top: 0, bottom: 0,
                    width: `${pct}%`,
                    background: d.inTarget ? 'var(--green)' : 'var(--orange)',
                    borderRadius: 4,
                  }} />
                  {d.tmin > 0 && (
                    <div style={{
                      position: 'absolute', left: `${targetPct}%`, top: 0, bottom: 0,
                      width: 2, background: 'var(--text-3)', opacity: 0.5,
                    }} />
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
