export default function CoachCard() {
  return (
    <div className="card" style={{ borderLeft: '4px solid var(--accent)', opacity: 0.85 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div className="label">AI Coach</div>
        <span style={{
          fontSize: 10, padding: '2px 8px', borderRadius: 12,
          background: 'var(--bg-card2)', color: 'var(--text-3)',
          border: '1px solid var(--border)',
        }}>
          Automatisch in fase 2
        </span>
      </div>
      <div style={{ color: 'var(--text-2)', fontSize: 14, lineHeight: 1.6 }}>
        <p>
          Je bouwt nu een solide base op voor de Dam tot Damloop. Focus op zone 2-runs
          en houd het weekvolume rustig oplopend.
        </p>
        <p style={{ marginTop: 8, color: 'var(--text-3)', fontSize: 13 }}>
          In fase 2 analyseert de coach automatisch je data en schrijft hier elke week
          een persoonlijk trainingsadvies.
        </p>
      </div>
    </div>
  )
}
