# Security Proofs

This document contains evidence that the Security Invariants are being enforced.

## 1. Network Isolation Proof
*Evidence that the agent cannot reach the cloud directly.*

```bash
# From verify_isolation.sh
[PASS] Agent -> Ollama: Connection Timed Out (Expected)
[PASS] Agent -> LocalStack: Connection Timed Out (Expected)
```

## 2. Capability Denial Proof
*Evidence that a forbidden action was rejected by Talos.*

**Log Output (Talos Node):**
```json
{
  "timestamp": "2023-10-27T10:00:00Z",
  "component": "policy_engine",
  "event": "capability_cbeck",
  "request_id": "req-123",
  "session_id": "sess-abc",
  "tool": "aws:s3:delete_bucket",
  "decision": "DENY",
  "reason": "capability_not_found"
}
```

**Agent View:**
```text
Error calling tool 'aws:s3:delete_bucket': [403] TALOS_DENIED: You do not have permission to perform this action.
```

## 3. Tool Protection Proof
*Evidence that the tool server never received the denied request.*

**Log Output (MCP Tools):**
*No log entry found for req-123*
