import { AlertTriangle, Info } from 'lucide-react'

export default function AttentionPoints({ data }) {
  const points = data.attentionPoints || []

  if (points.length === 0) {
    return null
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {points.map((p, i) => {
        const isWarning = p.level === 'warning'
        const color = isWarning ? 'var(--orange)' : 'var(--accent2)'
        const Icon = isWarning ? AlertTriangle : Info
        return (
          <div
            key={i}
            style={{
              background: 'var(--bg-card)',
              border: `1px solid var(--border)`,
              borderLeft: `4px solid ${color}`,
              borderRadius: 10,
              padding: '12px 16px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: 12,
            }}
          >
            <Icon size={18} color={color} style={{ flexShrink: 0, marginTop: 1 }} aria-hidden="true" />
            <span style={{ color: 'var(--text-1)', fontSize: 14, lineHeight: 1.5 }}>
              {p.message}
            </span>
          </div>
        )
      })}
    </div>
  )
}
