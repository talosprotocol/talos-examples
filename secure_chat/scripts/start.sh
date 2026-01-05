#!/usr/bin/env bash
# Secure Chat Server - Start Script
# Writes PID to file for clean shutdown

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="${SCRIPT_DIR}/../../../.demo"
PID_FILE="${DEMO_DIR}/secure_chat.pid"
PORT="${SECURE_CHAT_PORT:-8100}"

mkdir -p "${DEMO_DIR}"

# Check if already running
if [[ -f "${PID_FILE}" ]]; then
    if kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
        echo "Secure Chat already running (PID: $(cat "${PID_FILE}"))"
        exit 0
    fi
    rm -f "${PID_FILE}"
fi

cd "${SCRIPT_DIR}/.."

echo "Starting Secure Chat server on port ${PORT}..."
uvicorn server:app --host 0.0.0.0 --port "${PORT}" &
echo $! > "${PID_FILE}"

echo "Secure Chat started (PID: $(cat "${PID_FILE}"))"
