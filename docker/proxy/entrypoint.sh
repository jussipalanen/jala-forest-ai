#!/bin/sh
# Runs Streamlit on an internal port and Caddy on $PORT (Cloud Run sets PORT).
# The container stops if either process exits, so Cloud Run restarts it.
set -eu

if [ -n "${BASIC_AUTH_USER:-}" ] && [ -n "${BASIC_AUTH_HASH:-}" ]; then
  export AUTH_MODE=on
else
  export AUTH_MODE=off
  echo "BASIC_AUTH_USER/BASIC_AUTH_HASH not set: password protection is OFF" >&2
fi

streamlit run app/streamlit_app.py \
  --server.headless true --server.address 127.0.0.1 --server.port 8502 \
  --server.enableXsrfProtection true &
st_pid=$!

caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &
caddy_pid=$!

trap 'kill "$st_pid" "$caddy_pid" 2>/dev/null || true' INT TERM
# Exit when either process stops.
while kill -0 "$st_pid" 2>/dev/null && kill -0 "$caddy_pid" 2>/dev/null; do
  sleep 2
done
kill "$st_pid" "$caddy_pid" 2>/dev/null || true
wait || true
exit 1
