#!/usr/bin/env bash
# DevOps Agent - Start Script
# Uses Docker Compose and writes container ID for tracking

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="${SCRIPT_DIR}/../../../.demo"
CONTAINER_FILE="${DEMO_DIR}/devops_agent.container"
PORT="${DEVOPS_AGENT_PORT:-8200}"

mkdir -p "${DEMO_DIR}"

# Check if already running
if [[ -f "${CONTAINER_FILE}" ]]; then
    CONTAINER_ID=$(cat "${CONTAINER_FILE}")
    if docker ps -q --filter "id=${CONTAINER_ID}" | grep -q .; then
        echo "DevOps Agent already running (container: ${CONTAINER_ID:0:12})"
        exit 0
    fi
    rm -f "${CONTAINER_FILE}"
fi

cd "${SCRIPT_DIR}/.."

echo "Starting DevOps Agent on port ${PORT}..."
docker compose up -d

# Get the API container ID
CONTAINER_ID=$(docker compose ps -q dashboard-api 2>/dev/null || docker compose ps -q agent 2>/dev/null || echo "")

if [[ -n "${CONTAINER_ID}" ]]; then
    echo "${CONTAINER_ID}" > "${CONTAINER_FILE}"
    echo "DevOps Agent started (container: ${CONTAINER_ID:0:12})"
else
    echo "DevOps Agent containers started (compose mode)"
    echo "compose" > "${CONTAINER_FILE}"
fi
