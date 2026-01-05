#!/usr/bin/env python3
"""
Talos Secure Chat - FastAPI Server

REST API wrapper for SecureChatApp, enabling dashboard integration.

Endpoints:
    POST /v1/chat/send       - Send message, get AI response
    POST /v1/chat/feedback   - Submit feedback for last message
    GET  /v1/chat/stats      - Get conversation statistics
    GET  /v1/chat/summary    - Get security summary
    GET  /health             - Health check

Run:
    uvicorn server:app --host 0.0.0.0 --port 8100
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import asyncio
from typing import Optional

# Import the main chat app
from .main import SecureChatApp

app = FastAPI(
    title="Talos Secure Chat API",
    version="1.0.0",
    description="Secure AI chat with blockchain audit, ACL, and forward secrecy"
)

# CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to dashboard origin
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Singleton chat app instance
_chat_app: Optional[SecureChatApp] = None


def get_chat_app() -> SecureChatApp:
    """Get or create the singleton chat app."""
    global _chat_app
    if _chat_app is None:
        _chat_app = SecureChatApp()
    return _chat_app


# =============================================================================
# Request/Response Models
# =============================================================================

class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4096)


class SendMessageResponse(BaseModel):
    response: str
    message_id: str
    conversation_id: str
    secure: bool = True


class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(default="", max_length=1000)


class FeedbackResponse(BaseModel):
    status: str
    rating: int


class StatsResponse(BaseModel):
    conversations: int
    messages: int
    feedback_entries: int
    tool_calls: int
    avg_rating: float


class SummaryResponse(BaseModel):
    user_id: str
    assistant_id: str
    blockchain_height: int
    pending_data: int
    conversations: int
    messages: int
    tool_calls: int
    ollama_available: bool


class HealthResponse(BaseModel):
    status: str
    ollama: str
    version: str = "1.0.0"


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    chat_app = get_chat_app()
    ollama_ok = await chat_app.ollama.is_available()
    return HealthResponse(
        status="healthy" if ollama_ok else "degraded",
        ollama="online" if ollama_ok else "offline",
    )


@app.post("/v1/chat/send", response_model=SendMessageResponse)
async def send_message(req: SendMessageRequest):
    """Send a message and get AI response."""
    chat_app = get_chat_app()
    
    try:
        response = await chat_app.send_message(req.content)
        
        # Get the last message ID
        conv_id = chat_app.current_conv or ""
        messages = chat_app.db.get_history(conv_id, 1)
        msg_id = messages[-1].id if messages else ""
        
        return SendMessageResponse(
            response=response,
            message_id=msg_id,
            conversation_id=conv_id,
            secure=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/chat/feedback", response_model=FeedbackResponse)
async def submit_feedback(req: FeedbackRequest):
    """Submit feedback for the last message."""
    chat_app = get_chat_app()
    
    if not chat_app.current_conv:
        raise HTTPException(status_code=400, detail="No active conversation")
    
    try:
        result = await chat_app.submit_feedback(req.rating, req.comment)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return FeedbackResponse(
            status="recorded",
            rating=req.rating,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/chat/stats", response_model=StatsResponse)
async def get_stats():
    """Get conversation statistics."""
    chat_app = get_chat_app()
    stats = chat_app.db.get_stats()
    
    return StatsResponse(
        conversations=stats.get("conversations", 0),
        messages=stats.get("messages", 0),
        feedback_entries=stats.get("feedback_entries", 0),
        tool_calls=stats.get("tool_calls", 0),
        avg_rating=stats.get("avg_rating", 0.0),
    )


@app.get("/v1/chat/summary", response_model=SummaryResponse)
async def get_summary():
    """Get security summary."""
    chat_app = get_chat_app()
    summary = chat_app.get_summary()
    ollama_ok = await chat_app.ollama.is_available()
    
    return SummaryResponse(
        user_id=summary.get("user_id", ""),
        assistant_id=summary.get("assistant_id", ""),
        blockchain_height=summary.get("blockchain_height", 0),
        pending_data=summary.get("pending_data", 0),
        conversations=summary.get("conversations", 0),
        messages=summary.get("messages", 0),
        tool_calls=summary.get("tool_calls", 0),
        ollama_available=ollama_ok,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
