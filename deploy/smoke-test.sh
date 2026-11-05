#!/usr/bin/env bash
# Smoke-test the app image with the login on: robots.txt and /healthz are public,
# everything else needs the password, and every response carries X-Robots-Tag.
#   deploy/smoke-test.sh [IMAGE]
set -euo pipefail
IMAGE="${1:-jalaforest-app:local}"
NAME="jalaforest-smoke-$$"
PORT=18080
USER_=smoke
PASS="smoke-$(date +%s)"
HASH="$(docker run --rm --entrypoint caddy "$IMAGE" hash-password --plaintext "$PASS")"
URL="http://127.0.0.1:${PORT}"

docker run -d --name "$NAME" -p "127.0.0.1:${PORT}:8080" -e PORT=8080 -e AI_ENABLED=false \
  -e BASIC_AUTH_USER="$USER_" -e BASIC_AUTH_HASH="$HASH" "$IMAGE" >/dev/null
trap 'docker rm -f "$NAME" >/dev/null 2>&1 || true' EXIT
for _ in $(seq 1 60); do curl -sf "$URL/healthz" >/dev/null && break; sleep 1; done

fail=0
check() {  # check DESCRIPTION EXPECTED ACTUAL
  if [ "$2" = "$3" ]; then echo "ok    $1"; else echo "FAIL  $1: expected $2, got $3"; fail=1; fi
}
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
check "robots.txt is public"          200 "$(code "$URL/robots.txt")"
check "robots.txt disallows all"      "Disallow: /" "$(curl -s "$URL/robots.txt" | grep -m1 -x 'Disallow: /')"
check "healthz is public"             ok  "$(curl -s "$URL/healthz")"
check "app needs login"               401 "$(code "$URL/")"
check "websocket needs login"         401 "$(code "$URL/_stcore/stream")"
check "wrong password is rejected"    401 "$(code -u "$USER_:wrong" "$URL/")"
check "right password is accepted"    200 "$(code -u "$USER_:$PASS" "$URL/")"
check "X-Robots-Tag on app"   1 "$(curl -s -D - -o /dev/null -u "$USER_:$PASS" "$URL/" | grep -ci '^x-robots-tag: noindex')"
check "X-Robots-Tag on 401"   1 "$(curl -s -D - -o /dev/null "$URL/" | grep -ci '^x-robots-tag: noindex')"
check "no Server header"      0 "$(curl -s -D - -o /dev/null "$URL/" | grep -ci '^server:' || true)"
exit "$fail"
