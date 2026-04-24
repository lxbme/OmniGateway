import asyncio
import json
import sys
from pathlib import Path
from typing import Any


SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]

if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.agent.graph import graph_app


EXPECTED_EFFECTIVE_ORDER = [
    "input_node",
    "llm_node",
    "action_node",
    "llm_node",
    "output_node",
]


def summarize_node_state(node_name: str, state_update: dict[str, Any]) -> None:
    messages = state_update.get("messages", [])
    last_message = messages[-1] if messages else {}
    final_response = state_update.get("final_response")

    print(f"[Tool Test] 节点完成: {node_name}")
    print(f"[Tool Test] next_step: {state_update.get('next_step')}")

    if last_message:
        print(f"[Tool Test] 最新消息 role: {last_message.get('role')}")
        if last_message.get("tool_calls"):
            print("[Tool Test] 检测到 tool_calls:")
            print(json.dumps(last_message["tool_calls"], indent=2, ensure_ascii=False))
        if last_message.get("role") == "tool":
            print(f"[Tool Test] 工具返回: {last_message.get('content')}")

    if final_response:
        print(f"[Tool Test] final_response: {final_response}")


async def run_test() -> None:
    initial_state = {
        "messages": [
            {"role": "user", "content": "帮我查一下上海今天的天气。"}
        ],
        "documents": [],
        "context_text": "",
        "next_step": "input_node",
        "model": "agent-core-v1",
        "temperature": 0.2,
        "tool_rounds": 0,
        "final_response": None,
    }

    print("[Tool Test] 开始执行 LangGraph 工具调用实弹测试")
    print("[Tool Test] 初始 State:")
    print(json.dumps(initial_state, indent=2, ensure_ascii=False))

    visited_nodes: list[str] = []
    final_state: dict[str, Any] = {}

    async for update in graph_app.astream(initial_state, stream_mode="updates"):
        for node_name, state_update in update.items():
            visited_nodes.append(node_name)
            final_state.update(state_update)
            summarize_node_state(node_name, state_update)

    effective_order = [node for node in visited_nodes if node != "context_node"]
    final_response = final_state.get("final_response") or ""

    print("[Tool Test] 实际节点流转顺序:")
    print(" -> ".join(visited_nodes))
    print("[Tool Test] 去除空 RAG 上下文节点后的有效顺序:")
    print(" -> ".join(effective_order))
    print("[Tool Test] 最终回复:")
    print(final_response)

    assert effective_order == EXPECTED_EFFECTIVE_ORDER, (
        "工具调用路由顺序不符合预期: "
        f"expected={EXPECTED_EFFECTIVE_ORDER}, actual={effective_order}"
    )
    assert "[Cyber Hack]" in final_response, "最终回复缺少 [Cyber Hack] 人设前缀"
    assert any(keyword in final_response for keyword in ["上海", "天气", "多云", "25C", "东南风"]), (
        "最终回复没有结合 mock_weather_tool 的天气数据"
    )


if __name__ == "__main__":
    asyncio.run(run_test())
