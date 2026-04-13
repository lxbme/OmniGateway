import time
import uuid

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from app.api.schemas import ChatCompletionRequest
from app.services.llm_service import llm_service


router = APIRouter(tags=["Chat"])

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    if request.stream is True:
        return StreamingResponse(
            llm_service.stream_chat(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    model_name = llm_service.resolve_model(request.model)
    messages = llm_service.build_messages(request)
    content = await llm_service.generate_reply(
        messages=messages,
        model=request.model,
        temperature=request.temperature,
    )

    payload = {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
    }
    return JSONResponse(content=payload)
