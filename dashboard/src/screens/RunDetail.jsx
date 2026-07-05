import { useState, useEffect } from 'react'
import { api } from '../api'
import Card from '../ui/Card'
import SplitsBar from '../ui/SplitsBar'
import ZoneBar from '../ui/ZoneBar'
import MetricStat from '../ui/MetricStat'
import { paceStr, durationStr, kmStr } from '../format'

export default function RunDetail({ athleteId, runId, onBack }) {
  const [run, setRun] = useState(null)
  const [splits, setSplits] = useState([])
  const [eff, setEff] = useState(null)
  const [err, setErr] = useState(false)

  useEffect(() => {
    setRun(null); setErr(false)
    Promise.all([api.runs(athleteId), api.splits(athleteId, runId), api.runEfficiency(athleteId)])
      .then(([runs, sp, effs]) => {
        setRun(runs.find(r => r.activity_id === runId) || null)
        setSplits(sp)
        setEff((effs || []).find(e => e.activity_id === runId) || null)
      }).catch(() => setErr(true))
  }, [athleteId, runId])

  return (
    <div>
      <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--muted)', fontSize: 13, fontWeight: 500, marginBottom: 14 }}>‹ terug</button>
      {err ? <p style={{ color: 'var(--hard)' }}>Kon data niet laden.</p> : !run ? <p style={{ color: 'var(--faint)' }}>Laden…</p> : (
        <>
          <h2 style={{ fontSize: 16, fontWeight: 600 }}>{run.name || 'Run'}</h2>
          <p style={{ fontSize: 12, color: 'var(--faint)', margin: '2px 0 14px' }}>{run.date}</p>
          <Card>
            <div style={{ display: 'flex', gap: 8 }}>
              <MetricStat label="Afstand" value={kmStr(run.distance_km)} unit="km" />
              <MetricStat label="Tijd" value={durationStr(run.duration_s)} />
              <MetricStat label="Pace" value={paceStr(run.avg_pace_s_per_km)} />
              <MetricStat label="Ø HR" value={run.avg_hr ?? '–'} />
            </div>
          </Card>
          {splits.length > 0 && <Card><h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Splits per km</h3><SplitsBar splits={splits} /></Card>}
          <Card>
            <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Tijd in HR-zones</h3>
            <ZoneBar zones={run.zones} height={10} />
          </Card>
          {eff && (
            <Card>
              <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Loopdynamiek</h3>
              <div style={{ display: 'flex', gap: 8 }}>
                <MetricStat label="Cadans" value={eff.cadence_spm ?? '–'} />
                <MetricStat label="Grondcontact" value={eff.gct_ms ?? '–'} unit="ms" />
                <MetricStat label="Vert. osc." value={eff.vert_osc_mm ?? '–'} unit="mm" />
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
