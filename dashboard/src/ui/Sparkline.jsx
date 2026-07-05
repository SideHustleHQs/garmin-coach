export default function Sparkline({ vals, color = 'var(--good)', height = 30 }) {
  const clean = (vals || []).filter(v => v != null)
  if (clean.length < 2) return null
  const w = 110, min = Math.min(...clean), max = Math.max(...clean), r = (max - min) || 1
  const pts = clean.map((v, i) => `${(i / (clean.length - 1) * w).toFixed(1)},${(height - 2 - (v - min) / r * (height - 6)).toFixed(1)}`).join(' ')
  const lx = w, ly = (height - 2 - (clean[clean.length - 1] - min) / r * (height - 6))
  return (
    <svg viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" style={{ width: '100%', height, display: 'block', marginTop: 6 }} aria-hidden="true">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={lx} cy={ly.toFixed(1)} r="2.6" fill={color} />
    </svg>
  )
}
