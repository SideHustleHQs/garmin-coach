export default function Card({ children, onClick, style }) {
  return (
    <div onClick={onClick}
      style={{ background: 'var(--card)', border: '1px solid var(--line)',
        borderRadius: 'var(--radius-lg)', padding: 16, marginBottom: 12,
        cursor: onClick ? 'pointer' : 'default', ...style }}>
      {children}
    </div>
  )
}
