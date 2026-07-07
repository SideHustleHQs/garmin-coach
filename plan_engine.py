"""Regelgebaseerde trainingsplan-engine. Pure functies, geen I/O."""
from __future__ import annotations


def compute_paces(goal_time_s: int | None, distance_km: float, current_easy_s: int | None) -> dict:
    """Doel-paces in seconden/km. Met doeltijd: afgeleid van racepace.
    Zonder doeltijd: afgeleid van huidige easy-pace."""
    if goal_time_s:
        mp = round(goal_time_s / distance_km)
    elif current_easy_s:
        mp = current_easy_s - 20
    else:
        mp = 360  # conservatieve default (6:00/km)
    return {
        "mp": mp,
        "easy": (current_easy_s if (goal_time_s is None and current_easy_s) else mp + 35),
        "long": mp + 20,
        "tempo": mp - 25,
        "interval": mp - 55,
    }


def phase_for_week(week: int, total_weeks: int) -> str:
    """Periodiseringsfase op basis van positie in het plan (1-indexed week)."""
    frac = week / total_weeks
    if frac <= 0.30:
        return "base"
    if frac <= 0.70:
        return "build"
    if frac <= 0.85:
        return "peak"
    return "taper"


def long_run_progression(total_weeks: int, start_km: float, peak_km: float) -> list[float]:
    """Lange-duurloop per week: lineaire opbouw met cutback elke 3e week,
    piek in de peak-fase, daarna taper omlaag."""
    peak_week = max(1, round(total_weeks * 0.85))  # laatste peak-week
    out: list[float] = []
    for w in range(1, total_weeks + 1):
        if w >= peak_week:
            # taper: van piek terug naar ~60%
            steps_after = total_weeks - peak_week
            i = w - peak_week
            km = peak_km - (peak_km * 0.4) * (i / steps_after) if steps_after else peak_km
        else:
            base = start_km + (peak_km - start_km) * ((w - 1) / (peak_week - 1))
            if w % 3 == 0:  # cutback elke 3e week
                base *= 0.75
            km = base
        out.append(round(km))
    out[peak_week - 1] = round(peak_km)  # verzeker exacte piek
    return out


WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
HARD_TYPES = {"hyrox"}


def assemble_week(run_days: list[str], fixed_days: dict, long_km: float,
                  easy_km: float, quality: dict) -> list[dict]:
    """Bouw één week: lange run op laatste run-dag, quality op een run-dag die
    NIET direct na een harde (hyrox) dag valt, easy op de rest. Fixed dagen
    (strength/hyrox) ingevuld, overige dagen rest."""
    long_day = run_days[-1]
    # kandidaat-quality-dagen: run-dagen (excl. long) waarvan de vorige dag geen hard-type is
    def prev(d):
        return WEEKDAYS[(WEEKDAYS.index(d) - 1) % 7]
    candidates = [d for d in run_days if d != long_day and fixed_days.get(prev(d)) not in HARD_TYPES]
    quality_day = candidates[0] if candidates else next(d for d in run_days if d != long_day)

    days = []
    for wd in WEEKDAYS:
        if wd == long_day:
            days.append({"weekday": wd, "day_type": "run", "run_type": "long",
                         "distance_km": long_km, "title": f"Lange duurloop {round(long_km)} km"})
        elif wd == quality_day:
            days.append({"weekday": wd, "day_type": "run", "run_type": "quality",
                         "distance_km": None, "title": quality["title"], "quality": quality})
        elif wd in run_days:
            days.append({"weekday": wd, "day_type": "run", "run_type": "easy",
                         "distance_km": easy_km, "title": f"Rustige duurloop {round(easy_km)} km"})
        elif wd in fixed_days:
            days.append({"weekday": wd, "day_type": fixed_days[wd], "run_type": None,
                         "title": {"hyrox": "Hyrox", "strength": "Krachttraining"}.get(fixed_days[wd], fixed_days[wd])})
        else:
            days.append({"weekday": wd, "day_type": "rest", "run_type": None, "title": "Rust"})
    return days


import datetime as _dt


