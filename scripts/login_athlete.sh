#!/usr/bin/env bash
# Eenmalige interactieve eerste-login voor een atleet -> maakt .garmin_tokens/<athlete>/.
# Draait in de VOORGROND zodat een eventuele Garmin MFA-code gevraagd kan worden.
# Gebruik:  ./scripts/login_athlete.sh rowan
# Daarna doet de dagelijkse launchd-sync token-login (geen creds/MFA meer nodig).
set -uo pipefail

ATHLETE="${1:?Gebruik: ./scripts/login_athlete.sh <athlete>  (bv. rowan)}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
PY="$REPO/.venv/bin/python"

[[ -f .env ]] && { set -a; source .env; set +a; }

UP="$(echo "$ATHLETE" | tr '[:lower:]' '[:upper:]')"
email_var="GARMIN_EMAIL_${UP}"
pass_var="GARMIN_PASSWORD_${UP}"

export GARMIN_EMAIL="${!email_var:-}"
export GARMIN_PASSWORD="${!pass_var:-}"

if [[ -z "$GARMIN_EMAIL" || -z "$GARMIN_PASSWORD" ]]; then
  echo "Geen creds in .env voor $ATHLETE (${email_var} / ${pass_var})."
  echo "Vul die eerst in .env, of je wordt nu gevraagd:"
fi

echo "Interactieve login voor '$ATHLETE'. Bij MFA: voer de code in als gevraagd."
"$PY" garmin_test_pull.py --athlete "$ATHLETE" --days 7
echo
echo "Klaar. Tokens: .garmin_tokens/$ATHLETE/  ->  launchd-sync gebruikt ze voortaan."
