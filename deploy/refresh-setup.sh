#!/usr/bin/env bash
# Set up the scheduled data refresh (idempotent):
#   Cloud Scheduler (weekly) -> Cloud Build: import into Neon -> build image -> deploy.
#
#   deploy/refresh-setup.sh          # create or update everything
#   deploy/refresh-setup.sh --run    # also start one refresh now
#
# Needs DATABASE_URL (the Neon direct connection string) in .env for the first run.
PROJECT="${PROJECT:-client-jussialanen}"
REGION="${REGION:-europe-north1}"
SERVICE="${SERVICE:-jalaforest}"
REPO="${REPO:-jalaforest}"
REPO_URL="${REPO_URL:-https://github.com/jussipalanen/jala-forest-ai.git}"
GIT_REF="${GIT_REF:-main}"
SCHEDULE="${SCHEDULE:-0 5 * * 1}"        # Mondays 05:00
TIME_ZONE="${TIME_ZONE:-Europe/Helsinki}"
# Cloud Scheduler is not offered in europe-north1; it only triggers the build, so any region works.
SCHEDULER_LOCATION="${SCHEDULER_LOCATION:-europe-west1}"

set -euo pipefail
cd "$(dirname "$0")/.."

BUILD_SA="${SERVICE}-build@${PROJECT}.iam.gserviceaccount.com"
RUN_SA="${SERVICE}-run@${PROJECT}.iam.gserviceaccount.com"
SECRET_DB="${SERVICE}-database-url"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/app"
JOB="${SERVICE}-data-refresh"
G=(gcloud --project "$PROJECT" --quiet)

step() { printf '\n==> %s\n' "$*"; }
retry() {  # retry CMD...: IAM changes for a new service account can take a moment to apply
  for attempt in 1 2 3 4 5 6; do
    if "$@" >/dev/null 2>&1; then return 0; fi
    [ "$attempt" -lt 6 ] || { echo "Failed: $*" >&2; return 1; }
    sleep 10
  done
}

step "APIs"
"${G[@]}" services enable cloudscheduler.googleapis.com cloudbuild.googleapis.com >/dev/null

step "Secret ${SECRET_DB}"
if ! "${G[@]}" secrets describe "$SECRET_DB" >/dev/null 2>&1; then
  url="${DATABASE_URL:-$(grep -E '^DATABASE_URL=' .env 2>/dev/null | cut -d= -f2-)}"
  [ -n "$url" ] || { echo "Set DATABASE_URL (or add it to .env) for the first run" >&2; exit 1; }
  case "$url" in *-pooler.*) echo "Use Neon's direct connection string (without -pooler)" >&2; exit 1 ;; esac
  printf '%s' "$url" | "${G[@]}" secrets create "$SECRET_DB" --replication-policy=automatic \
    --labels="app=${SERVICE}" --data-file=- >/dev/null
  echo "Stored the database URL in Secret Manager."
fi

step "Service account ${BUILD_SA} (only what the refresh needs)"
"${G[@]}" iam service-accounts describe "$BUILD_SA" >/dev/null 2>&1 ||
  "${G[@]}" iam service-accounts create "${SERVICE}-build" --display-name "JalaForest data refresh" >/dev/null
member="serviceAccount:${BUILD_SA}"
retry "${G[@]}" secrets add-iam-policy-binding "$SECRET_DB" --member "$member" --role roles/secretmanager.secretAccessor
retry "${G[@]}" artifacts repositories add-iam-policy-binding "$REPO" --location "$REGION" --member "$member" \
  --role roles/artifactregistry.writer
retry "${G[@]}" run services add-iam-policy-binding "$SERVICE" --region "$REGION" --member "$member" \
  --role roles/run.developer
# Deploying a revision that runs as the app's service account, and starting builds as itself.
retry "${G[@]}" iam service-accounts add-iam-policy-binding "$RUN_SA" --member "$member" --role roles/iam.serviceAccountUser
retry "${G[@]}" iam service-accounts add-iam-policy-binding "$BUILD_SA" --member "$member" --role roles/iam.serviceAccountUser
retry "${G[@]}" projects add-iam-policy-binding "$PROJECT" --member "$member" --role roles/logging.logWriter --condition=None
retry "${G[@]}" projects add-iam-policy-binding "$PROJECT" --member "$member" --role roles/cloudbuild.builds.editor --condition=None

step "Build definition"
build_json="$(mktemp)"
trap 'rm -f "$build_json"' EXIT
python3 - "$build_json" <<PY
import json, sys
text = open("deploy/refresh-build.json").read()
for key, value in {"@PROJECT@": "$PROJECT", "@REGION@": "$REGION", "@SERVICE@": "$SERVICE", "@IMAGE@": "$IMAGE",
                   "@BUILD_SA@": "$BUILD_SA", "@REPO_URL@": "$REPO_URL", "@GIT_REF@": "$GIT_REF"}.items():
    text = text.replace(key, value)
build = json.loads(text)
build.pop("//", None)
import re
assert not re.search(r"@[A-Z_]+@", json.dumps(build)), "unfilled placeholder"
json.dump(build, open(sys.argv[1], "w"))
PY

step "Cloud Scheduler ${JOB} (${SCHEDULE}, ${TIME_ZONE})"
uri="https://cloudbuild.googleapis.com/v1/projects/${PROJECT}/builds"
action=create
"${G[@]}" scheduler jobs describe "$JOB" --location "$SCHEDULER_LOCATION" >/dev/null 2>&1 && action=update
"${G[@]}" scheduler jobs "$action" http "$JOB" --location "$SCHEDULER_LOCATION" \
  --schedule "$SCHEDULE" --time-zone "$TIME_ZONE" \
  --uri "$uri" --http-method POST \
  --message-body-from-file "$build_json" \
  --oauth-service-account-email "$BUILD_SA" \
  --oauth-token-scope "https://www.googleapis.com/auth/cloud-platform" \
  --attempt-deadline 60s \
  --description "Weekly JalaForest data refresh: Neon import, image build and deploy" >/dev/null

if [ "${1:-}" = "--run" ]; then
  step "Starting one refresh now"
  "${G[@]}" scheduler jobs run "$JOB" --location "$SCHEDULER_LOCATION"
  echo "Follow it: gcloud builds list --project ${PROJECT} --filter='tags=data-refresh' --limit 3"
fi
step "Done"
