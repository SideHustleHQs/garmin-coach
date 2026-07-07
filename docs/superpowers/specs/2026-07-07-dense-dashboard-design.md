# Marathon Coach — Vol dashboard (health + training) · Design

**Datum:** 2026-07-07
**Status:** goedgekeurd (brainstorm), klaar voor implementatieplan
**Scope:** Werkstroom A (dashboard-verdichting). Werkstroom B (schema adaptief op gezondheidsdata = Fase 3) volgt hierna, apart.

## Doel
Het "Vandaag"-scherm ombouwen van een beknopte glimp naar een **vol dashboard** dat zoveel mogelijk relevante info toont: hardloop-statistieken bovenaan, algemene gezondheidsstatistieken daaronder — plus de geplande training van vandaag bovenaan (gekoppeld aan het Schema). Detail blijft aantikbaar (drill-down).

### Succescriterium
Rowan opent "Vandaag" en ziet in één scroll: wat hij vandaag moet trainen, of hij hersteld is, zijn hardloop-fitheid (VO₂max, weekvolume, belasting, tempo@HR), zijn laatste run, én zijn gezondheid (HRV, slaap, body battery, rust-HR, stappen, calorieën) — elk met een trend waar zinvol.

## Niet-doelen
- Geen adaptief schema (dat is Werkstroom B / Fase 3).
- Geen nieuwe Garmin-data-ingest — alle benodigde data wordt al opgeslagen (activities, daily_stats [steps, active_calories], daily_heart_rates [resting_hr], body_battery [+level], training_readiness, vo2max, training_load_balance [acwr], hrv, sleep).
- Geen nieuwe metrics dan wat er is (+ afgeleide pace@HR die al bestaat in `metrics.py`).

## Layout (goedgekeurd, Optie "vol dashboard")
Verticale scroll op het Vandaag-scherm:
1. **Training vandaag** — kaart met de `planned_workout` van vandaag (titel + kern-pace); tik → Schema/workout. Lege staat als er geen plan/workout is.
2. **Readiness-hero** — score + label + coach-duiding (bestaand).
3. **Sectie "Hardlopen"** — tegelgrid (2 kol): VO₂max (+sparkline), Weekvolume (bars), Belasting/ACWR (meter + status), Tempo@150bpm (+sparkline).
4. **Laatste run** — kernstats + HR-zonebalk + duiding (bestaand, compacter).
5. **Sectie "Gezondheid"** — tegelgrid (3 kol): HRV (+sparkline), Slaap (uren + score), Body battery (niveau), Rust-HR (+sparkline), Stappen, Actieve kcal.

Tegels aantikbaar → bestaande/uit te breiden detailschermen. Consistent met huidige stijl (donker/licht, safety-orange, tabular-nums).

## Architectuur

### Backend — één geconsolideerd dashboard-endpoint
Vervang/breid `GET /athlete/{id}/home` uit tot een payload die het hele scherm voedt in één call (snel, minder round-trips). Velden:
- `today_workout`: de `planned_workout` van vandaag (of null) — title, run_type, target_pace_s, week_num, day_type.
- `readiness`: score, level, hrv, sleep_s, body_battery, duiding (bestaand).
- `running`:
  - `vo2max` + `vo2max_trend` (lijst {date, vo2max}),
  - `weekly_volume` (laatste ~6 weken, lijst {week, km}),
  - `acwr` + `acwr_status`,
  - `pace_at_hr` (laatste waarde uit `metrics.pace_at_hr`) + korte trend.
- `last_run`: bestaand (date, distance, pace, hr, zones, duiding).
- `health`:
  - `hrv` (laatste) + `hrv_trend`,
  - `sleep` {duration_s, score},
  - `body_battery` (level_current),
  - `resting_hr` (laatste) + `resting_hr_trend`,
  - `steps`, `active_calories` (laatste dag).

Alles null-tolerant: ontbrekende waarde → veld `null` (frontend toont "–"). Hergebruik bestaande query-patronen (`_conn`/`_exec`) en `metrics.py`. Trends: laatste ~14 dagen/6 weken, oplopend gesorteerd.

**Overweging:** bestaande losse endpoints (`/vo2max_trend`, `/weekly_volume`, `/training_load`, `/recovery`, `/daily_stats`) blijven bestaan (detailschermen gebruiken ze); het dashboard gebruikt de nieuwe geconsolideerde payload om het scherm in één fetch te vullen.

### Frontend — Vandaag-scherm herbouwen
- `screens/Home.jsx`: herbouw naar de volle layout; één `api.dashboard(athleteId)`-call.
- Nieuwe primitief `StatTile` (label, waarde, unit, + optioneel sparkline / bars / meter / trend-pijl) — DRY voor alle tegels.
- Nieuwe primitief `SectionHeader` (uppercase sectietitel).
- Hergebruik: `ReadinessHero`, `Card`, `CoachNote`, `Sparkline`, `ZoneBar`, `VolumeBars`, `format.js`.
- "Training vandaag"-kaart bovenaan (klik → zet screen op 'schema').
- Tegels aantikbaar → bestaande detailschermen (`fitness`/`load`) of run-detail; gezondheidstegels kunnen later een detailscherm krijgen (niet in deze scope — tik doet dan niets of opent een simpele trend). Voor deze scope: hardloop-tegels linken naar bestaande fitness/load-detail; gezondheidstegels tonen de trend inline (geen nieuw detailscherm).

## Foutafhandeling / lege staten
- Geen plan/workout vandaag → "Training vandaag"-kaart toont "Geen training gepland" (of rustdag).
- Ontbrekende stat (bv. VO₂max/ACWR voor Rowan) → tegel toont "–" (blijft staan, geen lege plek).
- Te weinig datapunten voor een trend → sparkline verborgen, alleen de waarde.
- Fetch-fout → nette foutmelding i.p.v. eeuwig "Laden…".

## Testen
- **Backend:** endpoint-test tegen test-DB — payload bevat alle secties; null-velden bij ontbrekende data; trends zijn arrays.
- **Frontend:** `StatTile` smoke (waarde + "–"-fallback); Home-scherm smoke-render met mock-payload (secties Hardlopen + Gezondheid aanwezig).
- Bestaande suite blijft groen.

## Deploy
Ongewijzigd: build → `dashboard/dist` committen → `vercel --prod` (whoami=sidehustlehqs). Data komt uit Supabase via de dagelijkse launchd-sync. Repo `~/garmin-coach`.

## Splitsing naar bouwplannen
Waarschijnlijk **één plan** (backend-endpoint + frontend-herbouw zijn samen behapbaar), tenzij het te groot wordt — dan backend-endpoint eerst, dan Home-herbouw. Beslis bij writing-plans.

## Openstaande verfijningen (later)
- Detailschermen voor gezondheidstegels (slaapfases, HRV-historie volledig).
- Fallback-tekst i.p.v. "–" voor Rowan's ontbrekende VO₂max/ACWR (bv. "meer runs nodig").
- Extra metrics indien gewenst (stress, ademhaling) — niet nu.
