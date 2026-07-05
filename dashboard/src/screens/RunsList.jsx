import { useState, useEffect } from 'react'
import { api } from '../api'
import Card from '../ui/Card'
import { paceStr, kmStr } from '../format'

export default function RunsList({ athleteId, onOpenRun }) {
  const [runs, setRuns] = useState(null)
  useEffect(() => { api.runs(athleteId).then(setRuns).catch(() => setRuns([])) }, [athleteId])
  if (!runs) return <p style={{ color: 'var(--faint)' }}>Laden…</p>
  return (
    <div>
      <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Runs</h2>
      <Card style={{ padding: '4px 14px' }}>
        {runs.map(r => (
          <div key={r.activity_id} onClick={() => onOpenRun(r.activity_id)}
            style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 4px', borderBottom: '1px solid var(--line)', cursor: 'pointer' }}>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: 14, fontWeight: 600 }}>{r.name || 'Run'}</p>
              <p style={{ fontSize: 11.5, color: 'var(--faint)', marginTop: 2 }}>{r.date}</p>
            </div>
            <div className="tnum" style={{ textAlign: 'right', fontSize: 13, fontWeight: 600 }}>
              {kmStr(r.distance_km)} km<br /><span style={{ color: 'var(--faint)', fontWeight: 500, fontSize: 11 }}>{paceStr(r.avg_pace_s_per_km)} /km</span>
            </div>
          </div>
        ))}
      </Card>
    </div>
  )
}
