import { useState, useEffect } from 'react'
import { api, getDailyNote } from '../api'
import Card from '../ui/Card'
import ReadinessHero from '../ui/ReadinessHero'
import StatTile from '../ui/StatTile'
import SectionHeader from '../ui/SectionHeader'
import VolumeBars from '../ui/VolumeBars'
import ZoneBar from '../ui/ZoneBar'
import CoachNote from '../ui/CoachNote'
import { paceStr, kmStr, sleepStr } from '../format'

export default function Home({ athleteId, onOpenRun, onNav }) {
  const [d, setD] = useState(null)
  const [err, setErr] = useState(false)
  const [coachNote, setCoachNote] = useState(null)

  useEffect(() => {
    setD(null); setErr(false)
    api.dashboard(athleteId).then(setD).catch(() => setErr(true))
  }, [athleteId])

  useEffect(() => {
    if (!athleteId) return
    getDailyNote(athleteId).then(d => setCoachNote(d.note)).catch(() => {})
  }, [athleteId])

  if (err) return <p style={{ color: 'var(--hard)' }}>Kon data niet laden.</p>
  if (!d) return <p style={{ color: 'var(--faint)' }}>Laden…</p>

  const r = d.running || {}
  const h = d.health || {}
  const tw = d.today_workout
  const lr = d.last_run

  return (
    <div>
      {/* Training vandaag */}
      <Card onClick={() => onNav && onNav('schema')} style={{ borderColor: '#3a2418', borderTop: '3px solid var(--amber)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 10.5, color: 'var(--amber)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em' }}>
            Training vandaag{tw && tw.week_num ? ` · week ${tw.week_num}` : ''}
          </span>
        </div>
        {tw ? (
          <>
            <p style={{ fontSize: 17, fontWeight: 600, margin: 0 }}>{tw.title}</p>
            {tw.target_pace_s ? <p style={{ fontSize: 12, color: 'var(--muted)', margin: '4px 0 0' }}>doel {paceStr(tw.target_pace_s)} /km</p> : null}
          </>
        ) : <p style={{ fontSize: 14, color: 'var(--muted)', margin: 0 }}>Geen training gepland vandaag.</p>}
      </Card>

      <ReadinessHero readiness={{ ...(d.readiness || {}), duiding: coachNote }} />

      <SectionHeader color="var(--blue)">Hardlopen</SectionHeader>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <StatTile label="VO₂max" value={r.vo2max} trendVals={(r.vo2max_trend || []).map(x => x.vo2max)} trendColor="var(--good)" onClick={() => onNav && onNav('fitness')} accentColor="var(--blue)" />
        <StatTile label="Weekvolume" value={r.weekly_volume && r.weekly_volume.length ? Math.round(r.weekly_volume[r.weekly_volume.length - 1].km) : null} unit="km" onClick={() => onNav && onNav('load')} accentColor="var(--blue)">
          <VolumeBars vals={(r.weekly_volume || []).map(w => w.km)} height={22} />
        </StatTile>
        <StatTile label="Belasting (ACWR)" value={r.acwr} onClick={() => onNav && onNav('load')} accentColor="var(--blue)" />
        <StatTile label="Tempo @150bpm" value={paceStr(r.pace_at_hr)} unit="/km" trendVals={(r.pace_at_hr_trend || []).map(x => x.pace_s_per_km)} trendColor="var(--good)" onClick={() => onNav && onNav('fitness')} accentColor="var(--blue)" />
      </div>

      {lr && (
        <Card onClick={() => onOpenRun && onOpenRun(lr.activity_id)} style={{ marginTop: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>Laatste run</span>
            <span style={{ fontSize: 11, color: 'var(--faint)' }}>{lr.date} · {kmStr(lr.distance_km)} km</span>
          </div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 10 }}>
            <span className="tnum" style={{ fontSize: 17, fontWeight: 600 }}>{paceStr(lr.avg_pace_s_per_km)} <span style={{ fontSize: 10.5, color: 'var(--faint)' }}>/km</span></span>
            <span className="tnum" style={{ fontSize: 17, fontWeight: 600 }}>{lr.avg_hr ?? '–'} <span style={{ fontSize: 10.5, color: 'var(--faint)' }}>bpm</span></span>
          </div>
          <ZoneBar zones={lr.zones} />
          {lr.duiding ? <div style={{ marginTop: 10 }}><CoachNote>{lr.duiding}</CoachNote></div> : null}
        </Card>
      )}

      <SectionHeader color="var(--green)">Gezondheid</SectionHeader>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
        <StatTile label="HRV" value={h.hrv} trendVals={(h.hrv_trend || []).map(x => x.hrv)} trendColor="var(--z2)" accentColor="var(--green)" />
        <StatTile label="Slaap" value={sleepStr(h.sleep && h.sleep.duration_s)} accentColor="var(--green)">
          {h.sleep && h.sleep.score != null ? <p style={{ fontSize: 10.5, color: 'var(--faint)', margin: '2px 0 0' }}>score {h.sleep.score}</p> : null}
        </StatTile>
        <StatTile label="Body" value={h.body_battery} accentColor="var(--green)" />
        <StatTile label="Rust-HR" value={h.resting_hr} unit="bpm" trendVals={(h.resting_hr_trend || []).map(x => x.resting_hr)} trendColor="var(--z1)" accentColor="var(--green)" />
        <StatTile label="Stappen" value={h.steps != null ? h.steps.toLocaleString('nl-NL') : null} accentColor="var(--green)" />
        <StatTile label="Actieve kcal" value={h.active_calories != null ? Math.round(h.active_calories) : null} accentColor="var(--green)" />
      </div>
    </div>
  )
}
