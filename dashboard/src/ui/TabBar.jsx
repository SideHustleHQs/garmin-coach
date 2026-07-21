const TABS = [['home', 'Vandaag'], ['runs', 'Runs'], ['schema', 'Schema'], ['coach', 'Coach'], ['delen', 'Delen']]
export default function TabBar({ current, onNav }) {
  const active = ['run', 'fitness', 'load'].includes(current) ? 'home' : current
  return (
    <div style={{ position: 'sticky', bottom: 0, display: 'flex', justifyContent: 'space-around',
      background: 'var(--card)', borderTop: '1px solid var(--line)', padding: '10px 6px 14px' }}>
      {TABS.map(([id, label]) => (
        <button key={id} onClick={() => onNav(id)} aria-label={label}
          style={{ background: 'none', border: 'none', color: active === id ? 'var(--accent)' : 'var(--faint)',
            fontSize: 11, fontWeight: 600 }}>{label}</button>
      ))}
    </div>
  )
}
