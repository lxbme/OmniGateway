import json
import os
import time
import uuid
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from dotenv import load_dotenv
from app.api.schemas import ChatCompletionRequest

# 加载 .env 文件中的环境变量 (这样 os.getenv 才能读到你填的智谱 Key)
load_dotenv()

router = APIRouter(tags=["Chat"])

# 提取 API Key，智谱官方文档里 Key 的环境变量名通常叫 ZHIPUAI_API_KEY
client = AsyncOpenAI(
    api_key=os.getenv("ZHIPUAI_API_KEY") or os.getenv("ZHIPU_API_KEY", "EMPTY"),
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest) -> StreamingResponse:
    async def event_generator():
        chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
        created = int(time.time())
        role_sent = False

        try:
            stream = await client.chat.completions.create(
                model=request.model, # 使用请求里传来的模型名称
                messages=[message.model_dump() for message in request.messages],
                temperature=request.temperature,
                stream=True,
            )

            async for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                if choice is None:
                    continue

                delta = {}
                if not role_sent:
                    delta["role"] = "assistant"
                    role_sent = True

                content = getattr(choice.delta, "content", None)
                if content:
                    delta["content"] = content

                payload = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": delta,
                            "finish_reason": choice.finish_reason,
                        }
                    ],
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            final_payload = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }
            yield f"data: {json.dumps(final_payload, ensure_ascii=False)}\n\n"
        except Exception as exc:
            error_payload = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": f"\n\n[服务器拦截报错] {str(exc)}",
                        },
                        "finish_reason": "stop",
                    }
                ],
            }
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )