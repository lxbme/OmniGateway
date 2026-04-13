from typing import NotRequired, TypedDict


class AgentState(TypedDict):
    messages: list[dict[str, str]]
    next_step: str
    final_response: NotRequired[str | None]
