# Marathon Coach — Fase 2 Design (marathon-planningsengine)

**Datum:** 2026-07-07
**Status:** goedgekeurd (brainstorm), klaar voor implementatieplan
**Scope:** Fase 2 van 4

## Doel

Een **regelgebaseerde trainingsplan-engine** die per atleet een compleet schema van nu →
racedag genereert, en dat schema toont in de "Schema"-tab (nu placeholder) als een
Runna-achtig plan: plan-header met voortgang + geschatte tijd, een weekweergave die de
runs slim rond de vaste kracht/Hyrox-dagen plant, en per training doel-paces per onderdeel.

### Atleten & races (concreet)
- **Rowan** — Marathon van Amsterdam, **zo 18 okt 2026** (~14 wk), doel **sub-4:00**
  (marathonpace ≈ 5:41/km). 3 runs/week; vast: Hyrox wo, kracht di/vr.
- **Vriendin** — NN Dam tot Damloop **16,1 km, 20 sep 2026** (~10 wk), doel "comfortabel
  finishen" (geen tijd). 2 runs/week.

### Succescriterium
Rowan opent de Schema-tab en ziet: hoeveel weken tot zijn race, zijn geschatte finishtijd,
de trainingen van deze week (met zijn Hyrox/kracht correct ingepast), en per run de doel-pace
per segment — met een korte uitleg waarom. Idem voor vriendin op haar 16 km-plan.

## Niet-doelen (Fase 2)
- **Geen adaptief herplannen** — het plan wordt één keer gegenereerd op basis van de fitheid
  bij aanmaak. Herberekenen na elke run = **Fase 3**.
- **Geen LLM** — paces, periodisering en coach-notes zijn regelgebaseerd. AI = **Fase 4**.
- **Geen push naar het horloge** (guided runs op Garmin/Apple Watch) — later/onzeker.
- **Geen GPS-kaarten** — losstaand, later.
- Kracht/Hyrox worden **ingepast en gerespecteerd**, niet zelf voorgeschreven (Rowan vult die
  zelf; de engine plant de runs eromheen). Kracht op meer dagen = latere verfijning.

## Ontwerpprincipes
Voortbouwend op Fase 1: prescriptief ("wat doe ik vandaag"), gelaagd (week-glimp → workout-detail),
altijd het waarom, concrete doel-paces, mobiel-eerst, per atleet. UI = **Optie A** (goedgekeurd):
plan-header + horizontale week-strip + grote "vandaag/geselecteerde"-workout met doel-paces.

## Data-model (nieuwe tabellen, SQLite + Postgres)

**`athlete_training_prefs`** — vaste weekstructuur per atleet.
- `athlete_id` (PK), `runs_per_week` INT, `run_days` TEXT (JSON lijst weekdagen, bv. `["mon","thu","sat"]`),
  `fixed_days` TEXT (JSON, bv. `{"wed":"hyrox","tue":"strength","fri":"strength"}`).

**`training_plan`** — één actief plan per atleet.
- `id` (PK, autoincrement / serial), `athlete_id`, `race_name` TEXT, `race_date` TEXT,
  `race_distance_km` REAL, `goal_time_s` INT NULL, `start_date` TEXT, `weeks` INT,
  `methodology` TEXT (default `"periodized-v1"`), `created_at` TEXT.

**`planned_workout`** — één rij per trainingsdag.
- PK `(athlete_id, date)`. Kolommen: `plan_id`, `week_num` INT, `phase` TEXT
  (base/build/peak/taper), `day_type` TEXT (run/strength/hyrox/rest),
  `run_type` TEXT NULL (easy/quality/long/race), `title` TEXT, `distance_km` REAL NULL,
  `segments` TEXT (JSON: `[{"label":"Inlopen 2 km","distance_m":2000,"target_pace_s":370}, {"label":"4× 1 km tempo","reps":4,"distance_m":1000,"target_pace_s":315}, ...]`),
  `target_pace_s` INT NULL (hoofd-pace), `coach_note` TEXT,
  `status` TEXT (planned/done/skipped, default planned), `linked_activity_id` INT NULL.

Schema idempotent via `db.py` (`SCHEMA_SQLITE`/`SCHEMA_PG` + `_init_pg`); `migrate_to_supabase.py`
TABLES/TABLE_PKS uitbreiden met de drie tabellen.

## Engine (`plan_engine.py` — pure functies, testbaar)

**Interface:** `generate_plan(plan: dict, prefs: dict, fitness: dict) -> list[planned_workout dict]`.
Geen I/O; de API-laag haalt fitness op, roept dit aan, en schrijft de rijen weg.

**1. Fitheid-baseline (`fitness` input):** afgeleid uit opgeslagen data (hergebruik `metrics.py`
+ vo2max/recente runs): huidige easy-pace, huidig weekvolume, langste recente run.

**2. Doel-paces (`compute_paces`):**
- Mét doeltijd (Rowan): marathonpace = doeltijd / afstand (sub-4 → 5:41/km). Afgeleid:
  easy = MP + 35 s, long = MP + 20 s, tempo/threshold = MP − 25 s, interval = MP − 55 s.
- Zónder doeltijd (vriendin): baseer op huidige easy-pace; race-pace = huidige easy − 20 s met
  bescheiden progressie over de weken; easy/long/tempo relatief daaraan.
- Alle paces afgerond op hele seconden.

**3. Periodisering (`phase_for_week`, `week_targets`):**
- Fasen naar rato van totaal weken: base ~30%, build ~40%, peak ~20%, taper (rest, min 2 wk
  marathon / 1-2 wk kortere race).
