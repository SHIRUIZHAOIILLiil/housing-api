from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from app.services import handle_chat_message

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    tool_used: str | None = None
    data: Any | None = None

@router.post("/ask", response_model=ChatResponse)
def chat_ask(payload: ChatRequest):
    try:
        result = handle_chat_message(payload.message)
        return ChatResponse(
            reply=result["reply"],
            tool_used=result.get("tool_used"),
            data=result.get("data"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"chat error: {e}")