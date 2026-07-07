# Marathon Coach — Fase 3 Design (adaptief herplannen)

**Datum:** 2026-07-07
**Status:** goedgekeurd (brainstorm), klaar voor implementatieplan
**Scope:** Fase 3 van 4. Splitst in **Plan 1 (dagelijkse micro-aanpassing + gemiste run)** en **Plan 2 (vooruit herplannen)**.

## Doel
Het statische Fase 2-plan laten leven: het reageert op je gezondheids- en trainingsdata. Dagelijks stuurt het de eerstvolgende training(en) bij op hoe je ervoor staat, en bij structureel afdwalen herberekent het de resterende weken tot de race — met harde veiligheidsvangrails.

### Atleten-context
Rowan (marathon sub-4, 18 okt) traint veel (Hyrox + kracht + 3 runs), kan load aan → tweerichting toegestaan. Vriendin (16 km, 20 sep) → conservatiever.

### Succescriterium
Als Rowan's readiness laag is (of ACWR te hoog, of hij een run miste), toont "Training vandaag" + het Schema een **aangepaste** sessie met uitleg waaróm, zonder dat hij iets hoeft te doen — en hij kan met één tik terug naar de origineel geplande sessie. Bij structureel afdwalen klopt het resterende schema weer richting sub-4.

## Ontwerpfilosofie (goedgekeurd)
- **Tweerichting, asymmetrisch:** slechte signalen → automatisch **afschalen**; structureel fris + vóór → **kleine** opwaardering/suggestie (nooit stapelen).
- **Auto-toegepast + transparant + overrulebaar:** aanpassing gebeurt vanzelf, met "aangepast · reden"-label; één tik terug naar origineel.
- **Regelgebaseerd** (geen LLM — dat is Fase 4). Stabiele interface zodat Fase 4 de regels kan vervangen.

## Niet-doelen
- Geen LLM/AI-coach (Fase 4).
- Geen medisch/blessure-diagnose; puur trainingsbelasting-heuristiek.
- Geen nieuwe Garmin-data-ingest (alle signalen bestaan al).

## Vangrails (HARD, altijd)
1. Nooit twee zware dagen achter elkaar; nooit `quality`/`long` direct ná een `hyrox`-dag (bestaat al in `assemble_week`).
2. Weekvolume max ~10% omhoog per week (bij herplannen).
3. Taper blijft altijd staan (laatste 2 wk marathon / 1-2 wk kortere race).
4. Na een zeer-lage-readiness-dag (<40) minimaal een easy/rustdag; geen kwaliteit.
5. Opwaardering nooit ná een afschaling in dezelfde 48u; nooit een geplande rustdag in een harde dag omzetten.

## Onderdeel 1 — Dagelijkse micro-aanpassing (Plan 1)

**Signalen (laatste waarden uit Supabase):** readiness-score, ACWR, HRV-afwijking van baseline, slaap (duur/score), body battery, plus per geplande run of de bijbehorende activity bestaat (gedaan) en of de target-pace gehaald werd.

**Regels (`adapt_engine.adjust_day(planned_workout, signals) -> adjustment | None`), pure functie:**
- **readiness < 40** of **ACWR > 1.5**: `quality`/`long` → **easy** (kortere afstand); als het al easy is → **rust**. Reden meegegeven.
- **readiness 40–55** of **slechte slaap (score < 50 of < 5u)**: `quality` behoudt maar **intensiteit één stap zachter** (tempo→marathonpace); `long` iets korter.
- **readiness ≥ 75 én laatste 2 kwaliteitsruns paces gehaald/onder target**: `quality` mag **10 s/km scherper** (of suggestie) — begrensd; alleen als geen afschaling in 48u.
- **Anders:** geen aanpassing (origineel plan).
- Elke aanpassing levert: `adjusted_run_type`, `adjusted_title`, `adjusted_segments` (herberekende paces/afstand), `adjustment_reason` (NL, via `coach_rules`).

**Gemiste run (`adapt_engine.absorb_missed(week_rows, today, signals)`):** als een geplande run-dag in het verleden ligt zonder gekoppelde activity → markeer `missed`; verschuif de belangrijkste gemiste sessie (long > quality) naar de eerstvolgende geschikte run-dag als dat binnen de vangrails past, anders laten vallen (geen inhaal-stapeling). Duiding meegeven.

## Onderdeel 2 — Vooruit herplannen (Plan 2)

