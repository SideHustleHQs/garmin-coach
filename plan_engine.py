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
