#!/usr/bin/env bash
set -euo pipefail

WEB_LABEL="fun.deltadevalex.ai-drama-web"
HEALTH_LABEL="fun.deltadevalex.ai-drama-health"
LAUNCHAGENTS_DIR="${HOME}/Library/LaunchAgents"
WEB_PLIST="${LAUNCHAGENTS_DIR}/${WEB_LABEL}.plist"
HEALTH_PLIST="${LAUNCHAGENTS_DIR}/${HEALTH_LABEL}.plist"

launchctl bootout "gui/$(id -u)" "${WEB_PLIST}" >/dev/null 2>&1 || true
launchctl bootout "gui/$(id -u)" "${HEALTH_PLIST}" >/dev/null 2>&1 || true

rm -f "${WEB_PLIST}" "${HEALTH_PLIST}"

printf 'Uninstalled %s\n' "${WEB_LABEL}"
printf 'Uninstalled %s\n' "${HEALTH_LABEL}"
