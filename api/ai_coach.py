"""AI-coach: Claude Haiku voor dagelijkse note, Sonnet voor chat.
Pure functies — geen DB I/O hier, context-dict komt van routes.py."""
from __future__ import annotations
import os
import anthropic

_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

_DAILY_SYSTEM = (
    "Je bent een persoonlijke hardloopcoach. Geef in 1-2 korte Nederlandse zinnen duiding "
    "op de gezondheids- en trainingsdata van de atleet. Wees direct en motiverend. "
    "Gebruik concrete getallen. Geen opsommingstekens, geen headers."
)

_CHAT_SYSTEM = (
    "Je bent een persoonlijke hardloopcoach. Beantwoord vragen over de training van de atleet "
    "in het Nederlands. Je hebt toegang tot de huidige gezondheids- en trainingsdata hieronder. "
    "Wees concreet, bondig (max 3 alinea's) en gebruik de data. Geen opsommingstekens tenzij "
    "de gebruiker er om vraagt."
)


def build_daily_context(ctx: dict) -> str:
    lines = [f"Atleet: {ctx.get('athlete_name', 'onbekend')}"]
    if ctx.get("readiness") is not None:
        lines.append(f"Readiness: {ctx['readiness']}/100")
    if ctx.get("hrv") is not None:
        lines.append(f"HRV: {ctx['hrv']} ms")
    if ctx.get("sleep_s") is not None:
        h = round(ctx["sleep_s"] / 3600, 1)
        score = f" (score {ctx['sleep_score']})" if ctx.get("sleep_score") else ""
        lines.append(f"Slaap: {h}u{score}")
    if ctx.get("body_battery") is not None:
        lines.append(f"Body battery: {ctx['body_battery']}")
    if ctx.get("acwr") is not None:
        lines.append(f"Belasting (ACWR): {ctx['acwr']}")
    if ctx.get("training_today"):
        t = ctx["training_today"]
        lines.append(f"Training vandaag: {t.get('title', t.get('run_type', '-'))}")
    return "\n".join(lines)


def daily_note(ctx: dict) -> str:
    """1-2 zinnen coaching-note via Claude Haiku."""
    context_text = build_daily_context(ctx)
    resp = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        system=_DAILY_SYSTEM,
        messages=[{"role": "user", "content": f"Data van vandaag:\n{context_text}"}],
    )
    return resp.content[0].text.strip()


def chat(messages: list[dict], ctx: dict) -> str:
    """Chat-reply via Claude Sonnet."""
    context_text = build_daily_context(ctx)
    system_with_ctx = f"{_CHAT_SYSTEM}\n\nHuidige data:\n{context_text}"
    resp = _client.messages.create(
        model="claude-sonnet-5",
        max_tokens=512,
        system=system_with_ctx,
        messages=messages,
    )
    return resp.content[0].text.strip()
