"""
Lightweight mock HTTP service for testing agent API interactions.
Serves structured JSON endpoints.
"""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler


class MockAPIHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: dict):
        response_body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "healthy", "service": "mock-api"})
        elif self.path == "/api/data":
            self._send_json(200, {
                "items": [
                    {"id": 1, "name": "Alpha Item", "value": 100},
                    {"id": 2, "name": "Beta Item", "value": 250}
                ],
                "total": 2
            })
        elif self.path == "/api/status":
            self._send_json(200, {"system": "operational", "version": "1.0.0"})
        else:
            self._send_json(404, {"error": "Not Found", "path": self.path})

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            body = {"raw": body_bytes.decode("utf-8", errors="replace")}

        if self.path == "/api/calculate":
            num1 = body.get("a", 0)
            num2 = body.get("b", 0)
            self._send_json(200, {"result": num1 + num2, "operation": "add"})
        elif self.path == "/api/echo":
            self._send_json(200, {"received": body, "status": "success"})
        else:
            self._send_json(200, {"message": "POST received", "payload": body})

    def log_message(self, format, *args):
        # Silence default logging during test runs
        return


def run_mock_server(port: int = 8080):
    server = HTTPServer(("0.0.0.0", port), MockAPIHandler)
    print(f"Mock API server listening on port {port}...")
    server.serve_forever()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_mock_server(port)
