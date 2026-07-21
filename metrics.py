"""Pure functies: afgeleide hardloop-metrics uit opgeslagen data. Geen I/O."""
from __future__ import annotations

from datetime import date as _date


def pace_at_hr(runs: list[dict], hr_min: int = 140, hr_max: int = 160) -> list[dict]:
    """Aerobe efficiëntie: pace (s/km) van runs met gemiddelde HR in de band (~150bpm ±10).

    runs: dicts met date, distance_m, duration_s, avg_hr. Gesorteerd op date oplopend.
    Band is bewust 20bpm breed: atleten met een hogere easy-HR (bv. ~160) vallen
    anders volledig buiten de boot en krijgen een leeg tempo-cijfer.
    """
    out = []
    for r in runs:
        hr = r.get("avg_hr")
        dist_m = r.get("distance_m") or 0
        dur_s = r.get("duration_s") or 0
        if hr is None or dist_m <= 0 or dur_s <= 0:
            continue
        if hr_min <= hr <= hr_max:
            pace = dur_s / (dist_m / 1000)
            out.append({"date": r["date"], "pace_s_per_km": round(pace, 1)})
    return out


def weekly_volume_km(runs: list[dict]) -> dict[str, float]:
    """Som van afstand (km) per ISO-week (sleutel 'YYYY-Www')."""
    totals: dict[str, float] = {}
    for r in runs:
        d = _date.fromisoformat(r["date"][:10])
        iso_year, iso_week, _ = d.isocalendar()
        key = f"{iso_year}-W{iso_week:02d}"
        totals[key] = totals.get(key, 0.0) + (r.get("distance_m") or 0) / 1000.0
    return {k: round(v, 1) for k, v in totals.items()}
