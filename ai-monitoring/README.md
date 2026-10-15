# AI Monitoring Playground

Standalone validation environment for the **AI Monitoring Engine**.

## What This Is

The playground wraps the existing `ai_engine` package inside a minimal FastAPI + React
application. The engine code is **never modified** — it is imported as a library.

```
ai_engine/              ← UNTOUCHED production package
ai_monitoring_playground/
  backend/              ← FastAPI + pipeline orchestrator
  frontend/             ← Vite + React dashboard
```

## Prerequisites

| Requirement | Version |
|---|---|
| Python | ≥ 3.10 |
| Node.js | ≥ 18 |
| npm | ≥ 9 |
| AI Engine dependencies | `ai_engine/requirements.txt` must already be installed |

## Quick Start

Open **two terminals** from this directory:

**Terminal 1 — Backend:**
```bat
start_backend.bat
```
Or manually:
```bat
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend:**
```bat
start_frontend.bat
```
Or manually:
```bat
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173** in your browser.

## What You'll See

| Panel | Description |
|---|---|
| **Camera Feed** | Live webcam with bounding box overlay. Border colour = current risk level. |
| **Monitoring Panel** | All detection metrics: face, identity, head pose, gaze, blink, mouth, objects, risk, violations, liveness. |
| **Pipeline Debug** | Collapsible table of every processor: status (READY/RUNNING/FAILED/SKIPPED), execution time, error messages. |
| **Evidence Gallery** | JPEG snapshots saved when new violations are detected. |
| **Event Timeline** | Scrolling log of all detection events with timestamps and frame numbers. |
| **Status Bar** | FPS, inference FPS, latency, CPU%, RAM%, dropped frames, uptime. |

## Ports

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| WebSocket | ws://localhost:8000/ws/monitor |
| Evidence Images | http://localhost:8000/evidence |
| Health | http://localhost:8000/health |
| Frontend | http://localhost:5173 |

## Pipeline Order

```
Frame (JPEG → numpy → Frame)
  → FaceDetector          (BlazeFace)
  → LandmarkDetector      (FaceMesh 468pt)
  → HeadPoseEstimator     (solvePnP)
  → EARProcessor          (Eye Aspect Ratio)
  → GazeExtractor         (iris tracking)
  → BlinkDetector         (temporal EAR)
  → MARProcessor          (Mouth Aspect Ratio)
  → FacePresenceTracker   (temporal state machine)
  → FaceIdentityProcessor (InsightFace embeddings)
  → ObjectDetector        (YOLOv8)
  → ObjectFilter          (confidence/class filter)
  → ObjectTracker         (ByteTrack)
  → IdentityProtection    (MiniFASNet anti-spoof)
  → ObservationFusion     (unified observation)
  → RuleEngine            (17+ rules)
  → RiskEngine            (weighted score 0–100)
  → ViolationManager      (timeline + merging)
  → JSON FrameResult      (broadcast via WebSocket)
```

Each processor is fault-tolerant — if it fails or a dependency fails, it is
`SKIPPED` and the pipeline continues with the remaining stages.

## Evidence

Violation snapshots are saved to `backend/evidence/` as JPEG files whenever a
**new** violation transitions to OPEN status. They are browsable via the
Evidence Gallery panel or directly at:
```
GET http://localhost:8000/evidence/{filename}
```

## Future Migration (Phase 5+)

The `backend/adapters/engine_adapter.py` is the sole integration seam. To
reconnect to the production database:

1. Inject a SQLAlchemy session into `EngineAdapter`.
2. Replace stub method bodies with ORM writes.
3. Wire events → violation table, evidence → blob storage.

No changes to the AI engine or pipeline orchestrator are required.
