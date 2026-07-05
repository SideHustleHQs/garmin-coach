# Marathon Coach — Fase 1 Design (data-fundament + Runna-achtig dashboard)

**Datum:** 2026-07-05
**Status:** goedgekeurd (brainstorm), klaar voor implementatieplan
**Scope:** Fase 1 van 4 (zie "Plaats in het geheel")

## Doel

Het huidige metric-dump-dashboard vervangen door een **Runna-achtig, mobiel-eerst,
gelaagd hardloop-dashboard** dat de data toont die er voor marathontraining écht toe
doet — geframed als de antwoorden van een coach, niet als een muur met cijfers.

Tegelijk het **data-fundament** leggen (ontbrekende data ingesten + afgeleide metrics
berekenen) waar Fase 2–4 op bouwen.

### Succescriterium
Rowan opent de app op zijn telefoon en weet binnen 5 seconden: ben ik klaar om te
trainen, waar sta ik qua fitheid, bouw ik veilig op, en hoe ging mijn laatste run —
met de mogelijkheid om op elke kaart te tikken voor volledige onderbouwing. De weergave
is deelbaar/toonbaar aan anderen.

## Plaats in het geheel (niet-doelen van Fase 1)

Het volledige product is een marathon-coach-platform in 4 fasen:
1. **Fase 1 (dit doc):** data-fundament + dashboard.
2. **Fase 2:** marathon-planningsengine (schema van nu → racedag o.b.v. fitheid + doel).
3. **Fase 3:** adaptief herplannen (schema past zich na elke run aan).
4. **Fase 4:** AI-coachlaag (LLM-analyses + voorstellen).

**Expliciet buiten Fase 1:**
- Geen trainingsschema of plan-generatie (Fase 2).
- Geen adaptieve herberekening (Fase 3).
- Geen LLM/AI. Coach-duiding in Fase 1 is **regelgebaseerd** (Fase 4 vervangt dit).
- "Schema"-tab is een placeholder. "Delen"-tab is minimaal (read-only home-weergave).
- Geen race-tijd-voorspellingen als kernfeature (mag simpel/afgeleid, geen prioriteit).

## Ontwerpprincipes (uit Runna-analyse)

1. **Prescriptief boven beschrijvend** — framing rond runnersvragen, niet rond metrics.
   In Fase 1 nog zonder plan, dus: "waar sta ik / ben ik klaar / bouw ik veilig op /
   hoe ging het". De structuur leidt al naar het plan van Fase 2.
2. **Gelaagd** — home = glimp; tik-door = volledige onderbouwing. "Meer data" leeft in
   detailschermen, niet op het home-scherm.
3. **Altijd het waarom** — elke kaart/run heeft een korte duiding.
4. **Concrete getallen** — echte paces, zones, ACWR — geen vage labels.
5. **Vertrouwen via toon** — coach-taal, rustig, Nederlands, jij/je-vorm.
6. **Mobiel-eerst + deelbaar.**

## Schermen

| Scherm | Beantwoordt | Kerninhoud |
|---|---|---|
| **Home** (coach-brief) | Dagelijkse glimp | Readiness-hero, fitheid-kaart, belasting-kaart, laatste-run-kaart, marathon-countdown-chip (leeg in Fase 1), tabbalk |
| **Run-detail** | Hoe ging deze run? | Kernstats, splits per km, tijd in HR-zones, loopdynamiek, trainingseffect, duiding |
| **Fitheid-detail** | Waar sta ik? | VO₂max-historie, tempo-bij-vaste-HR-trend (aerobe efficiëntie), rust-HR-trend |
| **Belasting-detail** | Bouw ik veilig op? | ACWR-historie, acute vs chronische load, aeroob/anaeroob vs targets, weekvolume-historie |
| **Runs-lijst** | Overzicht | Chronologische runs met kernstats; instap naar run-detail |

Tabbalk: **Vandaag · Runs · Schema (placeholder) · Delen (minimaal)**.

Multi-atleet: **Rowan primair**, met atleet-switcher (vriendin blijft). Alle schermen
zijn per atleet; de datalaag ondersteunt dit al.

## Architectuur

Bestaande stack blijft: FastAPI (`api/`) + Vite/React (`dashboard/`) + SQLite (lokaal) /
Supabase Postgres (prod), gevuld via de lokale launchd-sync
(`scripts/sync_local.sh`: pull → ingest → migrate_to_supabase).

### Componenten en verantwoordelijkheden

**1. Data-ingest-uitbreiding** (`ingest.py`, `db.py`)
- Nieuw: **HRV** ingesten (nu wel opgehaald, niet opgeslagen) → tabel `hrv`.
- Nieuw: **slaap** ingesten → tabel `sleep` (duur + fases + score voor zover Garmin levert).
- Uitbreiden: **body-battery-niveau** (huidig/hoog/laag), naast bestaande laden/ontladen.
- Postgres-schema (`SCHEMA_PG` in db.py) meegroeien; `migrate_to_supabase.py` TABLES-lijst
  uitbreiden met de nieuwe tabellen.
- Elke nieuwe tabel volgt bestaand patroon: PK `(athlete_id, date)`, upsert-ingest.

**2. Afgeleide-metric-laag** (nieuw: `metrics.py`)
Pure functies die uit opgeslagen data view-klare waarden berekenen. Geen I/O, goed testbaar.
- `weekly_volume(runs)` → km per ISO-week.
- `pace_at_hr(runs)` → aerobe-efficiëntie-trend. **v1-definitie:** gemiddelde pace over
  runs met gemiddelde HR in een aerobe band (bv. 145–155 bpm), als tijdreeks. Bewust simpel.
