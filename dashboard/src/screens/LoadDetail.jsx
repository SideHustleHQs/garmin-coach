import { useState, useEffect } from 'react'
import { api } from '../api'
import Card from '../ui/Card'
import VolumeBars from '../ui/VolumeBars'
import CoachNote from '../ui/CoachNote'

export default function LoadDetail({ athleteId, onBack }) {
  const [load, setLoad] = useState(null)
  const [vol, setVol] = useState([])
  useEffect(() => {
    Promise.all([api.trainingLoad(athleteId), api.weeklyVolume(athleteId)])
      .then(([l, v]) => { setLoad(l); setVol(v.slice().reverse()) }).catch(() => setLoad(null))
  }, [athleteId])
  const latest = load?.latest
  return (
    <div>
      <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--muted)', fontSize: 13, fontWeight: 500, marginBottom: 14 }}>‹ terug</button>
      <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Bouw ik veilig op</h2>
      {!load ? <p style={{ color: 'var(--faint)' }}>Laden…</p> : (
        <>
          <Card>
            <p style={{ fontSize: 12, color: 'var(--muted)' }}>Acute : chronische belasting (ACWR)</p>
            <p className="tnum" style={{ fontSize: 40, fontWeight: 500 }}>{latest?.acwr ?? '–'}</p>
            <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>optimaal 0,8–1,3</p>
          </Card>
          <Card>
            <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Weekvolume</h3>
            <VolumeBars vals={vol.map(w => w.km)} height={70} />
            <p style={{ fontSize: 11, color: 'var(--faint)', marginTop: 8 }}>laatste weken, km per week</p>
          </Card>
          {latest?.status_feedback ? <CoachNote>{latest.status_feedback}</CoachNote> : null}
        </>
      )}
    </div>
  )
}
