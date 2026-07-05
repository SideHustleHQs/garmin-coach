import { useState, useEffect } from 'react'
import './theme.css'
import { api } from './api'
import TabBar from './ui/TabBar'
import AthleteSwitcher from './ui/AthleteSwitcher'
import CountdownChip from './ui/CountdownChip'
import Home from './screens/Home'
import RunDetail from './screens/RunDetail'
import FitnessDetail from './screens/FitnessDetail'
import LoadDetail from './screens/LoadDetail'
import RunsList from './screens/RunsList'
import Schema from './screens/Schema'
import Delen from './screens/Delen'

export default function App() {
  const [athletes, setAthletes] = useState([])
  const [athleteId, setAthleteId] = useState(null)
  const [screen, setScreen] = useState('home')
  const [runId, setRunId] = useState(null)

  useEffect(() => {
    api.athletes().then(list => {
      setAthletes(list)
      if (list.length) setAthleteId(list.find(a => a.id === 'rowan')?.id || list[0].id)
    }).catch(() => setAthletes([]))
  }, [])

  function nav(s) { setScreen(s); setRunId(null) }
  function openRun(id) { setRunId(id); setScreen('run') }

  if (!athleteId) return <div style={{ padding: 24, color: 'var(--faint)' }}>Laden…</div>
  const athlete = athletes.find(a => a.id === athleteId) || {}

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <div style={{ padding: '18px 16px 12px', borderBottom: '1px solid var(--line)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 style={{ fontSize: 18, fontWeight: 600 }}>Hoi, {athlete.display_name}</h1>
            <p style={{ fontSize: 12, color: 'var(--faint)', marginTop: 2 }}>marathon-coach</p>
          </div>
          <CountdownChip weeks={null} label="wk tot race" />
        </div>
        <AthleteSwitcher athletes={athletes} current={athleteId} onSwitch={setAthleteId} />
      </div>

      <div style={{ flex: 1, padding: 16 }}>
        {screen === 'home' && <Home athleteId={athleteId} onOpenRun={openRun} onNav={nav} />}
        {screen === 'run' && <RunDetail athleteId={athleteId} runId={runId} onBack={() => nav('home')} />}
        {screen === 'fitness' && <FitnessDetail athleteId={athleteId} onBack={() => nav('home')} />}
        {screen === 'load' && <LoadDetail athleteId={athleteId} onBack={() => nav('home')} />}
        {screen === 'runs' && <RunsList athleteId={athleteId} onOpenRun={openRun} />}
        {screen === 'schema' && <Schema />}
        {screen === 'delen' && <Delen athlete={athlete} />}
      </div>

      <TabBar current={screen} onNav={nav} />
    </div>
  )
}
