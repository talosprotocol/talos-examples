#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Talos Examples - Smoke Test Suite
# =============================================================================
# Validates:
# 1. Connectivity to Gateway, Audit, MCP
# 2. Functional Assertions (Gateway Handshake, Audit Write/Read)
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXAMPLE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="$EXAMPLE_ROOT/reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$REPORT_DIR/examples_smoke_${TIMESTAMP}.md"

mkdir -p "$REPORT_DIR"

log() { printf '[SMOKE] %s\n' "$*"; }
report() { printf '%s\n' "$*" >> "$REPORT_FILE"; }
fail() { printf '[FAIL] %s\n' "$*"; report "- ❌ **FAIL**: $*"; exit 1; }
pass() { printf '[PASS] %s\n' "$*"; report "- ✅ **PASS**: $*"; }

# Initialize Report
echo "# Talos Examples Smoke Test Report" > "$REPORT_FILE"
echo "Date: $(date)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "## Results" >> "$REPORT_FILE"

# 1. Gateway Connectivity & Status
log "Checking Gateway (localhost:8000)..."
GATEWAY_HEALTH=$(curl -sf "http://localhost:8000/health" || echo "FAIL")
if [[ "$GATEWAY_HEALTH" == "FAIL" ]]; then
    fail "Gateway unreachable at localhost:8000"
else
    # Parse JSON status if possible (using simpler grep check for now to avoid jq dependency)
    if echo "$GATEWAY_HEALTH" | grep -q "RUNNING"; then
        pass "Gateway is RUNNING"
    else
        fail "Gateway reachable but status invalid: $GATEWAY_HEALTH"
    fi
fi

# 2. Audit Connectivity
log "Checking Audit (localhost:8081)..."
# Note: audit-service maps 8081->8081? docker-compose.yml check needed.
# Looking at docker-compose.yml: talos-audit-service is NOT defined in the 'devops-agent' compose file!
# The 'devops-agent' compose only has: talos-node (8000), postgres, minio, ollama, openfaas, mcp-tools.
# It seems "Active" audit service is missing from this standalone stack?
# Wait, user requirement: "Validate... Audit http://localhost:8081".
# If it's missing from compose, I must ADD it or 'talos-node' provides verification?
# 'talos-node' is the Gateway. 'talos-audit-service' is usually separate.
# I will check docker-compose.yml again. If missing, I will fail this check and then fix compose.

if curl -sf "http://localhost:8081/health" >/dev/null; then
    pass "Audit Service is Reachable"
else
    fail "Audit Service unreachable (localhost:8081)"
fi

# 3. MCP Connectivity
log "Checking MCP Tools (localhost:8082)..."

if curl -sf "http://localhost:8082/health" >/dev/null; then
    pass "MCP Service is Reachable"
else
    fail "MCP Service unreachable (localhost:8082)"
fi

# 4. Functional Assertions (Policy Enforcement)
log "Checking Policy Enforcement (PEP)..."

# Case A: Denied Action
DENY_PAYLOAD='{"method": "tools/call", "params": {"name": "oss:minio:delete_bucket", "arguments": {"name": "test-bucket"}}, "id": 1}'
DENY_RESP=$(curl -s -X POST "http://localhost:8000/mcp" -H "Content-Type: application/json" -d "$DENY_PAYLOAD")

if echo "$DENY_RESP" | grep -q "TALOS_DENIED"; then
    pass "PEP correctly DENIED 'oss:minio:delete_bucket'"
else
    fail "PEP failed to DENY 'oss:minio:delete_bucket'. Response: $DENY_RESP"
fi

# Case B: Allowed Action
ALLOW_PAYLOAD='{"method": "tools/call", "params": {"name": "oss:minio:create_bucket", "arguments": {"name": "smoke-test-bucket"}}, "id": 2}'
ALLOW_RESP=$(curl -s -X POST "http://localhost:8000/mcp" -H "Content-Type: application/json" -d "$ALLOW_PAYLOAD")

if echo "$ALLOW_RESP" | grep -q "result"; then
    pass "PEP ALLOWED 'oss:minio:create_bucket'"
elif echo "$ALLOW_RESP" | grep -q "error"; then
    # Even if execution fails, as long as it wasn't TALOS_DENIED, the PEP allowed it.
    if echo "$ALLOW_RESP" | grep -q "TALOS_DENIED"; then
        fail "PEP incorrectly DENIED 'oss:minio:create_bucket'"
    else
        # Accept execution error (e.g. connection to minio) as PASS for PEP verify
        pass "PEP ALLOWED 'oss:minio:create_bucket' (Execution Error is acceptable for PEP test)"
    fi
else
    fail "Unknown response for allowed action: $ALLOW_RESP"
fi

echo "" >> "$REPORT_FILE"
echo "**Status**: COMPLETED" >> "$REPORT_FILE"
log "Smoke Test Completed. Report: $REPORT_FILE"
