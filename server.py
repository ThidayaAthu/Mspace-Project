import json
import os
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


HOST = "127.0.0.1"
PORT = int(os.environ.get("DASHBOARD_PORT", "8000"))
CRITICAL_TEMP_C = float(os.environ.get("CRITICAL_TEMP_C", "105"))
SUBSCRIBERS = set()
SUBSCRIBERS_LOCK = threading.Lock()
ALERTED_VEHICLES = set()
ALERTED_LOCK = threading.Lock()


def publish(event):
    with SUBSCRIBERS_LOCK:
        subscribers = tuple(SUBSCRIBERS)
    for subscriber in subscribers:
        try:
            subscriber.put_nowait(event)
        except queue.Full:
            pass


def send_mspace_sms(vehicle, temperature):
    endpoint = os.environ.get("MSPACE_SMS_URL", "").strip()
    username = os.environ.get("MSPACE_USERNAME", "").strip()
    password = os.environ.get("MSPACE_PASSWORD", "").strip()
    recipient = os.environ.get("MSPACE_RECIPIENT", "").strip()
    sender = os.environ.get("MSPACE_SENDER", "").strip()

    if not all((endpoint, username, password, recipient)):
        print(
            "SMS not sent: configure MSPACE_SMS_URL, MSPACE_USERNAME, "
            "MSPACE_PASSWORD, and MSPACE_RECIPIENT using your mSpace account details."
        )
        return

    message = f"CRITICAL: {vehicle} Engine Overheating ({temperature:.1f} C)"
    payload = json.dumps({
        "username": username,
        "password": password,
        "source": sender,
        "destination": recipient,
        "message": message,
    }).encode("utf-8")
    request = Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            print(f"mSpace SMS HTTP {response.status} for {vehicle}.")
    except (URLError, TimeoutError) as error:
        print(f"mSpace SMS request failed: {error}")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            try:
                with open("index.html", "rb") as page:
                    content = page.read()
            except OSError as error:
                self.send_error(500, f"Could not read index.html: {error}")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            subscriber = queue.Queue(maxsize=100)
            with SUBSCRIBERS_LOCK:
                SUBSCRIBERS.add(subscriber)
            try:
                self.wfile.write(b": connected\n\n")
                self.wfile.flush()
                while True:
                    try:
                        event = subscriber.get(timeout=15)
                        data = json.dumps(event, separators=(",", ":")).encode("utf-8")
                        self.wfile.write(b"data: " + data + b"\n\n")
                    except queue.Empty:
                        self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                with SUBSCRIBERS_LOCK:
                    SUBSCRIBERS.discard(subscriber)
            return

        self.send_error(404, "Not found")

    def do_POST(self):
        if urlparse(self.path).path != "/api/telemetry":
            self.send_error(404, "Not found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16_384:
                raise ValueError("Content-Length must be between 1 and 16384")
            telemetry = json.loads(self.rfile.read(length))
            required = ("vehicle", "rpm", "speed_kph", "engine_temp_c", "fuel_pct", "fault_code")
            if not isinstance(telemetry, dict) or any(key not in telemetry for key in required):
                raise ValueError("Telemetry is missing required fields")
            if not isinstance(telemetry["vehicle"], str) or not telemetry["vehicle"]:
                raise ValueError("vehicle must be a non-empty string")
            for key in ("rpm", "speed_kph", "engine_temp_c", "fuel_pct"):
                if not isinstance(telemetry[key], (int, float)):
                    raise ValueError(f"{key} must be numeric")
        except (ValueError, json.JSONDecodeError) as error:
            self.send_error(400, str(error))
            return

        vehicle = telemetry["vehicle"]
        temperature = float(telemetry["engine_temp_c"])
        telemetry["critical"] = temperature >= CRITICAL_TEMP_C
        publish({"type": "telemetry", "data": telemetry})

        if telemetry["critical"]:
            with ALERTED_LOCK:
                first_alert = vehicle not in ALERTED_VEHICLES
                ALERTED_VEHICLES.add(vehicle)
            if first_alert:
                publish({
                    "type": "alert",
                    "vehicle": vehicle,
                    "message": f"CRITICAL: {vehicle} Engine Overheating",
                    "temperature": temperature,
                })
                send_mspace_sms(vehicle, temperature)
        else:
            with ALERTED_LOCK:
                ALERTED_VEHICLES.discard(vehicle)

        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string, *args):
        if self.path != "/events":
            super().log_message(format_string, *args)


if __name__ == "__main__":
    print(f"Dashboard: http://{HOST}:{PORT}")
    print(f"Critical engine temperature: {CRITICAL_TEMP_C:g} C")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
