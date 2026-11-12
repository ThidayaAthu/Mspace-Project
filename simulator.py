import json
import os
import random
import threading
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


SERVER_URL = os.environ.get("DASHBOARD_URL", "http://127.0.0.1:8000")
INTERVAL_SECONDS = float(os.environ.get("SIMULATOR_INTERVAL", "1"))
SPIKE_AFTER_SECONDS = float(os.environ.get("SPIKE_AFTER_SECONDS", "8"))
VEHICLES = [
    {
        "vehicle": "Excavator 04",
        "vehicle_type": "Excavator",
        "environment": "Coastal site · Hot and humid",
        "rpm": (850, 2200),
        "speed_kph": (0, 18),
        "engine_temp_c": (84, 96),
        "fuel_pct": (35, 95),
        "spike": True,
    },
    {
        "vehicle": "Loader 02",
        "vehicle_type": "Wheel loader",
        "environment": "North quarry · Dusty, rough terrain",
        "rpm": (1200, 2400),
        "speed_kph": (0, 14),
        "engine_temp_c": (87, 101),
        "fuel_pct": (22, 82),
        "spike": False,
    },
    {
        "vehicle": "Dump Truck 07",
        "vehicle_type": "Dump truck",
        "environment": "East haul road · Dry, loaded haul",
        "rpm": (1000, 2100),
        "speed_kph": (12, 42),
        "engine_temp_c": (80, 97),
        "fuel_pct": (28, 90),
        "spike": False,
    },
    {
        "vehicle": "Bulldozer 03",
        "vehicle_type": "Bulldozer",
        "environment": "West site · Rain-soaked soft ground",
        "rpm": (1100, 2050),
        "speed_kph": (0, 9),
        "engine_temp_c": (79, 94),
        "fuel_pct": (30, 86),
        "spike": False,
    },
]

if os.environ.get("VEHICLE_NAME"):
    VEHICLES[0] = {**VEHICLES[0], "vehicle": os.environ["VEHICLE_NAME"]}


def make_telemetry(profile, elapsed, rng=random):
    overheating = profile["spike"] and elapsed >= SPIKE_AFTER_SECONDS
    temperature_range = (116, 123) if overheating else profile["engine_temp_c"]
    return {
        "vehicle": profile["vehicle"],
        "vehicle_type": profile["vehicle_type"],
        "environment": profile["environment"],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rpm": rng.randint(*profile["rpm"]),
        "speed_kph": round(rng.uniform(*profile["speed_kph"]), 1),
        "engine_temp_c": round(rng.uniform(*temperature_range), 1),
        "fuel_pct": round(rng.uniform(*profile["fuel_pct"]), 1),
        "fault_code": "P0217" if overheating else "None",
    }


def run_vehicle(profile):
    vehicle = profile["vehicle"]
    print(
        f"Simulating {vehicle} ({profile['vehicle_type']}) in "
        f"{profile['environment']}; posting to {SERVER_URL}"
    )
    if profile["spike"]:
        print(f"{vehicle} engine temperature will spike after {SPIKE_AFTER_SECONDS:g} seconds.")
    started = time.monotonic()
    while True:
        telemetry = make_telemetry(profile, time.monotonic() - started)
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
                f"{vehicle} [{profile['environment']}]: "
                f"RPM {telemetry['rpm']} | {telemetry['speed_kph']} km/h | "
                f"{telemetry['engine_temp_c']} C | fuel {telemetry['fuel_pct']}% | "
                f"fault {telemetry['fault_code']}"
            )
        except (URLError, TimeoutError) as error:
            print(f"{vehicle}: dashboard unavailable; retrying: {error}")
        time.sleep(INTERVAL_SECONDS)


def main():
    print(f"Starting {len(VEHICLES)} independent vehicle simulations.")
    threads = [
        threading.Thread(target=run_vehicle, args=(profile,), name=profile["vehicle"])
        for profile in VEHICLES
    ]
    for thread in threads:
        thread.start()
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("\nStopping vehicle simulations.")


if __name__ == "__main__":
    main()
