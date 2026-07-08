export default function SectionHeader({ children, color }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      margin: '18px 0 10px',
    }}>
      {color && <div style={{ width: 3, height: 16, borderRadius: 2, background: color }} />}
      <p style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase',
        letterSpacing: '.08em', color: color || 'var(--muted)', margin: 0 }}>{children}</p>
    </div>
  )
}
