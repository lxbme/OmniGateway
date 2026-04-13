from app.agent.state import AgentState
from app.core.config import settings
from app.services.llm_service import llm_service


CYBER_HACK_PREFIX = "[Cyber Hack]"


def ensure_cyber_hack_style(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return f"{CYBER_HACK_PREFIX} 信号回来了，但内容被黑洞吃了。"
    if cleaned.startswith(CYBER_HACK_PREFIX):
        return cleaned
    return f"{CYBER_HACK_PREFIX} {cleaned}"


def input_node(state: AgentState) -> AgentState:
    print("收到用户输入")
    return {
        "messages": state.get("messages", []),
        "next_step": "llm_node",
        "final_response": state.get("final_response"),
    }


async def llm_node(state: AgentState) -> AgentState:
    messages = [
        {
            "role": "system",
            "content": settings.default_system_prompt,
        }
    ]
    messages.extend(state.get("messages", []))

    try:
        reply = await llm_service.generate_reply(messages=messages)
        reply = ensure_cyber_hack_style(reply)
    except Exception:
        reply = f"{CYBER_HACK_PREFIX} 核心链路断开，该死的服务器又在装死。"

    updated_messages = [
        *state.get("messages", []),
        {"role": "assistant", "content": reply},
    ]

    return {
        "messages": updated_messages,
        "next_step": "output_node",
        "final_response": state.get("final_response"),
    }


def output_node(state: AgentState) -> AgentState:
    print("工作流执行完毕")
    assistant_messages = [
        message
        for message in state.get("messages", [])
        if message.get("role") == "assistant"
    ]
    final_response = assistant_messages[-1]["content"] if assistant_messages else None

    return {
        "messages": state.get("messages", []),
        "next_step": "end",
        "final_response": final_response,
    }
