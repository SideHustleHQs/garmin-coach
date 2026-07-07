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
