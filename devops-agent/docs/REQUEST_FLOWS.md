# Request Flows

## 1. Secure Inference Flow (LLM)

The Agent needs to "think". It sends a prompt to the LLM.

```mermaid
sequenceDiagram
    participant Agent as DevOps Agent
    participant Talos as Talos Gateway
    participant Ollama as Ollama (LLM)

    Note over Agent,Ollama: Network: agent-net -> llm-net
    
    Agent->>Talos: POST /v1/chat/completions (Prompt)
    Note right of Agent: Auth: Session Token
    
    Talos->>Talos: 1. Verify Session
    Talos->>Talos: 2. Apply Rate Limits
    Talos->>Talos: 3. Audit Log (Inference Request)
    
    Talos->>Ollama: POST /v1/chat/completions
    Ollama-->>Talos: Response (Tokens)
    
    Talos->>Talos: 4. Audit Log (Token Usage)
    Talos-->>Agent: Response (Tokens)
```

## 2. Secure Execution Flow (MCP Tools)

The Agent needs to "act". It calls a tool (e.g., `aws:s3:create_bucket`).

```mermaid
sequenceDiagram
    participant Agent as DevOps Agent
    participant Talos as Talos Gateway
    participant Tools as MCP Tools
    participant Cloud as Cloud (AWS/OSS)

    Note over Agent,Cloud: Network: agent-net -> control-plane -> cloud-net

    Agent->>Talos: POST /mcp (Call Tool: create_bucket)
    Note right of Agent: Auth: Capability Token
    
    Talos->>Talos: 1. Verify Capability (aws:s3:create_bucket)
    
    alt Denied
        Talos-->>Agent: 403 Forbidden (TALOS_DENIED)
        Note right of Talos: Log: DENY
    else Allowed
        Note right of Talos: Log: ALLOW
        Talos->>Tools: Fwd: create_bucket
        Tools->>Cloud: Boto3/MinClient API Call
        Cloud-->>Tools: Success/Fail
        Tools-->>Talos: Tool Result
        Talos-->>Agent: Tool Result
    end
```
