#!/usr/bin/env bash
# Secure Chat Server - Stop Script
# Reads PID from file and cleanly shuts down

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="${SCRIPT_DIR}/../../../.demo"
PID_FILE="${DEMO_DIR}/secure_chat.pid"

if [[ ! -f "${PID_FILE}" ]]; then
    echo "Secure Chat not running (no PID file)"
    exit 0
fi

PID=$(cat "${PID_FILE}")

if kill -0 "${PID}" 2>/dev/null; then
    echo "Stopping Secure Chat (PID: ${PID})..."
    kill "${PID}"
    rm -f "${PID_FILE}"
    echo "Secure Chat stopped"
else
    echo "Secure Chat process not found, cleaning up PID file"
    rm -f "${PID_FILE}"
fi
