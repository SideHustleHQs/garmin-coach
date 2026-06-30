const BASE = '/api'

async function get(path) {
  const r = await fetch(BASE + path)
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
}
