from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from app.api.routes import router as chat_router # 引入刚才写好的 router

app = FastAPI(
    title="MCP Agent Core API",
    description="高可用大模型网关的 Python 核心大脑，兼容 OpenAI SSE 协议。",
    version="1.0.0"
)

# 注册核心的聊天路由
app.include_router(chat_router)

@app.get("/health", tags=["System"])
async def health_check():
    return JSONResponse(content={"status": "ok", "service": "mcp-agent-core"})

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)