- `readiness_snapshot(...)` → readiness-score + drijvers (HRV, slaap, body battery) samengevoegd.
- `acwr_status(...)` → passthrough/afronding van opgeslagen training_load_balance.

**3. Regelgebaseerde duiding-engine** (nieuw: `coach_rules.py`)
- Functies per context: `duiding_run(run)`, `duiding_readiness(snapshot)`, `duiding_load(load)`.
- Geven korte NL-zinnen o.b.v. drempels (bv. HR-zoneverdeling, negative split, ACWR-band).
- **Stabiele interface** zodat Fase 4 de implementatie kan vervangen door een LLM zonder
  dat de API-contracten wijzigen.

**4. API-laag** (`api/main.py`) — view-klare payloads, niet ruwe rijen
- `GET /api/athletes` (bestaat).
- `GET /api/{athlete}/home` → readiness, fitheid-samenvatting, belasting-samenvatting,
  laatste-run-samenvatting, marathon-countdown (null in Fase 1), + duiding-strings.
- `GET /api/{athlete}/runs` → lijst kernstats.
- `GET /api/{athlete}/runs/{activity_id}` → detail: stats, splits, zones, loopdynamiek,
  trainingseffect, duiding.
- `GET /api/{athlete}/fitness` → VO₂max-historie, pace@HR-trend, rust-HR-trend, + duiding.
- `GET /api/{athlete}/load` → ACWR-historie, acute/chronische load, aeroob/anaeroob-balans,
  weekvolume-historie, + duiding.

**5. Frontend** (`dashboard/src`) — herbouw rond schermen
- Schermen: `Home`, `RunDetail`, `FitnessDetail`, `LoadDetail`, `RunsList`.
- Gedeelde UI-primitieven: `Card`, `MetricStat`, `ZoneBar`, `SplitsBar`, `Sparkline`,
  `CoachNote`, `AthleteSwitcher`, `TabBar`, `ReadinessHero`, `CountdownChip`.
- Mobiel-eerst CSS; kaart-gebaseerd; flat; licht/donker; één accentkleur.
- Data via `api.js` naar de nieuwe endpoints; schermen consumeren view-klare payloads.
- Oude losse panel-componenten worden vervangen (niet uitgebreid).

### Datastroom

```
Garmin  →  garmin_test_pull.py  →  ingest.py (+ HRV, slaap, body-battery-niveau)  →  SQLite
                                                              │
                                        migrate_to_supabase.py │ (push)
                                                              ▼
                                                          Supabase
                                                              ▲
        Frontend (schermen)  ← view-klare JSON ←  api/main.py  ←  metrics.py + coach_rules.py
```

## Visueel / branding

- Runna-achtig: strak, rustig, veel witruimte, ronde kaarten, bold getallen.
- Mobiel-eerst (telefoon-breedte leidend), werkt ook op desktop.
- Licht + donker.
- Eén accentkleur — **exacte kleur/typografie te kiezen tijdens de bouw** (aparte
  branding-stap, geen blocker voor de spec).
- HR-zones: vaste kleurschaal koel→warm (Z1 blauw … Z5 rood).

## Foutafhandeling / randgevallen

- **Ontbrekende data** (bv. geen HRV/slaap op een dag, of nog geen ACWR): kaart toont een
  nette lege staat ("nog geen data"), niet een crash of 0.
- **Nieuwe atleet zonder runs:** lege-staat-schermen met uitleg.
- **API-fouten:** frontend toont per kaart een foutstaat, blokkeert niet het hele scherm.
- **Afgeleide metrics met te weinig datapunten** (bv. pace@HR met <3 runs in de band):
  toon "onvoldoende data voor trend" i.p.v. een misleidende lijn.

## Testen

- **`metrics.py`:** unit-tests met fixture-runs voor `weekly_volume`, `pace_at_hr`,
  `readiness_snapshot`, week-grenzen, en te-weinig-data-gevallen.
- **`coach_rules.py`:** unit-tests die drempel-grenzen afdekken (elke duiding-tak).
- **API:** endpoint-tests tegen een test-DB met seed-data; controleren op view-klare vorm
  en lege-staat-gedrag.
- **Ingest:** tests dat HRV/slaap/body-battery-niveau correct upserten (bestaand
  test-patroon in `tests/`).
- **Frontend:** minimaal — smoke-render van elk scherm met mock-payload.

## Deploy / operationeel

- Ongewijzigd t.o.v. huidige flow: lokale launchd-sync vult SQLite→Supabase; nieuwe
  ingest-stappen draaien mee in `scripts/sync_local.sh`.
- Frontend: lokaal builden, `dashboard/dist` committen, `npx vercel@latest --prod`
  (whoami = `sidehustlehqs`).
- Nieuwe DB-tabellen: schema wordt idempotent aangemaakt via `init_db()` (SQLite) en
  `_init_pg()` (Postgres) — draait al bij elke sync.

## Openstaande kleine keuzes (tijdens bouw, geen blocker)

- Exacte accentkleur + typografie (branding-stap).
- Precieze aerobe HR-band voor pace@HR (start 145–155 bpm, kalibreren op echte data).
- Vorm van de "Delen"-weergave (Fase 1: minimaal read-only; publieke link kan later).
