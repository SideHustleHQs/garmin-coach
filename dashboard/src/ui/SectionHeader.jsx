export default function SectionHeader({ children }) {
  return <p style={{ fontSize: 11, color: 'var(--faint)', textTransform: 'uppercase',
    letterSpacing: '.08em', fontWeight: 600, margin: '16px 2px 8px' }}>{children}</p>
}