- Lange duurloop: start op `max(langste recente run, ondergrens)`, +1–2 km/wk, elke 3e-4e week
  terugval (cutback), piek ~3 wk vóór race (marathon ~30–32 km; 16 km ~18 km), daarna taper omlaag.
- Kwaliteit per fase: base = korte tempo/strides; build = tempo + marathonpace-segmenten;
  peak = race-pace lange stukken + intervallen; taper = kort en scherp, minder volume.
- Easy runs: op easy-pace, korter dan lange run.

**4. Week-assemblage (`assemble_week`):** verdeel de fase-targets over de `run_days`, plaats
kwaliteit op een frisse dag, lange run op het weekend-slot, easy op een herstel-slot ná een
fixed hard-day (Hyrox). Vul `fixed_days` met strength/hyrox, resterende dagen = rest.
**Regel:** geen `quality`/`long` op de dag direct ná een `hyrox`-dag.

**5. Coach-note (`coach_rules.py` uitbreiden):** korte NL-uitleg per workout op basis van
run_type + fase (stabiele interface, Fase 4 vervangt door LLM).

## Geschatte finishtijd (`estimate_finish`)
Uit huidige fitheid (VO₂max-gebaseerde voorspelling of extrapolatie recente race-pace) → een
**range** (bv. 3:52–4:05), getoond in de plan-header. Herberekend bij het ophalen van het plan.

## API-endpoints (`api/routes.py`)
- `POST /athlete/{id}/plan` — maak/vervang plan. Body: race_name, race_date, race_distance_km,
  goal_time_s?, prefs (of leest `athlete_training_prefs`). Haalt fitness op, roept `generate_plan`,
  schrijft `training_plan` + `planned_workout`-rijen. Idempotent: verwijdert bestaand plan eerst.
- `GET /athlete/{id}/plan` — plan-header: race, race_date, weken-totaal, huidige week,
  voltooid/totaal km, geschatte tijd, doeltijd.
- `GET /athlete/{id}/plan/week?week=N` (default = huidige week) — lijst `planned_workout` van die week.
- `GET /athlete/{id}/workout/{date}` — één workout met segments + coach-note.
- `POST /athlete/{id}/workout/{date}/register` — koppel de gesyncte activity van die datum
  (match op athlete_id + date), zet status=done + `linked_activity_id`. (In Fase 2 mag dit ook
  automatisch bij sync: run op datum X → planned_workout datum X op done.)

## Frontend (`dashboard/`) — Schema-tab, Optie A
- Vervang `screens/Schema.jsx` (placeholder) door het echte scherm.
- Nieuwe primitieven waar nodig: `PlanHeader`, `WeekStrip` (7 dagen, type-icoon, vandaag geaccentueerd),
  `WorkoutCard` (segments met doel-pace + coach-note). Hergebruik bestaande `Card`/`CoachNote`/tokens.
- API-client (`api.js`): `plan`, `planWeek`, `workout`.
- Klik op een run-dag in de strip → toont die workout in de kaart. Klik op een run → (later) detail.
- Werkt licht/donker, mobiel-eerst; consistent met Fase 1-stijl (safety-orange).

## Plan aanmaken (bootstrap)
Voor Fase 2 worden de twee plannen aangemaakt via `POST /plan` met de bekende parameters
(Rowan marathon/sub-4/18 okt; vriendin 16 km/20 sep), en `athlete_training_prefs` geseed
(Rowan ma/do/za + Hyrox wo + kracht di/vr; vriendin 2 run-dagen). Een echte invoer-UI ("kies je
race") is een latere verfijning — niet in Fase 2.

## Foutafhandeling / randgevallen
- **Geen plan voor atleet** → `/plan` geeft `null`/lege staat; Schema-tab toont "nog geen plan".
- **Race-datum in verleden / < min weken** → engine geeft een verkort plan met een waarschuwing in
  de header (geen crash).
- **Onvoldoende fitheid-data** (weinig runs) → val terug op conservatieve default-paces + markeer
  de geschatte tijd als "indicatief".
- **Ontbrekende segments** → workout toont minimaal titel + afstand.

## Testen
- **`plan_engine.py`:** unit-tests voor `compute_paces` (sub-4 → 5:41 MP + afgeleide zones; geen-doel
  pad), `phase_for_week` (grenzen base/build/peak/taper), lange-run-progressie + cutback + taper,
  `assemble_week` (geen quality/long ná hyrox; juiste dagen gevuld), volledige `generate_plan`
  (juist aantal weken, elke run-dag gevuld, taper aanwezig).
- **API:** endpoint-tests tegen test-DB — plan aanmaken → header/week/workout kloppen; register zet
  status=done; lege staat bij geen plan.
- **Frontend:** smoke-render Schema-tab met mock plan/week payload.

## Deploy / operationeel
Ongewijzigd: SQLite lokaal / Supabase via lokale launchd-sync; nieuwe tabellen via `init_db`/`_init_pg`
+ `migrate_to_supabase`. Frontend build → `dashboard/dist` committen → `vercel --prod`
(whoami=sidehustlehqs). Repo op `~/garmin-coach`.

## Splitsing naar bouwplannen (writing-plans)
Net als Fase 1 in twee plannen:
- **Plan 1 (backend):** data-model + `plan_engine.py` + `coach_rules`-uitbreiding + endpoints + plan-bootstrap.
- **Plan 2 (frontend):** Schema-tab (Optie A) + primitieven + API-client + build/deploy.

## Openstaande verfijningen (later, niet-blokkerend)
- Kracht op 3-4 dagen i.p.v. rust invullen (Rowan's voorkeur), max 1 rustdag.
- Invoer-UI om zelf race/doel te kiezen.
- `weekly_volume_km` (ISO) vs bestaand `/weekly_volume` (`%W`) verzoenen wanneer gekoppeld.
