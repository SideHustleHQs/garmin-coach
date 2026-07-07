import { useState, useEffect } from 'react'
import { api } from '../api'
import PlanHeader from '../ui/PlanHeader'
import WeekStrip from '../ui/WeekStrip'
import WorkoutCard from '../ui/WorkoutCard'

function currentWeekOf(plan) {
  if (!plan?.start_date) return 1
  const wk = Math.floor((new Date() - new Date(plan.start_date)) / (7 * 864e5)) + 1
  return Math.min(Math.max(wk, 1), plan.weeks)
}

export default function Schema({ athleteId }) {
  const [plan, setPlan] = useState(undefined)   // undefined=laden, null=geen plan
  const [week, setWeek] = useState(1)
  const [days, setDays] = useState([])
  const [selected, setSelected] = useState(null)
  const [err, setErr] = useState(false)

  useEffect(() => {
    setPlan(undefined); setErr(false)
    api.plan(athleteId).then(p => {
      if (!p || p.plan === null) { setPlan(null); return }
      setPlan(p); setWeek(currentWeekOf(p))
    }).catch(() => setErr(true))
  }, [athleteId])

  useEffect(() => {
    if (!plan) return
    api.planWeek(athleteId, week).then(ds => {
      setDays(ds)
      const today = new Date().toISOString().slice(0, 10)
      const pick = ds.find(d => d.date === today) || ds.find(d => d.day_type === 'run') || ds[0]
      setSelected(pick ? pick.date : null)
    }).catch(() => setErr(true))
  }, [plan, week, athleteId])

  if (err) return <p style={{ color: 'var(--hard)' }}>Kon plan niet laden.</p>
  if (plan === undefined) return <p style={{ color: 'var(--faint)' }}>Laden…</p>
  if (plan === null) return (
    <div style={{ textAlign: 'center', color: 'var(--faint)', padding: '60px 20px' }}>
      <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--ink)' }}>Nog geen plan</p>
      <p style={{ fontSize: 13, marginTop: 8 }}>Er is nog geen trainingsplan aangemaakt voor deze atleet.</p>
    </div>
  )

  const selectedWorkout = days.find(d => d.date === selected)
  return (
    <div>
      <PlanHeader plan={plan} currentWeek={week} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '4px 2px 8px' }}>
        <button onClick={() => setWeek(w => Math.max(1, w - 1))} disabled={week <= 1}
          style={{ background: 'none', border: 'none', color: week <= 1 ? 'var(--faint)' : 'var(--muted)', fontSize: 18 }}>‹</button>
        <span style={{ fontSize: 12, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.06em' }}>Week {week} / {plan.weeks}</span>
        <button onClick={() => setWeek(w => Math.min(plan.weeks, w + 1))} disabled={week >= plan.weeks}
          style={{ background: 'none', border: 'none', color: week >= plan.weeks ? 'var(--faint)' : 'var(--muted)', fontSize: 18 }}>›</button>
      </div>
      <WeekStrip days={days} selectedDate={selected} onSelect={setSelected} />
      <WorkoutCard workout={selectedWorkout} />
    </div>
  )
}
