"""GeoGuard-NER backend: ingest node telemetry, score risk, expose status for the dashboard."""
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

sys.path.append(str(Path(__file__).resolve().parents[2] / "ml"))
from fos import SoilParams, factor_of_safety, risk_level  # noqa: E402

app = FastAPI(title="GeoGuard-NER API", version="0.1.0")
history = defaultdict(lambda: deque(maxlen=72))   # last 72 readings per node (in memory; swap for InfluxDB)


class Telemetry(BaseModel):
    node_id: str
    soil_moisture: float = Field(ge=0, le=1)
    tilt_deg: float
    vibration: float = 0.0
    rainfall_mm_h: float = 0.0
    slope_deg: float = 30.0          # site slope angle, set per node at installation
    local_alarm: bool = False


@app.post("/telemetry")
def ingest(t: Telemetry):
    fos = factor_of_safety(t.slope_deg, t.soil_moisture, SoilParams())
    level = "EVACUATE" if t.local_alarm else risk_level(fos)
    history[t.node_id].append({
        "time": datetime.now(timezone.utc).isoformat(),
        **t.model_dump(), "fos": round(fos, 3), "risk": level,
    })
    return {"node_id": t.node_id, "fos": round(fos, 3), "risk": level}


@app.get("/status")
def status():
    return {nid: h[-1] for nid, h in history.items() if h}


@app.get("/nodes/{node_id}/history")
def node_history(node_id: str):
    return list(history[node_id])
