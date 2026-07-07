# Garmin Coach — CLAUDE.md

## Project
Privé dashboard voor hardloop/Hyrox-training (eigen data + vriendin).
**Nooit werk-gerelateerd. Strikt gescheiden van werk-accounts.**

## Eigenaarschap
- **GitHub:** SideHustleHQs/garmin-coach (privé)
- **Vercel scope:** sidehustlehq (persoonlijk)
- **Lokaal pad:** `~/garmin-coach` — bewust NIET in `~/Documents` (macOS TCC/mapbescherming
  blokkeert launchd-toegang daar → auto-sync faalt met "Operation not permitted"/exit 126)

## Twee werelden — NOOIT mengen
| Wereld | GitHub | Vercel scope | Google |
|--------|--------|-------------|--------|
| PRIVÉ (deze repo) | SideHustleHQs | sidehustlehq | privé |
| WERK | rowan-blip | werk-team | rowan@contentventures.nl |

## Deploy-regel (HARD)
Vóór ELKE `vercel` deploy: draai `vercel whoami` en toon de uitkomst.
- Moet tonen: **sidehustlehq**
- Toont het iets anders (bijv. `rowan-blip`) → **STOP**, meld het, deploy NIET
- Wissel indien nodig: `vercel switch` → sidehustlehq

## Secrets
Uitsluitend uit **Bitwarden**. Nooit uit chat, losse JSON, of hardcoded.

## Secrets & env vars
Komen uitsluitend uit **Bitwarden**.
Nooit uit chat, losse JSON-bestanden, of hardcoded in code.
`.env` staat in `.gitignore` — nooit committen.

## Architectuur
- **API:** FastAPI Python (Vercel serverless via `@vercel/python`)
- **Frontend:** Vite + React 19 (Vercel static build, `dashboard/`)
- **Database:** Supabase Postgres (Frankfurt, `eu-central-1`)
- **Sync:** LOKAAL via launchd (`com.garmincoach.sync`, dagelijks 08:15) → `scripts/sync_local.sh`
  = pull → ingest (SQLite) → `migrate_to_supabase.py` (push). GitHub Actions is UITGEZET: Garmin
  blokkeert cloud-IP's (429 login / lege oauth2-refresh). Mac moet ~08:15 wakker zijn.

## Atleten
- `rowan` — primaire atleet (toegevoegd)
- `vriendin` — tweede atleet
Beide via per-atleet creds/tokens in `.env` + `.garmin_tokens/<athlete>/`.

## Dependency-splits
- `api/requirements.txt` → alleen API-deps (FastAPI, psycopg2, dotenv) — gebruikt door Vercel
- `requirements.txt` (root) → volledige deps incl. garminconnect — gebruikt door lokale sync
  (psycopg2-binary op 2.9.12: 2.9.10 mist een wheel voor py3.9/arm64)
