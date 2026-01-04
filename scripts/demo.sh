#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Talos Examples - Demo Harness
# =============================================================================
# Usage: ./demo.sh [up|down|smoke|full]
# Default: full (prepare -> up -> smoke -> down)
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXAMPLE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEVOPS_AGENT_DIR="$EXAMPLE_ROOT/devops-agent"
REPO_ROOT="$(cd "$EXAMPLE_ROOT/../../.." && pwd)"

MODE="${1:-full}"

log() { printf '[DEMO] %s\n' "$*"; }
error() { printf '[ERROR] %s\n' "$*" >&2; }

prepare() {
    log "Preparing workspace..."
    # Stage local SDKs for Docker build (Workspace Mode)
    local vendor_dir="$DEVOPS_AGENT_DIR/vendor"
    
    rm -rf "$vendor_dir"
    mkdir -p "$vendor_dir"
    
    # Python SDK
    local py_sdk="$REPO_ROOT/deploy/repos/talos-sdk-py"
    if [ -d "$py_sdk" ]; then
        log "Staging talos-sdk-py..."
        rsync -av --exclude 'venv' --exclude '__pycache__' --exclude '.git' \
            "$py_sdk" "$vendor_dir/" >/dev/null
    else
        error "talos-sdk-py not found at $py_sdk"
        exit 1
    fi

    # Audit Service
    local audit_svc="$REPO_ROOT/deploy/repos/talos-audit-service"
    if [ -d "$audit_svc" ]; then
        log "Staging talos-audit-service..."
        rsync -av --exclude 'venv' --exclude '__pycache__' --exclude '.git' \
            "$audit_svc" "$vendor_dir/" >/dev/null
    else
        error "talos-audit-service not found at $audit_svc"
        exit 1
    fi
    log "Staging complete."
    ls -la "$vendor_dir"
}

up() {
    prepare
    log "Starting Docker Stack..."
    cd "$DEVOPS_AGENT_DIR"
    docker compose --profile oss up -d --build --remove-orphans
    
    log "Waiting for health..."
    # Simple wait loop (docker compose wait is available in newer versions, but loop is safer)
    local retries=30
    local wait=2
    for ((i=1; i<=retries; i++)); do
        if docker compose --profile oss ps --format json | grep -q '"Health": "unhealthy"'; then
             error "Service unhealthy!"
             docker compose --profile oss ps
             exit 1
        fi
        
        # Check specific services
        if curl -sf "http://localhost:8000/health" >/dev/null; then
             log "Talos Node is UP!"
             return 0
        fi
        log "Waiting... ($i/$retries)"
        sleep "$wait"
    done
    error "Timed out waiting for stack."
    exit 1
}

down() {
    log "Stopping Docker Stack..."
    cd "$DEVOPS_AGENT_DIR"
    docker compose --profile oss down
    rm -rf vendor
}

smoke() {
    log "Running Smoke Tests..."
    "$SCRIPT_DIR/smoke.sh"
}

case "$MODE" in
    up)
        up
        ;;
    down)
        down
        ;;
    smoke)
        smoke
        ;;
    full)
        trap down EXIT
        up
        smoke
        ;;
    *)
        error "Unknown mode: $MODE"
        exit 1
        ;;
esac
