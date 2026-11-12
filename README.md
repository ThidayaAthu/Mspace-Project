# Fieldline Fleet Operations Prototype

A lightweight construction fleet dashboard prototype. A Python simulator sends mock vehicle telemetry to a local Python server, which streams updates to the browser in real time. No third-party Python packages are required.

> **Prototype only:** all vehicle readings and site conditions are simulated. Do not use this dashboard for real fleet operations or safety decisions.

## Requirements

- Python 3
- A modern web browser

## Quick start (Windows / PowerShell)

Open the project folder in VS Code. In the first terminal, start the dashboard server:

```powershell
python server.py
```

In a second terminal, start the multi-vehicle simulator:

```powershell
python simulator.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. Keep both terminals open while using the demo. Stop either process with **Ctrl+C**.

The simulator sends readings about once per second. After eight seconds, **Excavator 04** reports engine overheating to demonstrate the critical alert.

## Simulated fleet

| Vehicle | Simulated environment | Scenario |
|---|---|---|
| Excavator 04 | Coastal site — hot and humid | Engine temperature spikes and reports fault `P0217` |
| Loader 02 | North quarry — dusty, rough terrain | Higher-RPM wheel-loader profile |
| Dump Truck 07 | East haul road — dry, loaded haul | Higher-speed haul-truck profile |
| Bulldozer 03 | West site — rain-soaked soft ground | Low-speed dozer profile |

These are illustrative profiles, not physics-based terrain or vehicle models.

## Dashboard features

- Separate Overview, Fleet, Analytics, and Alerts pages, accessible from the dashboard navigation and shareable with URL hash links.
- Live fleet summary for reporting vehicles, active critical alerts, average temperature, and average fuel.
- Fleet page with vehicle table, environment, health, fault code, fuel, and last-seen time.
- Search by vehicle, fault, or environment, and filter by health status.
- Analytics page with per-vehicle temperature history, critical-temperature threshold, and readings grouped by simulated site environment.
- Alerts page with activity filters, acknowledge actions, and recovery status.
- CSV export of locally collected telemetry history.
- Responsive layout for desktop and mobile screens.

The dashboard keeps readings and alert history in browser memory; refreshing the page clears that local history.

## Configuration

The server listens on `127.0.0.1:8000` by default. Configure a different port in PowerShell before starting it:

```powershell
$env:DASHBOARD_PORT = "8080"
python server.py
```

If you change the server port, set the simulator URL to match in its terminal:

```powershell
$env:DASHBOARD_URL = "http://127.0.0.1:8080"
python simulator.py
```

Other simulator settings:

```powershell
$env:SIMULATOR_INTERVAL = "1"  # seconds between readings per vehicle
$env:SPIKE_AFTER_SECONDS = "8" # delay before the excavator overheating scenario
python simulator.py
```

`VEHICLE_NAME` can rename the excavator demo vehicle. The simulator still includes the other three vehicles.

## Optional mSpace SMS

SMS delivery is disabled unless credentials and an endpoint are configured. Obtain the correct API URL, credentials, sender ID, and request format from your SLT-Mobitel/mSpace account documentation or support. The current server implementation sends a JSON `POST` with `username`, `password`, `source`, `destination`, and `message`; adapt it if your account's API expects a different format.

Set the values in the server terminal and restart the server:

```powershell
$env:MSPACE_SMS_URL = "YOUR_OFFICIAL_MSPACE_API_ENDPOINT"
$env:MSPACE_USERNAME = "YOUR_USERNAME"
$env:MSPACE_PASSWORD = "YOUR_PASSWORD"
$env:MSPACE_RECIPIENT = "FLEET_MANAGER_PHONE_NUMBER"
$env:MSPACE_SENDER = "YOUR_APPROVED_SENDER_ID"
python server.py
```

Do not commit real credentials to the repository. When the excavator's temperature crosses the server threshold, the server attempts one SMS for that alert episode. The default threshold is `105` °C and can be changed with `CRITICAL_TEMP_C` before starting the server.

## How it works

1. `simulator.py` generates mock OBD-II-style readings for four independent vehicle profiles.
2. The simulator posts readings to `server.py` at `/api/telemetry`.
3. The server checks the engine-temperature threshold, optionally attempts an SMS, and streams telemetry and alert events over Server-Sent Events at `/events`.
4. `index.html` displays the live fleet view in the browser.

The demo server binds to localhost and is intended for local prototyping, not public deployment.
