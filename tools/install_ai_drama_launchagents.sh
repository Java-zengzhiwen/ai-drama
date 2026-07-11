#!/usr/bin/env bash
set -euo pipefail

WEB_LABEL="fun.deltadevalex.ai-drama-web"
HEALTH_LABEL="fun.deltadevalex.ai-drama-health"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
AI_DRAMA_WEB_BIN="${PROJECT_ROOT}/.venv/bin/ai-drama-web"
DATA_ROOT="${PROJECT_ROOT}/runtime-data"
SKILLS_ROOT="${PROJECT_ROOT}/skills"
SECRET_FILE="${DATA_ROOT}/secrets/agnes-api-key"
LAUNCHAGENTS_DIR="${HOME}/Library/LaunchAgents"
WEB_PLIST="${LAUNCHAGENTS_DIR}/${WEB_LABEL}.plist"
HEALTH_PLIST="${LAUNCHAGENTS_DIR}/${HEALTH_LABEL}.plist"

require_path() {
  local path="$1"
  local label="$2"
  if [[ ! -e "${path}" ]]; then
    printf 'missing %s: %s\n' "${label}" "${path}" >&2
    exit 1
  fi
}

xml_escape() {
  local value="$1"
  value="${value//&/&amp;}"
  value="${value//</&lt;}"
  value="${value//>/&gt;}"
  value="${value//\"/&quot;}"
  value="${value//\'/&apos;}"
  printf '%s' "${value}"
}

render_template() {
  local template="$1"
  local output="$2"
  local project_root_escaped
  local home_escaped
  local web_bin_escaped
  project_root_escaped="$(xml_escape "${PROJECT_ROOT}")"
  home_escaped="$(xml_escape "${HOME}")"
  web_bin_escaped="$(xml_escape "${AI_DRAMA_WEB_BIN}")"

  awk \
    -v project_root="${project_root_escaped}" \
    -v home_dir="${home_escaped}" \
    -v web_bin="${web_bin_escaped}" \
    '{
      gsub("__PROJECT_ROOT__", project_root)
      gsub("__HOME__", home_dir)
      gsub("__AI_DRAMA_WEB_BIN__", web_bin)
      print
    }' "${template}" > "${output}"
}

require_path "${AI_DRAMA_WEB_BIN}" "ai-drama-web executable"
require_path "${DATA_ROOT}" "runtime data root"
require_path "${SKILLS_ROOT}" "skills root"
require_path "${SECRET_FILE}" "Agnes secret file"

secret_mode="$(stat -f '%Lp' "${SECRET_FILE}")"
if [[ "${secret_mode}" != "600" ]]; then
  printf 'invalid Agnes secret file mode: %s\n' "${secret_mode}" >&2
  exit 1
fi
printf 'Agnes configured=true\n'

mkdir -p "${LAUNCHAGENTS_DIR}"
mkdir -p "${HOME}/Library/Logs/ai-drama-web"
mkdir -p "${HOME}/Library/Logs/ai-drama-health"

chmod 755 "${PROJECT_ROOT}/tools/install_ai_drama_launchagents.sh"
chmod 755 "${PROJECT_ROOT}/tools/uninstall_ai_drama_launchagents.sh"
chmod 755 "${PROJECT_ROOT}/tools/check_ai_drama_gateway.sh"

render_template "${PROJECT_ROOT}/ops/launchd/${WEB_LABEL}.plist.template" "${WEB_PLIST}"
render_template "${PROJECT_ROOT}/ops/launchd/${HEALTH_LABEL}.plist.template" "${HEALTH_PLIST}"

chmod 644 "${WEB_PLIST}" "${HEALTH_PLIST}"
plutil -lint "${WEB_PLIST}" >/dev/null
plutil -lint "${HEALTH_PLIST}" >/dev/null

launchctl bootout "gui/$(id -u)" "${WEB_PLIST}" >/dev/null 2>&1 || true
launchctl bootout "gui/$(id -u)" "${HEALTH_PLIST}" >/dev/null 2>&1 || true

launchctl bootstrap "gui/$(id -u)" "${WEB_PLIST}"
launchctl bootstrap "gui/$(id -u)" "${HEALTH_PLIST}"
launchctl kickstart -k "gui/$(id -u)/${WEB_LABEL}"

printf 'Installed %s\n' "${WEB_PLIST}"
printf 'Installed %s\n' "${HEALTH_PLIST}"
