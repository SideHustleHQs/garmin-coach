"""Regelgebaseerde coach-duiding (NL). Stabiele interface — Fase 4 vervangt de body
door een LLM zonder dat aanroepende code wijzigt. Elke functie: dict in, str uit."""
from __future__ import annotations


def duiding_readiness(snapshot: dict) -> str:
    score = snapshot.get("score")
    if score is None:
        return "Nog geen readiness-data voor vandaag."
    if score >= 75:
        return "Je bent goed hersteld en klaar voor een pittige sessie."
    if score >= 50:
        return "Redelijk hersteld — een rustige tot gemiddelde training past vandaag."
    return "Je herstel is laag. Kies voor rust of een lichte herstel-run."


def duiding_load(load: dict) -> str:
    acwr = load.get("acwr")
    if acwr is None:
        return "Nog onvoldoende data om je belasting te beoordelen."
    if acwr > 1.5:
        return f"Zeer hoge belasting (ratio {acwr:.1f}) — blessurerisico. Neem rust."
    if acwr > 1.3:
        return f"Belasting loopt op (ratio {acwr:.1f}). Houd deze week iets in."
    if acwr < 0.8:
        return f"Belasting is laag (ratio {acwr:.1f}). Ruimte om volume op te bouwen."
    return f"Je belasting is optimaal en veilig (ratio {acwr:.1f})."


def duiding_run(run: dict) -> str:
    paces = run.get("splits_pace") or []
    if len(paces) >= 3:
        if paces[-1] < paces[0]:
            return "Mooie negative split — je laatste kilometers waren je snelste."
        if paces[-1] > paces[0] * 1.05:
            return "Je tempo zakte richting het einde. Let op je pacing en herstel."
    hr = run.get("avg_hr")
    if hr is not None:
        return "Nette run met je hartslag onder controle."
    return "Run opgeslagen."
