# Garmin Coach — CLAUDE.md

## Project
Privé dashboard voor hardloop/Hyrox-training (eigen data + vriendin).
**Nooit werk-gerelateerd. Strikt gescheiden van werk-accounts.**

## Eigenaarschap
- **GitHub:** SideHustleHQs/garmin-coach (privé)
- **Vercel scope:** sidehustlehq (persoonlijk)

## Deploy-regel (HARD)
Vóór elke `vercel` deploy: controleer `vercel whoami`.
- Moet tonen: account onder **sidehustlehq**
- Zo niet → **stop**, meld het, deploy niet

## Secrets & env vars
Komen uitsluitend uit **Bitwarden**.
Nooit uit chat, losse JSON-bestanden, of hardcoded in code.
`.env` staat in `.gitignore` — nooit committen.

## Architectuur
- **API:** FastAPI Python (Vercel serverless via `@vercel/python`)
- **Frontend:** Vite + React 19 (Vercel static build, `dashboard/`)
- **Database:** Supabase Postgres (Frankfurt, `eu-central-1`)
- **Sync:** GitHub Actions cron 06:00 UTC → Garmin pull + ingest

## Atleten
- `vriendin` — primaire atleet
- `rowan` — secundaire atleet (toe te voegen)

## Dependency-splits
- `api/requirements.txt` → alleen API-deps (FastAPI, psycopg2, dotenv) — gebruikt door Vercel
- `requirements.txt` (root) → volledige deps incl. garminconnect — gebruikt door GitHub Actions + lokaal
