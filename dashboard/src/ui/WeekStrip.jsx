const ICON = { run: '🏃', strength: '🏋', hyrox: '⚡', rest: '·', race: '🏁' }
const RUNC = { easy: 'var(--z2)', quality: 'var(--accent)', long: 'var(--z4)', race: 'var(--hard)' }
const NL = ['MA', 'DI', 'WO', 'DO', 'VR', 'ZA', 'ZO']

export default function WeekStrip({ days, selectedDate, onSelect }) {
  return (
    <div style={{ display: 'flex', gap: 5, marginBottom: 14 }}>
      {days.map((d, i) => {
        const on = d.date === selectedDate
        const color = d.day_type === 'run' ? (RUNC[d.run_type] || 'var(--z2)') : 'var(--faint)'
        return (
          <button key={d.date} onClick={() => onSelect(d.date)} aria-label={`${NL[i]} ${d.title}`}
            style={{ flex: 1, textAlign: 'center', background: on ? 'var(--accent)' : 'var(--card)',
              border: '1px solid var(--line)', borderRadius: 10, padding: '8px 0', cursor: 'pointer' }}>
            <p style={{ fontSize: 10, fontWeight: 600, margin: 0, color: on ? '#0F1319' : 'var(--faint)' }}>{NL[i]}</p>
            <span style={{ fontSize: 14, color: on ? '#0F1319' : color }}>{ICON[d.day_type] || '·'}</span>
          </button>
        )
      })}
    </div>
  )
}
