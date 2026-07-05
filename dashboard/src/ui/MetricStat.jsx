export default function MetricStat({ label, value, unit }) {
  return (
    <div style={{ background: 'var(--bg)', borderRadius: 'var(--radius)', padding: 10, flex: 1 }}>
      <p style={{ fontSize: 11, color: 'var(--faint)', textTransform: 'uppercase', letterSpacing: '.05em' }}>{label}</p>
      <p className="tnum" style={{ fontSize: 16, fontWeight: 500, marginTop: 3 }}>
        {value}{unit ? <span style={{ fontSize: 11, color: 'var(--faint)' }}> {unit}</span> : null}
      </p>
    </div>
  )
}
