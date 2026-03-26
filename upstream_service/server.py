import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def chunk_text(text: str, size: int = 18) -> list[str]:
    if not text:
        return [""]
    return [text[index : index + size] for index in range(0, len(text), size)]


def extract_prompt(payload: dict) -> str:
    messages = payload.get("messages") or []
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")
    return ""


class MockUpstreamHandler(BaseHTTPRequestHandler):
    server_version = "MockUpstream/0.1"
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        if self.path != "/health":
            self.send_error(404, "not found")
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404, "not found")
            return

        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.send_error(400, "invalid json")
            return

        prompt = extract_prompt(payload)
        model = payload.get("model") or os.getenv("MOCK_COMPLETION_MODEL", "mock-upstream-chat")
        response_text = f"mock response from {model}: {prompt or 'empty prompt'}"

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        for part in chunk_text(response_text):
            event = {"choices": [{"delta": {"content": part}, "finish_reason": ""}]}
            self.wfile.write(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8"))
            self.wfile.flush()
            time.sleep(0.05)

        usage = {"usage": {"total_tokens": max(1, len(response_text.split()))}}
        self.wfile.write(f"data: {json.dumps(usage, ensure_ascii=False)}\n\n".encode("utf-8"))
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        self.close_connection = True

    def log_message(self, format: str, *args):
        print(
            "[HTTP]",
            self.address_string(),
            "-",
            format % args,
            flush=True,
        )


def main() -> None:
    port = int(os.getenv("PORT", "18080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), MockUpstreamHandler)
    print(f"[Info] Upstream mock listening on port {port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
