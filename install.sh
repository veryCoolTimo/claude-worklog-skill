#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
CONFIG_DIR="${HOME}/.config/worklog"

echo "==> Creating venv and installing the worklog CLI"
python3 -m venv "${REPO}/.venv"
"${REPO}/.venv/bin/pip" install -e "${REPO}"

echo "==> Linking the skill into ${CLAUDE_DIR}/skills/worklog"
mkdir -p "${CLAUDE_DIR}/skills"
ln -sfn "${REPO}/skill" "${CLAUDE_DIR}/skills/worklog"

echo "==> Preparing config dir ${CONFIG_DIR}"
mkdir -p "${CONFIG_DIR}"
[ -f "${CONFIG_DIR}/config.json" ] || cp "${REPO}/config.example.json" "${CONFIG_DIR}/config.json"

echo
echo "Next steps (manual):"
echo "  1. Put your service account key at ${CONFIG_DIR}/service-account.json"
echo "  2. Set spreadsheet_id in ${CONFIG_DIR}/config.json"
echo "  3. Make 'worklog' available on PATH, e.g.:"
echo "       ln -sfn ${REPO}/.venv/bin/worklog /usr/local/bin/worklog"
echo "  4. Register the SessionStart hook in ${CLAUDE_DIR}/settings.json (see docs/SETUP.md)"
