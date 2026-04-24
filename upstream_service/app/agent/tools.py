import json
from collections.abc import Callable
from typing import Any


WEATHER_TOOL_NAME = "mock_weather_tool"


def mock_weather_tool(city: str) -> str:
    weather_map = {
        "北京": "北京今天天气晴，气温 22C，东北风 2 级。",
        "上海": "上海今天天气多云，气温 25C，东南风 3 级。",
        "广州": "广州今天天气小雨，气温 28C，南风 2 级。",
    }
    return weather_map.get(city, f"{city}今天天气未知，当前为本地工具模拟结果。")


WEATHER_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": WEATHER_TOOL_NAME,
        "description": "查询指定城市的模拟天气信息。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "需要查询天气的城市名称，例如北京、上海、广州。",
                }
            },
            "required": ["city"],
            "additionalProperties": False,
        },
    },
}


AVAILABLE_TOOLS = [WEATHER_TOOL_SCHEMA]
TOOL_REGISTRY: dict[str, Callable[..., str]] = {
    WEATHER_TOOL_NAME: mock_weather_tool,
}


def parse_tool_arguments(raw_arguments: str | dict[str, Any] | None) -> dict[str, Any]:
    if raw_arguments is None:
        return {}
    if isinstance(raw_arguments, dict):
        return raw_arguments
    try:
        parsed = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    tool = TOOL_REGISTRY.get(name)
    if tool is None:
        return f"未知工具: {name}"
    return tool(**arguments)
