import { useState, useEffect } from 'react'
import './theme.css'
import { api } from './api'
import GoalBanner from './components/GoalBanner'
import AttentionPoints from './components/AttentionPoints'
import HeroRow from './components/HeroRow'
import TrainingLoad from './components/TrainingLoad'
import WeekVolume from './components/WeekVolume'
import TempoTrend from './components/TempoTrend'
import ZoneDistribution from './components/ZoneDistribution'
import RunEfficiency from './components/RunEfficiency'
import VO2MaxTrend from './components/VO2MaxTrend'
import RecentRuns from './components/RecentRuns'
import SplitsPanel from './components/SplitsPanel'
import DailyStats from './components/DailyStats'
import RecoveryStrip from './components/RecoveryStrip'

const PANEL_COMPONENTS = {
  GoalBanner, AttentionPoints, HeroRow, TrainingLoad,
  WeekVolume, TempoTrend, ZoneDistribution, RunEfficiency,
  VO2MaxTrend, RecentRuns, SplitsPanel, DailyStats, RecoveryStrip,
}

function AthleteTab({ athleteId }) {
  const [data, setData] = useState({})
  const [panels, setPanels] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [athletes, hero, runs, weekVol, tempo, zones, vo2, daily, recovery,
               trainingLoad, runEfficiency, attentionPoints] = await Promise.all([
          api.athletes(),
          api.hero(athleteId),
          api.runs(athleteId),
          api.weeklyVolume(athleteId),
          api.tempoTrend(athleteId),
          api.zoneDist(athleteId),
          api.vo2maxTrend(athleteId),
          api.dailyStats(athleteId),
          api.recovery(athleteId),
          api.trainingLoad(athleteId),
          api.runEfficiency(athleteId),
          api.attentionPoints(athleteId),
        ])

        const athlete = athletes.find(a => a.id === athleteId) || {}
        setPanels(athlete.panels || Object.keys(PANEL_COMPONENTS))

        const latestRun = runs[0]
        const splits = latestRun
          ? await api.splits(athleteId, latestRun.activity_id).catch(() => [])
          : []

        setData({ hero, runs, weekVol, tempo, zones, vo2, daily, recovery,
                  trainingLoad, runEfficiency, attentionPoints, splits })
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [athleteId])

  if (loading) return <div style={{ padding: 40, color: 'var(--text-2)' }}>Laden...</div>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {panels.map(name => {
        const Comp = PANEL_COMPONENTS[name]
        if (!Comp) return null
        return <Comp key={name} athleteId={athleteId} data={data} />
      })}
    </div>
  )
}

export default function App() {
  const [athletes, setAthletes] = useState([])
  const [activeId, setActiveId] = useState(null)

  useEffect(() => {
    api.athletes().then(list => {
      setAthletes(list)
      if (list.length > 0) setActiveId(list[0].id)
    })
  }, [])

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      <div style={{
        background: 'var(--bg-card)', borderBottom: '1px solid var(--border)',
        padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 24,
      }}>
        <span style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-1)' }}>
          🏃 Garmin Coach
        </span>
        <div style={{ display: 'flex', gap: 8 }}>
          {athletes.map(a => (
            <button
              key={a.id}
              onClick={() => setActiveId(a.id)}
              style={{
                padding: '6px 14px', borderRadius: 8, border: 'none', cursor: 'pointer',
                background: activeId === a.id ? 'var(--accent)' : 'var(--bg-card2)',
                color: 'var(--text-1)', fontSize: 13, fontWeight: 600,
              }}
            >
              {a.display_name}
            </button>
          ))}
        </div>
      </div>
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '24px 16px' }}>
        {activeId && <AthleteTab athleteId={activeId} />}
      </div>
    </div>
  )
}
