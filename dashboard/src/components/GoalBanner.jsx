const RACE_DATE = new Date('2026-09-20T00:00:00')

const PHASES = [
  { name: 'Basis',  start: new Date('2026-06-30'), end: new Date('2026-08-10'), color: '#3b82f6' },
  { name: 'Opbouw', start: new Date('2026-08-11'), end: new Date('2026-09-07'), color: '#22c55e' },
  { name: 'Piek',   start: new Date('2026-09-08'), end: new Date('2026-09-13'), color: '#f97316' },
  { name: 'Taper',  start: new Date('2026-09-14'), end: new Date('2026-09-19'), color: '#a78bfa' },
  { name: 'Race',   start: new Date('2026-09-20'), end: new Date('2026-09-20'), color: '#ef4444' },
]

function getCurrentPhase() {
  const now = new Date()
  return PHASES.find(p => now >= p.start && now <= p.end) || PHASES[0]
}

function daysUntilRace() {
  const now = new Date()
  const diff = RACE_DATE - now
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)))
}

export default function GoalBanner() {
  const days = daysUntilRace()
  const currentPhase = getCurrentPhase()
  const totalDays = (RACE_DATE - PHASES[0].start) / (1000 * 60 * 60 * 24)
  const elapsed = (new Date() - PHASES[0].start) / (1000 * 60 * 60 * 24)
  const progress = Math.min(100, Math.max(0, (elapsed / totalDays) * 100))

  return (
    <div className="card" style={{ borderLeft: `4px solid ${currentPhase.color}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div className="label">Doel</div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>Dam tot Damloop — 20 sep 2026 · 16,1 km</div>
          <div style={{ marginTop: 4, color: 'var(--text-2)' }}>
            Fase: <span style={{ color: currentPhase.color, fontWeight: 600 }}>{currentPhase.name}</span>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 40, fontWeight: 800, color: currentPhase.color, lineHeight: 1 }}>{days}</div>
          <div className="label">dagen te gaan</div>
        </div>
      </div>
      <div style={{ marginTop: 16 }}>
        <div style={{ height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${progress}%`, background: currentPhase.color, borderRadius: 3, transition: 'width .3s' }} />
        </div>
      </div>
      <div style={{ display: 'flex', gap: 4, marginTop: 12 }}>
        {PHASES.map(p => (
          <div key={p.name} style={{
            flex: p.name === 'Race' ? '0 0 auto' : 1,
            padding: '4px 8px', borderRadius: 6, textAlign: 'center', fontSize: 11,
            background: p.name === currentPhase.name ? p.color : 'var(--bg-card2)',
            color: p.name === currentPhase.name ? '#fff' : 'var(--text-3)',
            fontWeight: p.name === currentPhase.name ? 700 : 400,
          }}>
            {p.name}
          </div>
        ))}
      </div>
    </div>
  )
}
