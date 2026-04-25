import traceback

from app.agent.state import AgentState
from app.agent.tools import AVAILABLE_TOOLS, execute_tool, parse_tool_arguments
from app.core.config import settings
from app.services.llm_service import llm_service
from app.services.rag_service import (
    RAG_TOKEN_LIMIT,
    build_context_text as build_context_text_from_rag_service,
    count_tokens,
    get_token_encoding as get_rag_token_encoding,
)


CYBER_HACK_PREFIX = "[Cyber Hack]"
RAG_INSTRUCTION = "请仅根据提供的背景上下文回答问题。如果上下文不足以回答，请直说不知道。"


def ensure_cyber_hack_style(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return f"{CYBER_HACK_PREFIX} 信号回来了，但内容被黑洞吃了。"
    if cleaned.startswith(CYBER_HACK_PREFIX):
        return cleaned
    return f"{CYBER_HACK_PREFIX} {cleaned}"


def get_token_encoding():
    return get_rag_token_encoding()


def build_context_text(documents: list[str], token_limit: int = RAG_TOKEN_LIMIT) -> str:
    base_context_text = build_context_text_from_rag_service(documents, token_limit=token_limit)
    if not base_context_text:
        return ""

    context_body = base_context_text
    current_tokens = count_tokens(context_body)
    context_text = f"# Context Tokens: {current_tokens}\n{context_body}"

    while count_tokens(context_text) > token_limit and context_body:
        print("[RAG] 警告：上下文最终检查仍超限，开始执行暴力字符截断")
        context_body = context_body[:-64].rstrip()
        current_tokens = count_tokens(context_body)
        context_text = f"# Context Tokens: {current_tokens}\n{context_body}"

    final_tokens = count_tokens(context_text)
    if final_tokens > token_limit:
        print(f"[RAG] 严重警告：上下文仍超过 {token_limit} Tokens，请检查模板开销估算")

    return context_text


def input_node(state: AgentState) -> AgentState:
    print("收到用户输入")
    return {
        "messages": state.get("messages", []),
        "documents": state.get("documents", []),
        "context_text": state.get("context_text", ""),
        "next_step": "context_node",
        "model": state.get("model"),
        "temperature": state.get("temperature"),
        "tool_rounds": state.get("tool_rounds", 0),
        "final_response": state.get("final_response"),
    }


def context_node(state: AgentState) -> AgentState:
    context_text = build_context_text(state.get("documents", []))
    return {
        "messages": state.get("messages", []),
        "documents": state.get("documents", []),
        "context_text": context_text,
        "next_step": "llm_node",
        "model": state.get("model"),
        "temperature": state.get("temperature"),
        "tool_rounds": state.get("tool_rounds", 0),
        "final_response": state.get("final_response"),
    }


async def llm_node(state: AgentState) -> AgentState:
    system_prompt = settings.default_system_prompt
    context_text = state.get("context_text", "").strip()
    if context_text:
        system_prompt = f"{system_prompt}\n\n{RAG_INSTRUCTION}\n\n{context_text}"

    messages = [{"role": "system", "content": system_prompt}, *state.get("messages", [])]

    try:
        assistant_message = await llm_service.generate_message(
            messages=messages,
            model=state.get("model"),
            temperature=state.get("temperature", 0.7),
            tools=AVAILABLE_TOOLS,
        )
        if not assistant_message.get("tool_calls"):
            assistant_message["content"] = ensure_cyber_hack_style(
                str(assistant_message.get("content") or "")
            )
        can_call_tool = state.get("tool_rounds", 0) < 1
        next_step = "action_node" if assistant_message.get("tool_calls") and can_call_tool else "output_node"
    except AssertionError:
        traceback.print_exc()
        raise
    except Exception:
        assistant_message = {
            "role": "assistant",
            "content": f"{CYBER_HACK_PREFIX} 核心链路断开，该死的服务器又在装死。",
        }
        next_step = "output_node"

    updated_messages = [
        *state.get("messages", []),
        assistant_message,
    ]

    return {
        "messages": updated_messages,
        "documents": state.get("documents", []),
        "context_text": state.get("context_text", ""),
        "next_step": next_step,
        "model": state.get("model"),
        "temperature": state.get("temperature"),
        "tool_rounds": state.get("tool_rounds", 0),
        "final_response": state.get("final_response"),
    }


def action_node(state: AgentState) -> AgentState:
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else {}
    tool_messages = []

    for tool_call in last_message.get("tool_calls", []) or []:
        function_info = tool_call.get("function", {})
        tool_name = function_info.get("name", "")
        arguments = parse_tool_arguments(function_info.get("arguments"))
        result = execute_tool(tool_name, arguments)
        tool_messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.get("id"),
                "name": tool_name,
                "content": result,
            }
        )

    return {
        "messages": [*messages, *tool_messages],
        "documents": state.get("documents", []),
        "context_text": state.get("context_text", ""),
        "next_step": "llm_node",
        "model": state.get("model"),
        "temperature": state.get("temperature"),
        "tool_rounds": state.get("tool_rounds", 0) + 1,
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
        "documents": state.get("documents", []),
        "context_text": state.get("context_text", ""),
        "next_step": "end",
        "model": state.get("model"),
        "temperature": state.get("temperature"),
        "tool_rounds": state.get("tool_rounds", 0),
        "final_response": final_response,
    }
