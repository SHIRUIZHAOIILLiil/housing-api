from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from app.services import handle_chat_message

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        description="Short natural-language request that should map to one of the supported lookup tools.",
        examples=["latest rent E08000035"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "latest rent E08000035",
            }
        }
    }


class ChatResponse(BaseModel):
    reply: str = Field(..., description="Human-readable assistant reply.")
    tool_used: str | None = Field(default=None, description="Backend helper selected to satisfy the request, when one is used.")
    data: Any | None = Field(default=None, description="Structured payload returned by the helper tool.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "reply": "I found the latest rent stats for E08000035.",
                "tool_used": "get_latest_rent_stats",
                "data": {
                    "area_code": "E08000035",
                    "time_period": "2017-06",
                    "region_or_country_name": "Yorkshire and The Humber",
                },
            }
        }
    }

@router.post(
    "/ask",
    response_model=ChatResponse,
    summary="Run a chat-style lookup",
    description="Interpret a short natural-language request and route it to one of the supported postcode, area, rent, or sales helper tools.",
    responses={
        200: {"description": "Structured chat reply returned."},
        400: {"description": "Message could not be processed."},
        500: {"description": "Unexpected chat-service failure."},
    },
)
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
