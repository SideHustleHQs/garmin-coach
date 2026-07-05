export default function CoachNote({ children, dark }) {
  return (
    <div style={{ background: dark ? 'var(--ink)' : 'var(--accent-t)', borderRadius: 'var(--radius)', padding: 12 }}>
      <p style={{ fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.07em',
        color: dark ? 'var(--accent)' : 'var(--accent-d)', marginBottom: 4 }}>Coach</p>
      <p style={{ fontSize: 12.5, lineHeight: 1.5, color: dark ? 'rgba(238,241,244,.86)' : 'var(--accent-d)' }}>{children}</p>
    </div>
  )
}
