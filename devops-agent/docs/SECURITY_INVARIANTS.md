# Security Invariants

These rules are non-negotiable. Any violation constitutes a security failure.

## 1. Zero Trust Network Isolation
*   **Invariant**: The `devops-agent` container MUST NOT have direct network access to Cloud resources (LocalStack, MinIO, OpenFaaS) or LLM resources (Ollama).
*   **Enforcement**: Docker networks `agent-net` (private) vs `cloud-net` (public). The agent is only attached to `agent-net`.
*   **Verification**: `scripts/verify_isolation.sh` must confirm `curl` timeouts from agent to cloud services.

## 2. No Credentials in Agent
*   **Invariant**: The `devops-agent` container MUST NOT possess any valid cloud credentials (AWS keys, MinIO keys).
*   **Enforcement**: Credentials are injected ONLY into the `mcp-tools` container.
*   **Verification**: Inspection of `devops-agent` environment variables.

## 3. Universal Control Plane
*   **Invariant**: ALL external side-effects (Tools) and ALL inference requests (LLM) MUST pass through the `talos-node` gateway.
*   **Enforcement**: 
    *   Agent is configured to use `http://talos-node:8000/v1` for LLM.
    *   Agent is configured to use `http://talos-node:8000/mcp` for Tools.
    *   No other outbound routes exist.

## 4. Deny-By-Default
*   **Invariant**: Any capability NOT explicitly allowed in `config/capabilities.json` MUST be denied by `talos-node`.
*   **Enforcement**: Talos Policy Engine checks every MCP request against the loaded capability set.
*   **Verification**: automated "Attack" scenario in `demo.sh` where `delete_bucket` is attempted and denied.

## 5. Audit Trail
*   **Invariant**: Every decision (Allow or Deny) MUST be logged with `session_id` and `request_id`.
*   **Enforcement**: `talos-node` emits structured logs for every transaction.
