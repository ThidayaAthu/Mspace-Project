import json
import os
import random
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


SERVER_URL = os.environ.get("DASHBOARD_URL", "http://127.0.0.1:8000")
VEHICLE = os.environ.get("VEHICLE_NAME", "Excavator 04")
INTERVAL_SECONDS = float(os.environ.get("SIMULATOR_INTERVAL", "1"))
SPIKE_AFTER_SECONDS = float(os.environ.get("SPIKE_AFTER_SECONDS", "8"))


def make_telemetry(elapsed):
    overheating = elapsed >= SPIKE_AFTER_SECONDS
    temperature = random.uniform(116, 123) if overheating else random.uniform(82, 94)
    return {
        "vehicle": VEHICLE,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rpm": random.randint(850, 2200),
        "speed_kph": round(random.uniform(0, 18), 1),
        "engine_temp_c": round(temperature, 1),
        "fuel_pct": round(random.uniform(35, 95), 1),
        "fault_code": "P0217" if overheating else "None",
    }


def main():
    print(f"Simulating OBD-II telemetry for {VEHICLE}; posting to {SERVER_URL}")
    print(f"Engine temperature will spike after {SPIKE_AFTER_SECONDS:g} seconds.")
    started = time.monotonic()
    while True:
        telemetry = make_telemetry(time.monotonic() - started)
        request = Request(
            f"{SERVER_URL}/api/telemetry",
            data=json.dumps(telemetry).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=5) as response:
                response.read()
            print(
                f"{telemetry['vehicle']}: RPM {telemetry['rpm']} | "
                f"{telemetry['speed_kph']} km/h | "
                f"{telemetry['engine_temp_c']} C | "
                f"fuel {telemetry['fuel_pct']}% | "
                f"fault {telemetry['fault_code']}"
            )
        except (URLError, TimeoutError) as error:
            print(f"Dashboard unavailable; retrying: {error}")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
