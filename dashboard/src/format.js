export function paceStr(sPerKm) {
  if (sPerKm == null) return '–'
  const m = Math.floor(sPerKm / 60)
  const s = Math.round(sPerKm % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

export function durationStr(sec) {
  if (sec == null) return '–'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = Math.round(sec % 60)
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

export function kmStr(km) {
  if (km == null) return '–'
  return km.toFixed(1).replace('.', ',')
}

export function sleepStr(sec) {
  if (sec == null) return '–'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  return `${h}:${String(m).padStart(2, '0')}`
}

export function hmStr(sec) {
  if (sec == null) return '–'
  const h = Math.floor(sec / 3600)
  const m = Math.round((sec % 3600) / 60)
  return `${h}:${String(m).padStart(2, '0')}`
}

export function hmRange(r) {
  if (!r || r.length !== 2) return '–'
  return `${hmStr(r[0])}–${hmStr(r[1])}`
}
