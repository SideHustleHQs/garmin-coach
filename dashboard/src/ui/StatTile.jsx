import Sparkline from './Sparkline'

export default function StatTile({ label, value, unit, trendVals, trendColor, trendDir, onClick, children, accentColor }) {
  const top = accentColor ? `3px solid ${accentColor}` : '3px solid var(--line)'
  return (
    <div onClick={onClick} style={{
      background: 'var(--card)', borderRadius: 13, padding: '10px 11px',
      cursor: onClick ? 'pointer' : 'default',
      borderTop: top,
    }}>
      <p style={{ fontSize: 10, color: 'var(--faint)', textTransform: 'uppercase', letterSpacing: '.04em', margin: 0 }}>{label}</p>
      <p className="tnum" style={{ fontSize: 22, fontWeight: 800, margin: '4px 0 0', lineHeight: 1.1 }}>
        {value ?? '–'}
        {unit ? <span style={{ fontSize: 11, color: 'var(--faint)', fontWeight: 500 }}> {unit}</span> : null}
        {trendDir ? <span style={{ fontSize: 12, color: trendDir === 'up' ? 'var(--green)' : 'var(--red)' }}> {trendDir === 'up' ? '↑' : '↓'}</span> : null}
      </p>
      {trendVals && trendVals.filter(v => v != null).length >= 2
        ? <Sparkline vals={trendVals} color={trendColor || accentColor || 'var(--green)'} height={22} />
        : null}
      {children}
    </div>
  )
}
