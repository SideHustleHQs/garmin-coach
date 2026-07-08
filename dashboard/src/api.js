const BASE = '/api'

async function get(path) {
  const r = await fetch(BASE + path)
  if (!r.ok) throw new Error(`${r.status} ${path}`)
  return r.json()
}

async function post(path, body) {
  const r = await fetch(BASE + path, { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined })
  if (!r.ok) throw new Error(`${r.status} ${path}`)
  return r.json()
}

export const api = {
  athletes:        () => get('/athletes'),
  hero:            (id) => get(`/athlete/${id}/hero`),
  runs:            (id) => get(`/athlete/${id}/runs`),
  weeklyVolume:    (id) => get(`/athlete/${id}/weekly_volume`),
  tempoTrend:      (id) => get(`/athlete/${id}/tempo_trend`),
  zoneDist:        (id) => get(`/athlete/${id}/zone_distribution`),
  vo2maxTrend:     (id) => get(`/athlete/${id}/vo2max_trend`),
  dailyStats:      (id) => get(`/athlete/${id}/daily_stats?days=14`),
  recovery:        (id) => get(`/athlete/${id}/recovery?days=7`),
  trainingLoad:    (id) => get(`/athlete/${id}/training_load`),
  runEfficiency:   (id) => get(`/athlete/${id}/run_efficiency`),
  attentionPoints: (id) => get(`/athlete/${id}/attention_points`),
  splits:          (id, actId) => get(`/athlete/${id}/activity/${actId}/splits`),
  home:            (id) => get(`/athlete/${id}/home`),
  dashboard:       (id) => get(`/athlete/${id}/dashboard`),
  fitness:         (id) => get(`/athlete/${id}/fitness`),
  plan:            (id) => get(`/athlete/${id}/plan`),
  planWeek:        (id, week) => get(`/athlete/${id}/plan/week?week=${week}`),
  workout:         (id, date) => get(`/athlete/${id}/workout/${date}`),
  registerWorkout: (id, date) => post(`/athlete/${id}/workout/${date}/register`),
  overrideWorkout: (id, date) => post(`/athlete/${id}/workout/${date}/override`),
}

export async function getPlanMeta(athleteId) {
  const r = await fetch(`/api/athlete/${athleteId}/plan/meta`)
  if (!r.ok) throw new Error('plan/meta failed')
  return r.json()
}

export async function getDailyNote(athleteId) {
  const r = await fetch(`/api/athlete/${athleteId}/coach/daily`, { method: 'POST' })
  if (!r.ok) throw new Error('coach/daily failed')
  return r.json()
}

export async function sendChatMessage(athleteId, message) {
  const r = await fetch(`/api/athlete/${athleteId}/coach/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  if (!r.ok) throw new Error('coach/chat failed')
  return r.json()
}

export async function getChatHistory(athleteId) {
  const r = await fetch(`/api/athlete/${athleteId}/coach/history`)
  if (!r.ok) throw new Error('coach/history failed')
  return r.json()
}
