export default function CoachNote({ children }) {
  if (!children) return null
  return (
    <div style={{
      background: 'var(--card)', border: '1px solid var(--green)',
      borderRadius: 10, padding: '8px 12px', marginTop: 10,
      fontSize: 13, color: 'var(--muted)', lineHeight: 1.45,
      fontStyle: 'italic',
    }}>
      <span style={{ color: 'var(--green)', fontStyle: 'normal', fontWeight: 700 }}>Coach · </span>
      {children}
    </div>
  )
}
