import http.server
import json
import traceback
import socket
import gzip
import io

LOG_FILE = "gitlab_sentry.log"
PORT = 9001

class SentryHandler(http.server.BaseHTTPRequestHandler):
    def handle_request(self):
        try:
            # Capture request details
            method = self.command
            url = self.path
            headers = dict(self.headers)

            # Capture body (if any)
            content_length = int(headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b""
            body_str = "<empty>"

            # Process payload
            if content_length > 0:
                if headers.get("Content-Encoding") == "gzip":
                    try:
                        # Decompress gzipped payload
                        decompressed = gzip.decompress(body)
                        # Decode as UTF-8 and handle Sentry envelope (JSON lines)
                        decompressed_str = decompressed.decode("utf-8", errors="replace")
                        try:
                            # Parse each line as JSON
                            envelope_lines = decompressed_str.splitlines()
                            parsed_body = [json.loads(line) for line in envelope_lines if line.strip()]
                            body_str = "\n".join(json.dumps(item, indent=2) for item in parsed_body)
                        except json.JSONDecodeError:
                            # Log raw decompressed text if JSON parsing fails
                            body_str = f"[Failed to parse decompressed JSON]\n{decompressed_str}"
                    except gzip.BadGzipFile:
                        # Log hex if decompression fails
                        body_str = f"[Failed to decompress gzip]\n{body.hex()}"
                else:
                    # Non-gzipped payload, decode as UTF-8
                    decoded_str = body.decode("utf-8", errors="replace")
                    try:
                        parsed_body = json.loads(decoded_str)
                        body_str = json.dumps(parsed_body, indent=2)
                    except json.JSONDecodeError:
                        # Log raw decoded text instead of dummy message
                        body_str = f"[Non-JSON body]\n{decoded_str}"

            # Log request details
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write("--- NEW EVENT ---\n")
                f.write(f"METHOD: {method}\n")
                f.write(f"URL: {url}\n")
                f.write("HEADERS:\n")
                for key, value in headers.items():
                    f.write(f"  {key}: {value}\n")
                f.write("BODY:\n")
                f.write(f"{body_str}\n\n")

            # Respond based on method
            if method == "POST" and url in [f"/1", f"/api/1/store/", f"/api/1/envelope/"]:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "ok"}')
            else:
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"OK")

        except Exception as e:
            print(f"Server error: {e}")
            traceback.print_exc()
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Server error")

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def do_PUT(self):
        self.handle_request()

    def do_DELETE(self):
        self.handle_request()

    def do_HEAD(self):
        self.handle_request()

    def do_PATCH(self):
        self.handle_request()

    def do_OPTIONS(self):
        self.handle_request()

    def log_message(self, format, *args):
        # Disable default console logging
        return

if __name__ == "__main__":
    print(f"Listening on http://localhost:{PORT}")
    try:
        server = http.server.HTTPServer(("0.0.0.0", PORT), SentryHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server")
        server.server_close()
