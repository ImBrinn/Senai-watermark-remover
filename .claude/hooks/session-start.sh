#!/bin/bash
# Claude Code cloud sessions: installs what the tests, linter and screenshot
# tools need. The container is cached after this runs, so later sessions
# start quickly. Does nothing on your own computer.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"

# Qt's runtime libraries (PySide6 needs them even when drawing offscreen).
if ! ldconfig -p | grep -q 'libEGL.so.1' || ! ldconfig -p | grep -q 'libxkbcommon.so.0'; then
  sudo=""
  [ "$(id -u)" -ne 0 ] && sudo="sudo"
  export DEBIAN_FRONTEND=noninteractive
  $sudo apt-get update -qq || true
  $sudo apt-get install -y -qq libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3 >/dev/null
fi

# The package itself (editable), the GUI and test extras, and the linter.
python3 -m pip install --quiet --disable-pip-version-check --root-user-action=ignore \
  -e ".[gui,test]" pyflakes

# Qt has no display in the cloud; draw offscreen for tests and screenshots.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo 'export QT_QPA_PLATFORM=offscreen' >> "$CLAUDE_ENV_FILE"
fi
