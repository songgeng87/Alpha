#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PID_FILE="server.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No PID file found. Server not running?"
  exit 0
fi

PID=$(cat "$PID_FILE")
if ps -p "$PID" > /dev/null 2>&1; then
  echo "Stopping server (PID=$PID) ..."
  kill "$PID" || true
  # 最多等待 10 秒
  for i in {1..10}; do
    if ps -p "$PID" > /dev/null 2>&1; then
      sleep 1
    else
      break
    fi
  done
  if ps -p "$PID" > /dev/null 2>&1; then
    echo "Force killing server (PID=$PID) ..."
    kill -9 "$PID" || true
  fi
  echo "Server stopped."
else
  echo "No running process with PID $PID. Cleaning up."
fi

rm -f "$PID_FILE"
