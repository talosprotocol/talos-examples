from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-tools")

# Detect Track
CLOUD_PROVIDER = os.getenv("CLOUD_PROVIDER", "aws").lower()
logger.info(f"Starting MCP Tools Server. Provider: {CLOUD_PROVIDER}")

# Initialize Providers
aws_provider = None
oss_minio = None
oss_faas = None

if CLOUD_PROVIDER == "aws":
    from mcp_tools.providers.aws_localstack import AWSProvider
    aws_provider = AWSProvider()
else:
    from mcp_tools.providers.oss_minio import MinioProvider
    from mcp_tools.providers.oss_openfaas import OpenFaaSProvider
    oss_minio = MinioProvider()
    oss_faas = OpenFaaSProvider()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok", "provider": CLOUD_PROVIDER}

@app.post("/mcp")
async def handle_mcp_call(request: Request):
    """
    Executes the tool call against the configured provider.
    """
    body = await request.json()
    # Simple JSON-RPC dispatch
    # method = body.get("method") # Unused
    params = body.get("params", {})
    
    request_id = body.get("id")
    
    # Assume "tools/call" or "call_tool"
    tool_name = params.get("name")
    tool_args = params.get("arguments", {})
    if not tool_args:
         tool_args = params # fallback if flattened

    logger.info(f"Executing Tool: {tool_name} Args: {tool_args}")
    
    try:
        result = {}
        if CLOUD_PROVIDER == "aws":
            result = aws_provider.execute(tool_name, tool_args)
        else:
            # Route OSS tools with unified naming or prefix
            if "s3" in tool_name or "minio" in tool_name:
                if "create" in tool_name:
                    result = oss_minio.create_bucket(tool_args.get("name"))
                elif "delete" in tool_name:
                    result = oss_minio.delete_bucket(tool_args.get("name"))
            elif "lambda" in tool_name or "faas" in tool_name:
                result = oss_faas.execute(tool_name, tool_args)
            else:
                raise ValueError(f"Unsupported tool for OSS track: {tool_name}")

        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        })
    except Exception as e:
        logger.error(f"Execution Error: {e}")
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        })
