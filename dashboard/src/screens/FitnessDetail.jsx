import { useState, useEffect } from 'react'
import { api } from '../api'
import Card from '../ui/Card'
import Sparkline from '../ui/Sparkline'
import CoachNote from '../ui/CoachNote'
import { paceStr } from '../format'

export default function FitnessDetail({ athleteId, onBack }) {
  const [f, setF] = useState(null)
  useEffect(() => { api.fitness(athleteId).then(setF).catch(() => setF(null)) }, [athleteId])
  return (
    <div>
      <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--muted)', fontSize: 13, fontWeight: 500, marginBottom: 14 }}>‹ terug</button>
      <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Waar sta ik</h2>
      {!f ? <p style={{ color: 'var(--faint)' }}>Laden…</p> : (
        <>
          <Card>
            <p style={{ fontSize: 12, color: 'var(--muted)' }}>VO₂max</p>
            <p className="tnum" style={{ fontSize: 40, fontWeight: 500 }}>{f.vo2max_trend.at(-1)?.vo2max ?? '–'}</p>
            <Sparkline vals={f.vo2max_trend.map(x => x.vo2max)} />
          </Card>
          <div style={{ display: 'flex', gap: 12 }}>
            <Card style={{ flex: 1 }}>
              <p style={{ fontSize: 12, color: 'var(--muted)' }}>Tempo bij vaste HR</p>
              <p className="tnum" style={{ fontSize: 22, fontWeight: 500 }}>{paceStr(f.pace_at_hr.at(-1)?.pace_s_per_km)}</p>
              <p style={{ fontSize: 11, color: 'var(--faint)', marginTop: 4 }}>aerobe efficiëntie</p>
            </Card>
            <Card style={{ flex: 1 }}>
              <p style={{ fontSize: 12, color: 'var(--muted)' }}>Rust-HR</p>
              <p className="tnum" style={{ fontSize: 22, fontWeight: 500 }}>{f.resting_hr_trend.at(-1)?.resting_hr ?? '–'} <span style={{ fontSize: 11, color: 'var(--faint)' }}>bpm</span></p>
              <Sparkline vals={f.resting_hr_trend.map(x => x.resting_hr)} color="var(--z1)" />
            </Card>
          </div>
          {f.duiding ? <CoachNote>{f.duiding}</CoachNote> : null}
        </>
      )}
    </div>
  )
}
