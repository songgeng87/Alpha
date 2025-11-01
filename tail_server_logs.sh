#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -d logs ]]; then
  echo "No logs directory yet. Start the server first."
  exit 1
fi

LATEST_LOG=$(ls -1t logs/server_*.log 2>/dev/null | head -n1 || true)
if [[ -z "${LATEST_LOG}" ]]; then
  echo "No server logs found."
  exit 1
fi

echo "Tailing: ${LATEST_LOG}"

tail -f "${LATEST_LOG}"
