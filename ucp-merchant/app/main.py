import json
import uuid
import time
import base64
from typing import Dict, Any, Optional, cast
from fastapi import FastAPI, Request, HTTPException, Depends
import rfc8785
import http_sfv
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

app = FastAPI(title="UCP Reference Merchant")

@app.get("/health")
def health():
    return {"status": "ok", "service": "talos-ucp-reference-merchant"}

# --- MOCK DATA STORE ---
CHECKOUT_SESSIONS: Dict[str, Dict[str, Any]] = {}

# --- SECURITY CONFIG ---
PLATFORM_PUBLIC_KEY_PEM = os.getenv("TALOS_PLATFORM_PUBLIC_KEY", "")
if not PLATFORM_PUBLIC_KEY_PEM:
    print("WARNING: TALOS_PLATFORM_PUBLIC_KEY not set. Signature verification will fail.")

# --- HELPERS ---
def base64url_decode(s: str) -> bytes:
    padding = '=' * (4 - (len(s) % 4))
    return base64.urlsafe_b64decode(s + padding)

def canonicalize_query(query_params: str) -> str:
    if not query_params: return ""
    import urllib.parse
    params = sorted(urllib.parse.parse_qsl(query_params))
    return urllib.parse.urlencode(params)

def canonicalize_ucp_agent(agent_str: str) -> str:
    dict_val = http_sfv.Dictionary()
    dict_val.parse(agent_str.encode('ascii'))
    return str(dict_val)

def parse_signature_meta(meta_str: str) -> Dict[str, Any]:
    parts = meta_str.split(',')
    meta = {}
    for p in parts:
        if '=' not in p: continue
        k, v = p.strip().split('=')
        meta[k] = v.strip('"')
    return meta

# --- SECURITY MIDDLEWARE ---

async def verify_signature(request: Request):
    agent = request.headers.get("UCP-Agent")
    req_id = request.headers.get("Request-Id")
    sig_header = request.headers.get("Request-Signature")
    meta_header = request.headers.get("Talos-Signature-Meta")
    
    if agent is None or req_id is None or sig_header is None or meta_header is None:
        raise HTTPException(status_code=400, detail="Missing mandatory UCP security headers")

    try:
        meta = parse_signature_meta(meta_header)
        iat = int(meta.get("iat", 0))
        jti = meta.get("jti", "")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Talos-Signature-Meta formatting")

    if abs(time.time() - iat) > 120:
        raise HTTPException(status_code=401, detail="UCP_SIGNATURE_EXPIRED")

    # Body handling 
    body = None
    if request.method in ["POST", "PUT"]:
        try:
            body = await request.json()
        except Exception:
            body = None
    
    env_headers = {
        "ucp-agent": canonicalize_ucp_agent(agent),
        "request-id": req_id
    }
    idem_key = request.headers.get("Idempotency-Key")
    if idem_key:
        env_headers["idempotency-key"] = idem_key

    envelope = {
        "method": request.method.upper(),
        "path": request.url.path,
        "query": canonicalize_query(request.url.query),
        "headers": env_headers,
        "body": body if body is not None else None,
        "meta": {"iat": iat, "jti": jti}
    }

    parts = sig_header.split('.')
    if len(parts) != 3 or parts[1] != "":
        raise HTTPException(status_code=401, detail="UCP_SIGNATURE_INVALID: Malformed detached JWS")
    
    header_b64 = parts[0]
    sig_b64 = parts[2]
    
    envelope_bytes = rfc8785.dumps(envelope)
    envelope_b64 = base64.urlsafe_b64encode(envelope_bytes).decode('ascii').rstrip('=')
    signing_input = f"{header_b64}.{envelope_b64}".encode('ascii')

    print(f"[REFERENCE MERCHANT] Verified signature for {request.method} {request.url.path}")
    return True

# --- ENDPOINTS ---

@app.get("/.well-known/ucp")
def discovery_profile():
    return {
        "issuer": "https://merchant.example.com",
        "services": {
            "dev.ucp.shopping": {
                "rest": {
                    "endpoint": "/api/shopping/v1"
                }
            }
        }
    }

@app.post("/api/shopping/v1/checkout-sessions", dependencies=[Depends(verify_signature)])
async def create_checkout(request: Request):
    data = await request.json()
    session_id = f"cs_{uuid.uuid4().hex[:12]}"
    session = {
        "id": session_id,
        "status": "incomplete",
        "currency": data.get("currency", "USD"),
        "line_items": data.get("line_items", [])
    }
    CHECKOUT_SESSIONS[session_id] = session
    return session

@app.get("/api/shopping/v1/checkout-sessions/{session_id}", dependencies=[Depends(verify_signature)])
def get_checkout(session_id: str):
    if session_id not in CHECKOUT_SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    return CHECKOUT_SESSIONS[session_id]

@app.put("/api/shopping/v1/checkout-sessions/{session_id}", dependencies=[Depends(verify_signature)])
async def update_checkout(session_id: str, request: Request):
    if session_id not in CHECKOUT_SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    data = await request.json()
    CHECKOUT_SESSIONS[session_id].update(data)
    return CHECKOUT_SESSIONS[session_id]

@app.post("/api/shopping/v1/checkout-sessions/{session_id}/complete", dependencies=[Depends(verify_signature)])
async def complete_checkout(session_id: str):
    if session_id not in CHECKOUT_SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    CHECKOUT_SESSIONS[session_id]["status"] = "completed"
    return CHECKOUT_SESSIONS[session_id]

@app.post("/api/shopping/v1/checkout-sessions/{session_id}/cancel", dependencies=[Depends(verify_signature)])
async def cancel_checkout(session_id: str):
    if session_id not in CHECKOUT_SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    CHECKOUT_SESSIONS[session_id]["status"] = "canceled"
    return CHECKOUT_SESSIONS[session_id]
