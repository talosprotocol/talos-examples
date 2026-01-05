#!/usr/bin/env bash
# DevOps Agent - Stop Script
# Stops Docker Compose stack

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="${SCRIPT_DIR}/../../../.demo"
CONTAINER_FILE="${DEMO_DIR}/devops_agent.container"

cd "${SCRIPT_DIR}/.."

echo "Stopping DevOps Agent..."
docker compose down

if [[ -f "${CONTAINER_FILE}" ]]; then
    rm -f "${CONTAINER_FILE}"
fi

echo "DevOps Agent stopped"
