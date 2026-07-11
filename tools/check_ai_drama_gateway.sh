#!/usr/bin/env bash
set -euo pipefail

WEB_LABEL="fun.deltadevalex.ai-drama-web"
FRPC_LABEL="fun.deltadevalex.frpc"
LOCAL_URL="http://127.0.0.1:8000/api/health"
PUBLIC_URL="https://assets.deltadevalex.fun/healthz"

launchd_state() {
  local label="$1"
  local output
  if ! output="$(launchctl print "gui/$(id -u)/${label}" 2>/dev/null)"; then
    printf 'missing'
    return 1
  fi
  printf '%s' "${output}" | awk '/state = / {print $3; found=1; exit} END {if (!found) print "loaded"}'
}

local_code="$(curl --noproxy '*' --connect-timeout 5 --max-time 15 -fsS -o /dev/null -w '%{http_code}' "${LOCAL_URL}")"
public_code="$(curl --noproxy '*' --connect-timeout 5 --max-time 15 -fsS -o /dev/null -w '%{http_code}' "${PUBLIC_URL}")"
web_state="$(launchd_state "${WEB_LABEL}")"
frpc_state="$(launchd_state "${FRPC_LABEL}")"

printf 'local_health=%s public_healthz=%s web=%s frpc=%s\n' "${local_code}" "${public_code}" "${web_state}" "${frpc_state}"

[[ "${local_code}" == "200" ]]
[[ "${public_code}" == "200" ]]
[[ "${web_state}" == "running" ]]
[[ "${frpc_state}" == "running" ]]
