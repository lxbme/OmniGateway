import json
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
GATEWAY_URL = "http://127.0.0.1:8080/v1/chat/completions"
ADMIN_URL = "http://127.0.0.1:8081/admin/create"
MODEL_NAME = "mock-upstream-chat"
PROMPT = "Reply Only One Word: OK"


def run_compose(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )


def wait_for_port(host: str, port: int, timeout: float = 120.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except OSError:
            time.sleep(1)
    raise TimeoutError(f"timed out waiting for {host}:{port}")


def wait_for_admin_ready(timeout: float = 180.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            create_token()
            return
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, KeyError):
            time.sleep(2)
    raise TimeoutError("gateway admin endpoint did not become ready in time")


def create_token() -> str:
    secret = os.getenv("ADMIN_SECRET", "test_secret")
    request = Request(
        ADMIN_URL,
        data=json.dumps({"alias": "integration-test"}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Admin-Secret": secret,
        },
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["token"]


def stream_chat_completion(token: str, prompt: str) -> str:
    request = Request(
        GATEWAY_URL,
        data=json.dumps(
            {
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
            }
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    parts: list[str] = []
    saw_done = False
    with urlopen(request, timeout=30) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8").strip()
            if not line or not line.startswith("data: "):
                continue

            payload = line[6:]
            if payload == "[DONE]":
                saw_done = True
                break

            event = json.loads(payload)
            for choice in event.get("choices", []):
                delta = choice.get("delta") or {}
                content = delta.get("content")
                if content:
                    parts.append(content)

    assert saw_done, "response stream did not finish with [DONE]"
    return "".join(parts)


@pytest.fixture(scope="session", autouse=True)
def compose_stack():
    run_compose("up", "-d", "--build")
    wait_for_port("127.0.0.1", 8080)
    wait_for_port("127.0.0.1", 8081)
    wait_for_admin_ready()
    yield
    run_compose("down")


def test_same_prompt_three_times_returns_consistent_answer():
    token = create_token()
    responses = [stream_chat_completion(token, PROMPT) for _ in range(3)]

    assert len(responses) == 3
    assert all(response for response in responses)
    assert responses[0] == responses[1] == responses[2]
    assert "mock response from" in responses[0]
    assert PROMPT in responses[0]
