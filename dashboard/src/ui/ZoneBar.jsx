const C = ['var(--z1)', 'var(--z2)', 'var(--z3)', 'var(--z4)', 'var(--z5)']
export default function ZoneBar({ zones, height = 8 }) {
  const vals = [zones?.z1, zones?.z2, zones?.z3, zones?.z4, zones?.z5].map(v => v || 0)
  const total = vals.reduce((a, b) => a + b, 0) || 1
  return (
    <div style={{ display: 'flex', height, borderRadius: 5, overflow: 'hidden' }}>
      {vals.map((v, i) => <div key={i} style={{ width: `${(v / total) * 100}%`, background: C[i] }} />)}
    </div>
  )
}
