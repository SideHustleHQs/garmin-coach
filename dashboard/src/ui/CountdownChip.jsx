export default function CountdownChip({ weeks, label }) {
  if (weeks == null) return null
  return (
    <div style={{ textAlign: 'center', background: 'var(--ink)', color: 'var(--bg)', borderRadius: 14, padding: '7px 11px' }}>
      <p className="tnum" style={{ fontSize: 18, fontWeight: 500, lineHeight: 1 }}>{weeks}</p>
      <p style={{ fontSize: 9.5, marginTop: 3, opacity: .7, textTransform: 'uppercase', letterSpacing: '.08em' }}>{label}</p>
    </div>
  )
}
