import asyncio
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def resolve_live_test_base_url() -> str:
    explicit_base_url = (
        os.getenv("GRAPH_API_BASE_URL")
        or os.getenv("LOCAL_LLM_BASE_URL")
        or os.getenv("LOCAL_GATEWAY_BASE_URL")
    )
    if explicit_base_url:
        return explicit_base_url.rstrip("/")

    if os.path.exists("/.dockerenv"):
        return "http://upstream-service:18080/v1"
    return "http://127.0.0.1:8000/v1"


LIVE_TEST_BASE_URL = resolve_live_test_base_url()
os.environ["PREFER_LOCAL_GATEWAY"] = "1"
os.environ["GRAPH_API_BASE_URL"] = LIVE_TEST_BASE_URL
os.environ.setdefault("DEFAULT_MODEL", "mock-model")

from app.agent.graph import graph_app


async def run_live_test() -> None:
    initial_state = {
        "messages": [
            {"role": "user", "content": "你好，请确认你的赛博黑客人设是否接通。"}
        ],
        "next_step": "input_node",
        "final_response": None,
    }

    print("🚀 [Live Test] 正在激活 LangGraph 状态机...")
    print(f"[Live Test] 当前连接 BASE_URL: {LIVE_TEST_BASE_URL}")
    print("[Live Test] 初始状态:")
    print(json.dumps(initial_state, indent=2, ensure_ascii=False))

    result = await graph_app.ainvoke(initial_state)

    print("[Live Test] 状态机执行完成，最终结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("[Live Test] final_response:")
    print(result.get("final_response"))


if __name__ == "__main__":
    asyncio.run(run_live_test())
