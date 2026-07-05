export default function AthleteSwitcher({ athletes, current, onSwitch }) {
  return (
    <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
      {athletes.map(a => (
        <button key={a.id} onClick={() => onSwitch(a.id)}
          style={{ border: '1px solid var(--line)', borderRadius: 20, padding: '5px 13px', fontSize: 12.5, fontWeight: 500,
            background: current === a.id ? 'var(--ink)' : 'var(--card)',
            color: current === a.id ? 'var(--bg)' : 'var(--muted)' }}>
          {a.display_name}
        </button>
      ))}
    </div>
  )
}
