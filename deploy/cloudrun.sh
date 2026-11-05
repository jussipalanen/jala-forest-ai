#!/usr/bin/env bash
# Deploy the map app to Cloud Run at minimal cost. Idempotent: safe to re-run.
#
#   deploy/cloudrun.sh                 # build, push and deploy
#   deploy/cloudrun.sh --new-password  # also generate a new login password
#
# Settings (override with environment variables):
PROJECT="${PROJECT:-client-jussialanen}"
REGION="${REGION:-europe-north1}"
SERVICE="${SERVICE:-jalaforest}"
REPO="${REPO:-jalaforest}"
LOGIN_USER="${LOGIN_USER:-jalaforest}"
BUDGET_AMOUNT="${BUDGET_AMOUNT:-1}"   # monthly budget alert, in the billing account's currency

set -euo pipefail
cd "$(dirname "$0")/.."

SA="${SERVICE}-run@${PROJECT}.iam.gserviceaccount.com"
SECRET_GEMINI="${SERVICE}-gemini-api-key"
SECRET_HASH="${SERVICE}-basic-auth-hash"
SECRET_PASSWORD="${SERVICE}-basic-auth-password"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/app:$(git rev-parse --short HEAD)$(git diff --quiet || echo -dirty)"
G=(gcloud --project "$PROJECT" --quiet)

new_password=false
[ "${1:-}" = "--new-password" ] && new_password=true

step() { printf '\n==> %s\n' "$*"; }
secret_exists() { "${G[@]}" secrets describe "$1" >/dev/null 2>&1; }
add_secret() {  # add_secret NAME VALUE: create on first use, then add a version (old ones disabled)
  if secret_exists "$1"; then
    printf '%s' "$2" | "${G[@]}" secrets versions add "$1" --data-file=- >/dev/null
    "${G[@]}" secrets versions list "$1" --filter='state=ENABLED' --format='value(name)' --sort-by=~createTime \
      | tail -n +2 | while read -r v; do "${G[@]}" secrets versions disable "$v" --secret "$1" >/dev/null; done
  else
    printf '%s' "$2" | "${G[@]}" secrets create "$1" --replication-policy=automatic \
      --labels="app=${SERVICE}" --data-file=- >/dev/null
  fi
}

[ -f data/export/stand_natura_overlap.parquet ] || { echo "Missing data/export: run ./dev run first" >&2; exit 1; }

step "APIs"
"${G[@]}" services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com \
  billingbudgets.googleapis.com >/dev/null

step "Artifact Registry ${REPO} (keeps the 2 newest images; 0.5 GB is free)"
if ! "${G[@]}" artifacts repositories describe "$REPO" --location "$REGION" >/dev/null 2>&1; then
  "${G[@]}" artifacts repositories create "$REPO" --location "$REGION" --repository-format docker \
    --labels="app=${SERVICE}" --description "JalaForest map app images" >/dev/null
fi
"${G[@]}" artifacts repositories set-cleanup-policies "$REPO" --location "$REGION" --no-dry-run \
  --policy deploy/artifact-cleanup-policy.json >/dev/null

step "Secrets"
if ! secret_exists "$SECRET_GEMINI"; then
  key="${GEMINI_API_KEY:-$(grep -E '^GEMINI_API_KEY=' .env 2>/dev/null | cut -d= -f2-)}"
  [ -n "$key" ] || { echo "Set GEMINI_API_KEY (or add it to .env) for the first deploy" >&2; exit 1; }
  add_secret "$SECRET_GEMINI" "$key"
fi
if $new_password || ! secret_exists "$SECRET_HASH"; then
  password="$(python3 -c 'import secrets; print(secrets.token_urlsafe(18))')"
  hash="$(docker run --rm caddy:2.11.8-alpine caddy hash-password --plaintext "$password")"
  add_secret "$SECRET_PASSWORD" "$password"
  add_secret "$SECRET_HASH" "$hash"
  echo "New login password stored in Secret Manager ($SECRET_PASSWORD)."
fi

step "Service account ${SA} (reads only this service's secrets)"
"${G[@]}" iam service-accounts describe "$SA" >/dev/null 2>&1 ||
  "${G[@]}" iam service-accounts create "${SERVICE}-run" --display-name "JalaForest Cloud Run" >/dev/null
for s in "$SECRET_GEMINI" "$SECRET_HASH"; do
  # A just-created service account can take a moment to become visible to IAM.
  for attempt in 1 2 3 4 5 6; do
    if "${G[@]}" secrets add-iam-policy-binding "$s" --member "serviceAccount:${SA}" \
        --role roles/secretmanager.secretAccessor >/dev/null 2>&1; then
      break
    fi
    [ "$attempt" -lt 6 ] || { echo "Could not grant ${SA} access to ${s}" >&2; exit 1; }
    sleep 10
  done
done

step "Build and push ${IMAGE}"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet >/dev/null 2>&1
docker build --platform linux/amd64 -t "$IMAGE" .
docker push "$IMAGE"

step "Deploy ${SERVICE} (scale to zero, max 1 instance, request-based billing)"
"${G[@]}" run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --service-account "$SA" \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 1 --memory 1Gi \
  --min-instances 0 --max-instances 1 \
  --concurrency 20 \
  --cpu-throttling --no-cpu-boost \
  --timeout 3600 \
  --session-affinity \
  --labels "app=${SERVICE}" \
  --set-env-vars "BASIC_AUTH_USER=${LOGIN_USER},AI_ENABLED=true" \
  --set-secrets "GEMINI_API_KEY=${SECRET_GEMINI}:latest,BASIC_AUTH_HASH=${SECRET_HASH}:latest"

step "Budget alert (${BUDGET_AMOUNT} per month, resources labelled app=${SERVICE})"
billing="$(gcloud billing projects describe "$PROJECT" --format='value(billingAccountName)' | sed 's|billingAccounts/||')"
budget_name="${SERVICE} monthly"
if ! gcloud billing budgets list --billing-account "$billing" --format='value(displayName)' 2>/dev/null \
    | grep -qx "$budget_name"; then
  gcloud billing budgets create --billing-account "$billing" --display-name "$budget_name" \
    --budget-amount "${BUDGET_AMOUNT}" --filter-projects "projects/${PROJECT}" \
    --filter-labels "app=${SERVICE}" \
    --threshold-rule percent=0.5 --threshold-rule percent=1.0 >/dev/null
fi

url="$("${G[@]}" run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
step "Done"
cat <<EOF
URL:        ${url}
Login:      ${LOGIN_USER} / password: gcloud secrets versions access latest --secret ${SECRET_PASSWORD} --project ${PROJECT}
Health:     ${url}/healthz   (for UptimeRobot, no login; answers "ok")
robots.txt: ${url}/robots.txt
EOF