def _quality_spec(phase: str, paces: dict) -> dict:
    """Segments + titel voor de kwaliteitsrun per fase."""
    if phase == "base":
        return {"type": "tempo", "title": "Tempo-run 6 km", "segments": [
            {"label": "Inlopen 1,5 km", "distance_m": 1500, "target_pace_s": paces["easy"]},
            {"label": "3 km tempo", "distance_m": 3000, "target_pace_s": paces["tempo"]},
            {"label": "Uitlopen 1,5 km", "distance_m": 1500, "target_pace_s": paces["easy"]}]}
    if phase == "peak":
        return {"type": "interval", "title": "Intervallen 8 km", "segments": [
            {"label": "Inlopen 2 km", "distance_m": 2000, "target_pace_s": paces["easy"]},
            {"label": "5× 1 km", "reps": 5, "distance_m": 1000, "target_pace_s": paces["interval"]},
            {"label": "tussen 400 m dribbel", "distance_m": 400, "target_pace_s": paces["easy"] + 20},
            {"label": "Uitlopen 1,5 km", "distance_m": 1500, "target_pace_s": paces["easy"]}]}
    return {"type": "tempo", "title": "Tempo-intervallen 8 km", "segments": [
        {"label": "Inlopen 2 km", "distance_m": 2000, "target_pace_s": paces["easy"]},
        {"label": "4× 1 km tempo", "reps": 4, "distance_m": 1000, "target_pace_s": paces["tempo"]},
        {"label": "tussen 400 m dribbel", "distance_m": 400, "target_pace_s": paces["easy"] + 20},
        {"label": "Uitlopen 1,5 km", "distance_m": 1500, "target_pace_s": paces["easy"]}]}


def generate_plan(plan: dict, prefs: dict, fitness: dict) -> list[dict]:
    import coach_rules
    weeks = plan["weeks"]
    paces = compute_paces(plan.get("goal_time_s"), plan["race_distance_km"], fitness.get("current_easy_s"))
    peak_km = 32 if plan["race_distance_km"] > 30 else round(plan["race_distance_km"] * 1.15)
    start_km = max(fitness.get("longest_km") or 8, round(peak_km * 0.45))
    long_by_week = long_run_progression(weeks, start_km, peak_km)
    start = _dt.date.fromisoformat(plan["start_date"])

    rows: list[dict] = []
    for w in range(1, weeks + 1):
        phase = phase_for_week(w, weeks)
        quality = _quality_spec(phase, paces)
        easy_km = max(5, round(long_by_week[w - 1] * 0.4))
        days = assemble_week(prefs["run_days"], prefs["fixed_days"],
                             long_km=long_by_week[w - 1], easy_km=easy_km, quality=quality)
        for d in days:
            date = start + _dt.timedelta(days=(w - 1) * 7 + WEEKDAYS.index(d["weekday"]))
            run_type = d.get("run_type")
            if run_type == "quality":
                segments = quality["segments"]
                target = paces["tempo"]
            elif run_type == "long":
                segments = [{"label": f"Lange duurloop {round(d['distance_km'])} km",
                             "distance_m": int(d["distance_km"] * 1000), "target_pace_s": paces["long"]}]
                target = paces["long"]
            elif run_type == "easy":
                segments = [{"label": d["title"], "distance_m": int((d["distance_km"] or 0) * 1000),
                             "target_pace_s": paces["easy"]}]
                target = paces["easy"]
            else:
                segments = None
                target = None
            rows.append({
                "date": date.isoformat(), "week_num": w, "phase": phase,
                "day_type": d["day_type"], "run_type": run_type, "title": d["title"],
                "distance_km": d.get("distance_km"), "segments": segments, "target_pace_s": target,
                "coach_note": coach_rules.duiding_workout(run_type, phase) if run_type else None,
            })
    return rows


def estimate_finish(distance_km: float, goal_time_s: int | None, fitness: dict) -> tuple[int, int]:
    """Geschatte finishtijd-range (s). Met doeltijd: rond het doel; anders uit easy-pace."""
    if goal_time_s:
        center = goal_time_s
    else:
        easy = fitness.get("current_easy_s") or 360
        center = round((easy - 15) * distance_km)
    return (round(center * 0.97), round(center * 1.03))
