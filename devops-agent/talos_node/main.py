from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import httpx
import json
import logging
import os
from contextlib import asynccontextmanager

# Configure structured logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("talos-gateway")

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
MCP_TOOLS_URL = os.getenv("MCP_TOOLS_URL", "http://mcp-tools:8000")
POLICY_PATH = os.getenv("TALOS_POLICY_PATH", "/app/config/capabilities.json")

# Load Policy
POLICY = {"capabilities": {"allow": [], "deny": []}}
if os.path.exists(POLICY_PATH):
    with open(POLICY_PATH, 'r') as f:
        POLICY = json.load(f)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting Talos Gateway. LLM: {OLLAMA_URL}, Tools: {MCP_TOOLS_URL}")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "mode": "gateway"}

# ==============================================================================
# LLM PROXY (Secure Inference)
# ==============================================================================
@app.post("/v1/chat/completions")
async def proxy_chat_completions(request: Request):
    """
    Proxies chat completion requests to Ollama, adding audit logging.
    """
    body = await request.json()
    model = body.get("model")
    
    # Audit Log: Inference Request
    logger.info(f"AUDIT_EVENT type=inference_request model={model} ip={request.client.host}")

    # Enforce basic policy (e.g., model allowlist - simplified)
    if not model.startswith("llama3.2") and not model.startswith("gpt"):
        # Allow default models for demo simplicity, but log warning
        logger.warning(f"Using non-standard model: {model}")

    async def forward_stream():
        async with httpx.AsyncClient() as client:
            # Note: Ollama supports /v1/chat/completions strictly
            req = client.build_request("POST", f"{OLLAMA_URL}/v1/chat/completions", json=body, timeout=60.0)
            r = await client.send(req, stream=True)
            async for chunk in r.aiter_bytes():
                yield chunk
            # In a real impl, we would count tokens here for accounting

    return StreamingResponse(forward_stream(), media_type="text/event-stream")

# ==============================================================================
# MCP TOOL GATEWAY (Secure Execution)
# ==============================================================================
@app.post("/mcp")
async def handle_mcp_request(request: Request):
    """
    Intercepts MCP JSON-RPC requests, checks capabilities, and forwards to tool server.
    """
    body = await request.json()
    method = body.get("method")
    params = body.get("params", {})
    
    # We only care about tool execution for policy enforcement
    # Standard MCP JSON-RPC: method="tools/call" (or similar depending on MCP version)
    # For this demo, we assume a simplified JSON-RPC or the specific MCP protocol payload
    # Let's assume the agent sends a structured "execute_tool" request or standard MCP `tools/call`.
    
    # Detect Tool Call
    tool_name = None
    if method == "tools/call":
        tool_name = params.get("name")
    elif method == "call_tool": # various implementations
        tool_name = params.get("name")
        
    if tool_name:
        # POLICY CHECK
        allowed = False
        denied = False
        
        # Check Deny List First
        for deny_pattern in POLICY["capabilities"]["deny"]:
            if deny_pattern == tool_name or (deny_pattern.endswith("*") and tool_name.startswith(deny_pattern[:-1])):
                denied = True
                break
        
        if not denied:
            for allow_pattern in POLICY["capabilities"]["allow"]:
                if allow_pattern == tool_name or (allow_pattern.endswith("*") and tool_name.startswith(allow_pattern[:-1])):
                    allowed = True
                    break
        
        # AUDIT DECISION
        if denied or not allowed:
            logger.error(f"AUDIT_EVENT type=tool_call tool={tool_name} decision=DENY reason={'explicit_deny' if denied else 'not_allowed'}")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {
                    "code": -32003,
                    "message": "TALOS_DENIED: You do not have permission to perform this action."
                }
            })
        
        logger.info(f"AUDIT_EVENT type=tool_call tool={tool_name} decision=ALLOW")

    # Forward to MCP Tools Server
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{MCP_TOOLS_URL}/mcp", json=body, timeout=30.0)
            return JSONResponse(response.json(), status_code=response.status_code)
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal Error: {str(e)}"
                }
            })
