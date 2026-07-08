export default function MetricStat({ label, value, unit, color }) {
  return (
    <div style={{ flex: 1, background: 'var(--line)', borderRadius: 8, padding: '8px 10px' }}>
      <p style={{ fontSize: 10, color: 'var(--faint)', textTransform: 'uppercase', marginBottom: 2 }}>{label}</p>
      <p className="tnum" style={{ fontSize: 15, fontWeight: 700, color: color || 'var(--ink)' }}>
        {value ?? '–'}{unit ? <span style={{ fontSize: 11, color: 'var(--faint)' }}> {unit}</span> : null}
      </p>
    </div>
  )
}
