import Sparkline from './Sparkline'

export default function StatTile({ label, value, unit, trendVals, trendColor = 'var(--z2)', trendDir, onClick, children }) {
  return (
    <div onClick={onClick} style={{ background: 'var(--card)', border: '1px solid var(--line)',
      borderRadius: 13, padding: 11, cursor: onClick ? 'pointer' : 'default' }}>
      <p style={{ fontSize: 10.5, color: 'var(--faint)', textTransform: 'uppercase', letterSpacing: '.04em', margin: 0 }}>{label}</p>
      <p className="tnum" style={{ fontSize: 19, fontWeight: 500, margin: '3px 0 0' }}>
        {value ?? '–'}{unit ? <span style={{ fontSize: 10.5, color: 'var(--faint)', fontWeight: 500 }}> {unit}</span> : null}
        {trendDir ? <span style={{ fontSize: 11, color: trendDir === 'up' ? 'var(--good)' : 'var(--hard)' }}> {trendDir === 'up' ? '↑' : '↓'}</span> : null}
      </p>
      {trendVals && trendVals.filter(v => v != null).length >= 2 ? <Sparkline vals={trendVals} color={trendColor} height={22} /> : null}
      {children}
    </div>
  )
}
