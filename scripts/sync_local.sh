#!/usr/bin/env bash
# Lokale dagelijkse Garmin-sync (draait via launchd op de Mac — residentieel IP).
# Pullt beide atleten en ingest naar Supabase (DATABASE_URL uit .env).
# Token-login wordt gebruikt zodra .garmin_tokens/<athlete>/ bestaat; de eerste
# keer voor een atleet is een verse login nodig (creds uit .env).
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

PY="$REPO/.venv/bin/python"
LOG_DIR="$REPO/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/sync.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

# Load .env (DATABASE_URL + per-athlete creds)
if [[ -f .env ]]; then
  set -a; source .env; set +a
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  log "WAARSCHUWING: DATABASE_URL leeg → ingest schrijft naar lokale SQLite, NIET Supabase."
fi

run_athlete() {
  local athlete="$1" name="$2" email="$3" password="$4"

  # Skip rowan zolang er geen creds én geen tokens zijn.
  if [[ -z "$email" && ! -d ".garmin_tokens/$athlete" ]]; then
    log "SKIP $athlete: geen creds in .env en geen cached tokens."
    return 0
  fi

  log "PULL $athlete..."
  if GARMIN_EMAIL="$email" GARMIN_PASSWORD="$password" "$PY" garmin_test_pull.py --athlete "$athlete" --days 7 >>"$LOG" 2>&1; then
    log "INGEST $athlete..."
    "$PY" ingest.py --athlete "$athlete" --name "$name" >>"$LOG" 2>&1 \
      && log "OK $athlete" || log "FOUT ingest $athlete (zie log)"
  else
    log "FOUT pull $athlete (zie log)"
  fi
}

log "=== sync start ==="
run_athlete vriendin Vriendin "${GARMIN_EMAIL_VRIENDIN:-}" "${GARMIN_PASSWORD_VRIENDIN:-}"
run_athlete rowan    Rowan    "${GARMIN_EMAIL_ROWAN:-}"    "${GARMIN_PASSWORD_ROWAN:-}"

# ingest.py schrijft naar lokale SQLite; push die naar Supabase (live dashboard).
# get_conn() is altijd SQLite, dus Postgres wordt uitsluitend hierlangs gevuld.
if [[ -n "${DATABASE_URL:-}" ]]; then
  log "PUSH -> Supabase..."
  "$PY" -c "from db import init_db; init_db()" >>"$LOG" 2>&1 \
    && "$PY" scripts/migrate_to_supabase.py >>"$LOG" 2>&1 \
    && log "OK push naar Supabase" || log "FOUT push naar Supabase (zie log)"
else
  log "SKIP push: DATABASE_URL leeg (data blijft in lokale SQLite)."
fi

# Dagelijkse bijsturing: roep het LIVE /adapt-endpoint aan (dat leest+schrijft Supabase,
# waar het plan leeft). adapt.py schrijft alleen lokale SQLite en is dus een dev-tool.
if [[ -n "${DATABASE_URL:-}" ]]; then
  log "ADAPT (dagelijkse bijsturing via live endpoint)..."
  BASE="https://garmin-coach-phi.vercel.app"
  for ath in vriendin rowan; do
    curl -s -m 40 -X POST "$BASE/api/athlete/$ath/adapt" >>"$LOG" 2>&1 && log "OK adapt $ath" || log "FOUT adapt $ath (zie log)"
  done
fi
log "=== sync klaar ==="
