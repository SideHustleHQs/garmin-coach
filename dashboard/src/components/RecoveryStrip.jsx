export default function RecoveryStrip({ data }) {
  const rows = [...(data.recovery || [])].reverse()

  return (
    <div className="card">
      <div className="label" style={{ marginBottom: 12 }}>Herstel (body battery)</div>
      {rows.length === 0 ? (
        <div className="no-data">Geen hersteldata — horloge draagt ze alleen tijdens runs</div>
      ) : (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {rows.map(r => {
            const hasData = r.body_battery_charged != null || r.body_battery_drained != null
            return (
              <div key={r.date} className="card" style={{
                flex: '1 1 120px', minWidth: 100, background: 'var(--bg-card2)',
                textAlign: 'center', padding: 12,
              }}>
                <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 4 }}>{r.date}</div>
                {hasData ? (
                  <>
                    <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--green)' }}>
                      +{r.body_battery_charged?.toFixed(0) ?? '?'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--red)' }}>
                      −{r.body_battery_drained?.toFixed(0) ?? '?'}
                    </div>
                    {r.hr_min && (
                      <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 4 }}>
                        HR {r.hr_min}–{r.hr_max}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="no-data" style={{ fontSize: 12 }}>geen data</div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