**Drift-triggers (bij de dagelijkse sync):**
- ≥2 gemiste kwaliteits-/lange runs in de laatste 2 weken, óf
- ACWR ≥ 1.5 gedurende ≥5 dagen, óf
- fitheid wijkt structureel af van doel (geschatte tijd valt buiten een marge rond de doeltijd).

**Actie (`adapt_engine.replan(plan, remaining_rows, fitness) -> new_rows`):** herbereken de resterende weken via de bestaande `plan_engine` (nieuwe fitheid-baseline + huidige week als startpunt), met de vangrails (max +10% volume/wk, taper intact). Verleden (afgeronde) dagen blijven ongemoeid.

## Data-model
Uitbreiding van `planned_workout` (geen nieuwe tabel): het origineel blijft de basis; de aanpassing is een overlay.
- Nieuwe kolommen: `adjusted_run_type TEXT`, `adjusted_title TEXT`, `adjusted_segments TEXT (JSON)`, `adjusted_target_pace_s INTEGER`, `adjustment_reason TEXT`, `is_adjusted INTEGER DEFAULT 0`, `user_override INTEGER DEFAULT 0`, `missed INTEGER DEFAULT 0`.
- **Effectieve workout** (wat de API teruggeeft) = `user_override ? origineel : (is_adjusted ? adjusted_* : origineel)`. Idempotent: adaptatie herschrijft alleen niet-override, toekomstige/vandaag dagen.
- Migratie: `_migrate_planned_workout` (SQLite ALTER, mirror in `_init_pg` via ADD COLUMN IF NOT EXISTS) + `SCHEMA_*`.

## Waar het draait
- **Dagelijkse sync** (`scripts/sync_local.sh`): na ingest → een stap die de adaptatie voor vandaag+komende dagen (en drift → replan) berekent en wegschrijft. Nieuwe module/CLI `scripts/adapt.py` (of aanroep vanuit sync).
- **On-demand:** `POST /athlete/{id}/adapt` (herbereken nu) voor test/handmatig.
- **API-lezen:** `/dashboard`, `/plan/week`, `/workout` geven de **effectieve** workout + `adjustment_reason` + `is_adjusted`/`missed`-vlaggen.
- **Override:** `POST /athlete/{id}/workout/{date}/override` (zet `user_override=1` → toont origineel).

## Frontend
- **Dashboard "Training vandaag"** + **Schema `WorkoutCard`**: als `is_adjusted` → toon aangepaste titel/paces + een subtiel label "aangepast · {reden}" en een "← origineel"-knop (roept override aan). `missed`-dagen krijgen een grijs "gemist"-merk in de `WeekStrip`.
- Hergebruik bestaande primitieven; minimale toevoeging (badge + revert-knop).

## Foutafhandeling / randgevallen
- Geen plan → adaptatie doet niets.
- Ontbrekende signalen (bv. geen readiness vandaag) → geen afschaling op dat signaal (conservatief: alleen aanpassen op wat er is).
- Override + latere nieuwe aanpassing: override blijft gerespecteerd tot de dag voorbij is.
- Replan raakt nooit afgeronde/verleden dagen.

## Testen
- **`adapt_engine`:** unit-tests per regel (readiness-drempels → juiste downgrade; fris+ahead → upgrade binnen grens; vangrail: geen upgrade na recente downgrade; missed-absorptie respecteert geen-stapeling; replan behoudt taper + volume-cap).
- **API:** effectieve-workout-logica (override/adjusted/origineel), `/adapt` schrijft aanpassingen, `/override` zet vlag.
- **Frontend:** WorkoutCard toont aangepaste + reden + revert; WeekStrip toont missed.

## Deploy / operationeel
Ongewijzigd: SQLite/Supabase via launchd-sync; nieuwe kolommen via `init_db`/`_init_pg` + migrate. Adaptatie draait in de sync (draait al dagelijks). Frontend build + deploy zoals gebruikelijk.

## Splitsing naar bouwplannen
- **Plan 1:** data-model (kolommen + migratie) + `adapt_engine.adjust_day`/`absorb_missed` + `coach_rules`-redenen + effectieve-workout in de API + `/adapt` + `/override` + sync-integratie + frontend-badge/revert.
- **Plan 2:** `adapt_engine.replan` + drift-detectie + sync-trigger + tests.

## Openstaande verfijningen (later)
- Fase 4: LLM vervangt de regel-heuristiek + geeft narratieve coaching.
- Notificatie bij grote aanpassing (push).
