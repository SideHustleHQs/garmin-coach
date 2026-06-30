function formatTime(seconds) {
  if (!seconds) return '--:--:--'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  return h > 0
    ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    : `${m}:${String(s).padStart(2, '0')}`
}

function formatPace(secsPerKm) {
  if (!secsPerKm) return '--'
  const m = Math.floor(secsPerKm / 60)
  const s = Math.floor(secsPerKm % 60)
  return `${m}:${String(s).padStart(2, '0')} /km`
}

function ReadinessRing({ score }) {
  const pct = (score || 0) / 100
  const r = 40
  const circ = 2 * Math.PI * r
  const dash = circ * pct
  const color = score >= 70 ? '#22c55e' : score >= 40 ? '#f97316' : '#ef4444'

  return (
    <svg width={100} height={100} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={50} cy={50} r={r} fill="none" stroke="var(--border)" strokeWidth={8} />
      <circle
        cx={50} cy={50} r={r} fill="none"
        stroke={color} strokeWidth={8}
        strokeDasharray={`${dash} ${circ}`}
        strokeLinecap="round"
      />
      <text
        x={50} y={55} textAnchor="middle"
        style={{ fontSize: 20, fontWeight: 700, fill: color, transform: 'rotate(90deg)', transformOrigin: '50px 50px' }}
      >
        {score ?? '--'}
      </text>
    </svg>
  )
}

export default function HeroRow({ data }) {
  const { hero } = data
  if (!hero) return null

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
      <div className="card" style={{ textAlign: 'center' }}>
        <div className="label">Voorspelde 16,1 km tijd</div>
        <div style={{ fontSize: 36, fontWeight: 800, color: 'var(--accent)', lineHeight: 1.1, marginTop: 8 }}>
          {formatTime(hero.predicted_16k_time_s)}
        </div>
        <div style={{ color: 'var(--text-2)', marginTop: 4, fontSize: 13 }}>
          {formatPace(hero.predicted_16k_pace_s_per_km)}
        </div>
        {!hero.predicted_16k_time_s && (
          <div className="no-data" style={{ marginTop: 8 }}>Meer runs nodig</div>
        )}
      </div>

      <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <div className="label">Training Readiness</div>
        <ReadinessRing score={hero.latest_readiness?.score} />
        <div style={{ color: 'var(--text-2)', fontSize: 12, marginTop: 4 }}>
          {hero.latest_readiness?.level?.replace(/_/g, ' ') ?? 'Geen data'}
        </div>
      </div>

      <div className="card" style={{ textAlign: 'center' }}>
        <div className="label">VO₂max</div>
        <div style={{ fontSize: 48, fontWeight: 800, color: 'var(--accent2)', lineHeight: 1, marginTop: 8 }}>
          {hero.latest_vo2max?.value ?? '--'}
        </div>
        <div style={{ color: 'var(--text-2)', fontSize: 12, marginTop: 4 }}>
          {hero.latest_vo2max?.date ? `Gemeten ${hero.latest_vo2max.date}` : 'Geen data'}
        </div>
      </div>
    </div>
  )
}
