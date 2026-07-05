import { useState, useEffect } from 'react'
import { api } from '../api'
import Card from '../ui/Card'
import ReadinessHero from '../ui/ReadinessHero'
import Sparkline from '../ui/Sparkline'
import VolumeBars from '../ui/VolumeBars'
import ZoneBar from '../ui/ZoneBar'
import CoachNote from '../ui/CoachNote'
import { paceStr, kmStr } from '../format'

export default function Home({ athleteId, onOpenRun, onNav }) {
  const [home, setHome] = useState(null)
  const [vol, setVol] = useState([])
  const [vo2, setVo2] = useState([])
  const [err, setErr] = useState(false)

  useEffect(() => {
    setHome(null); setErr(false)
    Promise.all([api.home(athleteId), api.weeklyVolume(athleteId), api.vo2maxTrend(athleteId)])
      .then(([h, v, t]) => { setHome(h); setVol(v.slice().reverse().map(w => w.km)); setVo2(t.map(x => x.vo2max)) })
      .catch(() => setErr(true))
  }, [athleteId])

  if (err) return <p style={{ color: 'var(--hard)' }}>Kon data niet laden.</p>
  if (!home) return <p style={{ color: 'var(--faint)' }}>Laden…</p>

  const { readiness, fitness, load, last_run } = home
  return (
    <div>
      <ReadinessHero readiness={readiness} />
      <div style={{ display: 'flex', gap: 12 }}>
        <Card onClick={() => onNav('fitness')} style={{ flex: 1 }}>
          <p style={{ fontSize: 12, color: 'var(--muted)' }}>Waar sta ik</p>
          <p className="tnum" style={{ fontSize: 24, fontWeight: 500 }}>{fitness?.vo2max ?? '–'} <span style={{ fontSize: 11, color: 'var(--faint)' }}>VO₂max</span></p>
          <Sparkline vals={vo2} />
        </Card>
        <Card onClick={() => onNav('load')} style={{ flex: 1 }}>
          <p style={{ fontSize: 12, color: 'var(--muted)' }}>Belasting</p>
          <p className="tnum" style={{ fontSize: 24, fontWeight: 500 }}>{load?.acwr ?? '–'}</p>
          <VolumeBars vals={vol} />
        </Card>
      </div>
      {last_run && (
        <Card onClick={() => onOpenRun(last_run.activity_id)}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Laatste run</span>
            <span style={{ fontSize: 11, color: 'var(--faint)' }}>{last_run.date}</span>
          </div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 10 }}>
            <span className="tnum" style={{ fontSize: 18, fontWeight: 500 }}>{kmStr(last_run.distance_km)} km</span>
            <span className="tnum" style={{ fontSize: 18, fontWeight: 500 }}>{paceStr(last_run.avg_pace_s_per_km)} /km</span>
            <span className="tnum" style={{ fontSize: 18, fontWeight: 500 }}>{last_run.avg_hr ?? '–'} bpm</span>
          </div>
          <div style={{ marginBottom: 8 }}><ZoneBar zones={last_run.zones} /></div>
          {last_run.duiding ? <CoachNote>{last_run.duiding}</CoachNote> : null}
        </Card>
      )}
    </div>
  )
}
