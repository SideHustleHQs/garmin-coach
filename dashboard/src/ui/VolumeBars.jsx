export default function VolumeBars({ vals, height = 30 }) {
  const max = Math.max(...(vals || [1]), 1)
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height, marginTop: 6 }}>
      {(vals || []).map((v, i) => (
        <div key={i} style={{ flex: 1, height: `${Math.round((v / max) * 100)}%`,
          background: i === vals.length - 1 ? 'var(--accent)' : 'var(--line)', borderRadius: 3 }} />
      ))}
    </div>
  )
}
