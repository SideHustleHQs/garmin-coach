"""Regelgebaseerde dagelijkse plan-aanpassing. Pure functies, geen I/O.
Stabiele interface — Fase 4 kan de regels vervangen door een LLM."""
from __future__ import annotations


def _easy(paces, km=6):
    return {"adjusted_run_type": "easy", "adjusted_title": f"Rustige duurloop {km} km",
            "adjusted_target_pace_s": paces["easy"],
            "adjusted_segments": [{"label": f"Rustige duurloop {km} km",
                                   "distance_m": km * 1000, "target_pace_s": paces["easy"]}]}


def adjust_day(workout: dict, signals: dict, paces: dict) -> dict | None:
    """Geef een aanpassing voor deze geplande workout, of None (origineel behouden).
    workout: run_type/title/target_pace_s/distance_km/segments. signals: readiness/acwr/
    sleep_score/sleep_s/recent_quality_hit/downgrade_last_48h. paces: compute_paces-dict."""
    rt = workout.get("run_type")
    if rt not in ("easy", "quality", "long"):
        return None  # rust/kracht/hyrox/race: niet aanpassen

    readiness = signals.get("readiness")
    acwr = signals.get("acwr")
    sleep_score = signals.get("sleep_score")
    sleep_s = signals.get("sleep_s")

    bad = (readiness is not None and readiness < 40) or (acwr is not None and acwr > 1.5)
    mid = (readiness is not None and 40 <= readiness < 55) or \
          (sleep_score is not None and sleep_score < 50) or \
          (sleep_s is not None and sleep_s < 5 * 3600)

    if bad:
        if rt in ("quality", "long"):
            adj = _easy(paces)
            adj["adjustment_reason"] = f"Lage readiness/hoge belasting → vandaag rustig i.p.v. {rt}."
            return adj
        return {"adjusted_run_type": "rest", "adjusted_title": "Rust", "adjusted_segments": None,
                "adjusted_target_pace_s": None,
                "adjustment_reason": "Je herstel is laag — vandaag rust."}

    if mid:
        if rt == "quality":
            return {"adjusted_run_type": "quality", "adjusted_title": workout.get("title") or "Kwaliteit (zachter)",
                    "adjusted_target_pace_s": paces["mp"],
                    "adjusted_segments": [{"label": "werk op marathonpace", "target_pace_s": paces["mp"]}],
                    "adjustment_reason": "Matig herstel → kwaliteit één stap zachter (marathonpace)."}
        if rt == "long":
            km = round((workout.get("distance_km") or 16) * 0.85)
            adj = _easy(paces, km); adj["adjusted_run_type"] = "long"
            adj["adjusted_title"] = f"Lange duurloop {km} km (ingekort)"
            adj["adjusted_target_pace_s"] = paces["long"]
            adj["adjusted_segments"] = [{"label": adj["adjusted_title"], "distance_m": km * 1000, "target_pace_s": paces["long"]}]
            adj["adjustment_reason"] = "Matig herstel → lange duurloop iets ingekort."
            return adj
        return None  # easy blijft easy

    # fris + vóór → kleine opwaardering (alleen quality, geen recente downgrade)
    if rt == "quality" and readiness is not None and readiness >= 75 \
            and signals.get("recent_quality_hit") and not signals.get("downgrade_last_48h"):
        base = workout.get("target_pace_s") or paces["tempo"]
        return {"adjusted_run_type": "quality", "adjusted_title": (workout.get("title") or "Kwaliteit") + " (aangescherpt)",
                "adjusted_target_pace_s": base - 10,
                "adjusted_segments": [{"label": "werk (scherper)", "target_pace_s": base - 10}],
                "adjustment_reason": "Je bent fris en ligt voor — 10 s/km scherper."}
    return None


import datetime as _dt


def check_drift(rows: list, today, signals: dict) -> dict:
    """Detecteer structureel afdwalen. Pure functie.
    Returns {"drift": bool, "reason": str | None}"""
    if isinstance(today, str):
        today = _dt.date.fromisoformat(today)
    today_s = str(today)
    cutoff = str(today - _dt.timedelta(days=14))

    # Trigger 1: ≥2 gemiste kwaliteits/lange runs in 14 dagen
    missed_quality = [
        r for r in rows
        if r.get("planned_date", "") >= cutoff
        and r.get("planned_date", "") < today_s
        and r.get("run_type") in ("quality", "long")
        and (r.get("missed") or not r.get("linked_activity_id"))
    ]
    if len(missed_quality) >= 2:
        return {"drift": True,
                "reason": f"{len(missed_quality)} kwaliteits/lange runs gemist — plan herberekend."}

    # Trigger 2: ACWR ≥ 1.5 gedurende ≥5 dagen
    acwr_hist = signals.get("acwr_history", [])
    high_acwr_days = sum(1 for v in acwr_hist if v is not None and v >= 1.5)
    if high_acwr_days >= 5:
        return {"drift": True,
                "reason": f"Chronisch hoge belasting ({high_acwr_days} dagen ACWR≥1.5) — plan herberekend."}

    return {"drift": False, "reason": None}


def replan(plan: dict, today, prefs: dict, fitness: dict) -> list:
    """Herbereken de resterende weken via plan_engine.generate_plan.
    Geeft alleen toekomstige/vandaag rijen terug."""
    from plan_engine import generate_plan
    if isinstance(today, str):
        today = _dt.date.fromisoformat(today)
    today_s = str(today)
    # Bereken weeks uit race_date als dat ontbreekt
    plan = dict(plan)
    if "weeks" not in plan and "race_date" in plan:
        race = _dt.date.fromisoformat(plan["race_date"])
        plan["weeks"] = max(1, (race - today).days // 7)
    # Alias distance_km -> race_distance_km indien nodig
    if "race_distance_km" not in plan and "distance_km" in plan:
        plan["race_distance_km"] = plan["distance_km"]
    # start_date = vandaag indien niet meegegeven
    if "start_date" not in plan:
        plan["start_date"] = today_s
    # fixed_days default leeg indien niet meegegeven
    prefs = dict(prefs)
    if "fixed_days" not in prefs:
        prefs["fixed_days"] = {}
    new_rows = generate_plan(plan, prefs, fitness)
    # Bepaal taper-start (2 weken voor race)
    race_d = _dt.date.fromisoformat(plan["race_date"])
    taper_start_s = str(race_d - _dt.timedelta(weeks=2))
    # generate_plan gebruikt "date"; normaliseer naar "planned_date" voor consistentie
    result = []
    for r in new_rows:
        row = dict(r)
        date_val = row.get("planned_date") or row.get("date", "")
        row["planned_date"] = date_val
        if date_val < today_s:
            continue
        # Taper-regel: geen quality-runs in laatste 2 weken
        if date_val >= taper_start_s and row.get("run_type") == "quality":
            row = dict(row)
            row["run_type"] = "easy"
            row["title"] = "Rustige duurloop (taper)"
        result.append(row)
    return result


def absorb_missed(rows: list[dict], today: str) -> list[dict]:
    """Markeer verleden run-dagen zonder afgeronde activity als missed.
    (Herplanning/verschuiven van gemiste sessies gebeurt in Plan 2 — hier alleen markeren.)"""
    out = []
    for r in rows:
        r = dict(r)
        r["missed"] = bool(r.get("day_type") == "run" and r["date"] < today and not r.get("done"))
        out.append(r)
    return out
