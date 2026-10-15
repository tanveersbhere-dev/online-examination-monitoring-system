# ExamShield — Online Examination Monitoring System Using Computer Vision

**ExamShield** is an enterprise-grade automated online examination management and real-time computer-vision proctoring platform. The repository brings together both key modules:
1. **Examination Management System:** Comprehensive administrative, examiner, and student portal for paper authoring, exam scheduling, role-based authentication, candidate assignment, live MCQ attempting, and auto-evaluation reporting.
2. **AI Monitoring Unit:** Real-time proctoring and computer-vision pipeline that monitors candidate attention, detects face presence/absence, tracks gaze orientation, detects unauthorized physical objects (smartphones, earphones, unauthorized materials), applies temporal confirmation logic, captures multi-angle evidence replays, and computes automated integrity indices.

---

## 📁 Repository Directory Structure

```text
online-examination-monitoring-system/
├── frontend/                     # Examination Management Web App (React + Vite + MUI)
│   ├── src/                      # Examiner workspace, student exam portal, evaluation views
│   ├── package.json
│   └── vite.config.ts
├── backend/                      # Examination Core API Service (FastAPI + SQLAlchemy Async)
│   ├── app/                      # Auth, exams, question papers, evaluations, AI event ingestion
│   │   ├── api/v1/routes/        # REST and WebSocket endpoints
│   │   ├── monitoring_integration/# Bridges examination sessions with AI monitoring events
│   │   ├── models/               # SQLAlchemy ORM models
│   │   └── services/             # Token service, exam lifecycle, email notifications
│   ├── alembic/                  # Database migration scripts
│   ├── requirements.txt
│   └── start_backend.bat
├── ai-monitoring/                # AI Computer-Vision Monitoring Host & Engine
│   ├── ai_engine/                # 19-stage real-time video processing pipeline
│   │   ├── detectors/            # Face detection, landmark extraction, head pose
│   │   ├── environment/          # Fused object detection, phone/book/device validation
│   │   ├── gaze/                 # 3D gaze estimation, camera-centered attention tracking
│   │   ├── intelligence/         # Temporal rule engine, observation fusion, behavioral scoring
│   │   └── requirements.txt
│   ├── backend/                  # AI Host Server (FastAPI + WebSocket video ingestion)
│   ├── frontend/                 # AI Host UI (Live candidate monitoring & mobile camera feed)
│   ├── incident_intelligence/    # Violation episode manager, debouncing, session integrity
│   ├── scripts/                  # Production verification & benchmarking
│   ├── tests/                    # Unit and regression test suite
│   ├── start_all.bat             # One-click launcher for AI Monitoring Subsystem
│   ├── start_backend.bat
│   └── start_frontend.bat
├── .env.example                  # Environment configuration template
├── .gitignore                    # Git rules (excludes venvs, node_modules, weights, media)
├── start_project.bat             # Unified full-stack launcher
├── start_backend.bat             # Dedicated backend launcher
└── start_frontend.bat            # Dedicated frontend launcher
```

---

## 🚀 Key Features

### 1. Examination Management
- **Role-Based Access Control:** Secure portals for Administrators, Examiners, Supervisors, and Students.
- **Dynamic Question Paper Builder:** Supports MCQ, Subjective, and Mixed question types, section-level timing controls, and customizable weight distributions.
- **Candidate Runtime:** Timed question interface with real-time countdown, question palette navigation, and secure submission confirmation.
- **Evaluation Reporting:** Automatic MCQ scoring, question-by-question breakdown, candidate summary, and score finalization.
- **Automated Communication:** Secure SMTP integration for scheduling notices, exam invitations, and result publishing.

### 2. AI-Powered Monitoring Subsystem
- **Facial Verification & Landmark Tracking:** Powered by Google MediaPipe and OpenCV for continuous student presence verification.
- **Gaze & Attention Estimation:** Evaluates screen-focused attention vs. prolonged off-screen looking to prevent unauthorized glances.
- **Unauthorized Object Detection:** Real-time YOLO-based detection of smartphones, secondary laptops, books, and earphones.
- **Temporal Confirmation:** Distinguishes momentary glances from genuine violations by enforcing persistence threshold windows, preventing false alarms.
- **Forensic Evidence Capture:** Generates synchronized 3-second replay clips and verified high-resolution snapshots for human invigilator review.
- **Multi-Camera Support:** Supports both primary laptop webcams and secondary mobile camera perspectives over local network WebSockets.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, Vite, Material UI (MUI), TypeScript, Axios, Emotion |
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy (Async), Alembic, Pydantic v2, PostgreSQL |
| **AI Engine** | OpenCV, MediaPipe, Ultralytics YOLOv8/YOLOE, ONNX Runtime, NumPy |
| **Protocols** | REST API, WebSockets (Full-Duplex frame streaming), SMTP |

---

## ⚙️ Quick Start Guide

### Prerequisites
- Python 3.10 or 3.12+
- Node.js 18+ and npm
- PostgreSQL database

### 1. Setup Environment Configuration
Copy `.env.example` to `.env` and fill in your database credentials:
```bash
cp .env.example .env
```

### 2. Run Examination Management System
```bash
# Double-click start_project.bat, or launch manually:
# Terminal 1: Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```
- Examination Frontend: `http://localhost:5173`
- Backend API Docs: `http://127.0.0.1:8000/docs`

### 3. Run AI Monitoring Subsystem
```bash
cd ai-monitoring
# Launch using the dedicated script:
start_all.bat
# Or manually:
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
```
- AI Monitoring Host UI: `https://localhost:5173`
- AI WebSocket Stream: `ws://localhost:8001/ws/monitor`

---

## 🧠 AI Model Weights & Setup
To maintain repository agility and comply with standard Git file thresholds, large neural network binary weights (`*.pt`, `*.onnx`, `*.ts`) are excluded from tracking.
- Pre-trained base weights (`yolov8n.pt`, `silero_vad.onnx`) and custom fine-tuned object weights should be placed under `ai-monitoring/models/` or configured via model path environment variables.
- MediaPipe models are downloaded or cached automatically on initial pipeline bootstrap.

---

## 🧪 Testing

```bash
# Run Backend Integration Tests:
cd backend
pytest app/tests/test_monitoring_integration.py

# Run AI Monitoring Behavior & Intelligence Tests:
cd ai-monitoring
pytest tests/test_behavior_engine.py tests/test_incident_domain_core.py
```

---

## 📄 License
This project is developed as part of the Final Year Project (FYP) at Quaid-i-Azam University, Islamabad. All rights reserved.
