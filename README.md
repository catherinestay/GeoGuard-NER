# GeoGuard-NER

**Autonomous IoT-AI Early Warning & Debris Flow Prediction System for North-East India**

Dexathon 2026 · Theme: Disaster Management & Smart Resilience · Category: Hardware / Software Hybrid
Team **VELORA** (Team ID: TEAM-1)

GeoGuard-NER is a network of solar-powered sensor anchors pushed into unstable hill slopes. Each node measures
subsurface soil moisture and slope tilt, sends the readings over long-range LoRa, and feeds an AI model that estimates the
slope's **Factor of Safety (FoS)** and flags debris-flow risk before failure. Satellites and radar fail under monsoon cloud, and cellular
networks drop out in remote highway corridors (NH-27 / NH-44). GeoGuard-NER senses the ground directly and does not depend on either.

![Sensor node](docs/images/sensor-node.png)

## System architecture

![System architecture](docs/images/system-architecture.jpg)

1. **Edge sensing:** ESP32 + MPU6050 (tilt/vibration) + capacitive soil moisture probe + SX1276 LoRa, powered by a 5V 2W solar panel, a TP4056 charge controller and a LiFePO4 pack.
2. **Transmission and local fail-safe:** telemetry goes over LoRa to a gateway. The node triggers a local siren/strobe on its own if the link is lost or a hard tilt threshold is crossed.
3. **Cloud ingestion and AI:** data reaches the backend over MQTT/HTTP and is stored in InfluxDB. A 72-hour LSTM sequence model runs on soil moisture, tilt, vibration and rainfall.
4. **GIS dashboard:** FastAPI serves predictions to a React + Mapbox/Leaflet dashboard showing 🟢 Normal | 🟡 Watch | 🔴 Evacuate.

## Repository layout

| Path | Contents |
|---|---|
| `firmware/geoguard_node/` | ESP32 Arduino firmware: sampling, deep sleep, LoRa uplink, local siren fail-safe |
| `backend/` | FastAPI service: telemetry ingestion, risk scoring, status API |
| `ml/` | Infinite-slope Factor of Safety, PyTorch LSTM model and training script |
| `dashboard/` | React + Leaflet GIS dashboard (to be added) |
| `docs/` | Diagrams and documentation |
| `docker-compose.yml` | Local Mosquitto (MQTT) + InfluxDB stack |

## Hardware bill of materials

| Part | Purpose |
|---|---|
| ESP32 dev board | Microcontroller |
| SX1276 LoRa module (868/915 MHz) | Long-range uplink |
| MPU6050 | Tilt, vibration and seismic tracking (I²C) |
| Capacitive soil moisture sensor | Volumetric water content |
| 5V 2W monocrystalline solar panel | Energy harvesting |
| TP4056 charge controller + LiFePO4 pack | Charging and storage |
| IP67 enclosure, cable gland, iron rebar anchor | Weatherproofing and ground fixing |

### Default wiring (ESP32 DevKit)

| Signal | GPIO |
|---|---|
| LoRa SCK / MISO / MOSI | 18 / 19 / 23 |
| LoRa CS / RST / DIO0 | 5 / 14 / 26 |
| MPU6050 SDA / SCL | 21 / 22 |
| Soil moisture (analog) | 34 |
| Siren / strobe relay | 27 |

Change these in the pin block at the top of `firmware/geoguard_node/geoguard_node.ino` to match your board.

## Quick start

### 1. Firmware
Install the Arduino IDE (or PlatformIO) with the ESP32 board package, then install the libraries **LoRa** (Sandeep Mistry) and **MPU6050** (Electronic Cats or Adafruit).
Open `firmware/geoguard_node/geoguard_node.ino`, set `NODE_ID` and `LORA_FREQ`, and flash.

### 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs, then send a sample reading:
```bash
curl -X POST http://127.0.0.1:8000/telemetry -H "Content-Type: application/json" \
  -d '{"node_id":"N01","soil_moisture":0.42,"tilt_deg":3.1,"vibration":0.02,"rainfall_mm_h":18}'
curl http://127.0.0.1:8000/status
```

### 3. ML
```bash
cd ml
pip install -r requirements.txt
python fos.py          # prints a worked Factor of Safety example
python train.py        # trains the LSTM on synthetic data (swap in field data later)
```

### 4. Local MQTT + InfluxDB
```bash
docker compose up -d
```

## Risk levels

| Level | Meaning | Action |
|---|---|---|
| 🟢 Normal | FoS comfortably above 1.5 | Routine monitoring |
| 🟡 Watch | FoS between 1.2 and 1.5, or rising saturation | Increase sampling, notify the DDMA |
| 🔴 Evacuate | FoS below 1.2, or predicted failure within about 45 min | Trigger sirens and road-gate barriers, alert the DDMA |

These thresholds are placeholders. They must be calibrated against real geotechnical data before any deployment.

## Status and roadmap

- [x] Benchtop node prototype (tilt sensing and packet delivery tested)
- [x] Backend, FoS and LSTM scaffolding
- [ ] LoRa gateway firmware (LoRa to MQTT bridge)
- [ ] React + Leaflet dashboard
- [ ] Kalman-filter sensor fusion on the node
- [ ] Field pilot on a hill slope; model retraining on real data

> The ML model currently trains on synthetic data and has not been validated for real-world warnings.

## Team VELORA

Add team member names and roles here.

## License

MIT, see [LICENSE](LICENSE).
