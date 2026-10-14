# Dependency Cleanup Candidates

**Project**: FYP Examination System (`ExamShield`)  
**Audit Date**: October 2026  
**Status**: Informational / Advisory Only (No modifications made to `requirements.txt` or `package.json` in this phase)

---

## 1. Executive Summary

During the forensic audit and cleanup phase, dependency manifests (`backend/requirements.txt` and `frontend/package.json`) and the active Python virtual environment (`backend/venv`) were inspected to distinguish core Examination System dependencies from remnants of experimental AI pipelines.

Key findings:
- **`backend/requirements.txt`** is already streamlined. It contains only 19 core web and storage packages plus `opencv-python` and `numpy`.
- **`backend/venv` (Active Environment)** contains heavy machine learning and streaming packages (`torch`, `ultralytics`, `mediapipe`, `sounddevice`, `selenium`) that were installed during past in-tree AI experiments (Phases 2 & 3 POCs).
- **`frontend/package.json`** is clean, containing only standard React 18, React Router DOM 6, Axios, Emotion, and Material UI packages. No AI/experimental packages are present.

---

## 2. Backend Environment Candidates (`backend/venv`)

The following packages are currently installed in `backend/venv` but are **NOT** specified in `backend/requirements.txt`. They were installed during prior local AI experiments (computer vision, head pose/gaze estimation, audio classification) and are candidates for pruning from the examination system virtual environment once the independent AI engine operates as a separate service:

| Installed Package | Installed Version | Original Role in Old AI Experiments | Status / Future Action |
|:---|:---|:---|:---|
| `torch` | `2.13.0` | PyTorch deep learning framework for local YOLO / ViT inference | **Removable in future venv prune**. Independent engine will host ML inference. |
| `torchvision` | `0.28.0` | Vision utilities for PyTorch | **Removable in future venv prune**. |
| `ultralytics` | `8.4.106` | YOLOv8 object & wearable audio device detector | **Removable in future venv prune**. |
| `ultralytics-thop` | `2.1.0` | FLOPs profiler for Ultralytics YOLO models | **Removable in future venv prune**. |
| `mediapipe` | `0.10.35` | Google MediaPipe for face landmarks / gaze tracking | **Removable in future venv prune**. |
| `sounddevice` | `0.5.5` | Audio capture library for microphone streaming | **Removable in future venv prune**. Phase 3 Audio Detector will capture independently. |
| `selenium` | `4.46.0` | Browser automation (used in old proctoring POC scripts) | **Removable in future venv prune**. |
| `opencv-contrib-python` | `5.0.0.93` | Extra OpenCV modules | Redundant with `opencv-python`. |
| `polars` | `1.43.0` | Fast DataFrame library used in incident benchmarking | **Removable in future venv prune**. |
| `imageio-ffmpeg` | `0.6.0` | Video rendering utility for replay generation | Optional depending on video processing needs. |

---

## 3. Backend Manifest Candidates (`backend/requirements.txt`)

Review of the packages listed in `requirements.txt`:

| Package | Status | Retention Rationale |
|:---|:---|:---|
| `fastapi>=0.100.0` | **Retain (Core)** | Examination System Web API framework |
| `uvicorn[standard]>=0.23.0` | **Retain (Core)** | ASGI Server |
| `sqlalchemy[asyncio]>=2.0.0` | **Retain (Core)** | Async ORM & Database layer |
| `asyncpg>=0.28.0` | **Retain (Core)** | PostgreSQL async driver |
| `alembic>=1.11.0` | **Retain (Core)** | Schema migrations |
| `pydantic>=2.0.0` | **Retain (Core)** | Data validation |
| `pydantic-settings>=2.0.0` | **Retain (Core)** | Configuration management |
| `python-dotenv>=1.0.0` | **Retain (Core)** | Environment variable loading |
| `httpx>=0.24.0` | **Retain (Core)** | Async HTTP client for API tests & external calls |
| `pytest>=7.0.0` | **Retain (Core)** | Test runner |
| `pytest-asyncio>=0.21.0` | **Retain (Core)** | Async test runner |
| `passlib[bcrypt]>=1.7.4` | **Retain (Core)** | Password hashing |
| `PyJWT>=2.8.0` | **Retain (Core)** | Authentication JWT tokens |
| `python-multipart>=0.0.6` | **Retain (Core)** | Multipart form data (student face photo uploads) |
| `email-validator>=2.0.0` | **Retain (Core)** | Email validation in schemas |
| `aiosmtplib>=2.0.0` | **Retain (Core)** | Async email notifications for invitations/alerts |
| `opencv-python>=4.8.0` | **Retain (Core / Utility)** | Used by `student_service.py` (face image decoding/saving) and `exam_environment.py` (blank snapshot generation) |
| `numpy>=1.24.0` | **Retain (Core / Utility)** | Used by image buffer decoding in student face photo service |
| `bcrypt==4.0.1` | **Retain (Core)** | Password encryption backend |

> **Conclusion for `requirements.txt`**: None of the 19 packages should be removed now. Both `opencv-python` and `numpy` are actively required by student registration face capture processing.

---

## 4. Frontend Candidates (`frontend/package.json`)

All dependencies in `frontend/package.json` are essential core packages:

| Dependency | Purpose | Status |
|:---|:---|:---|
| `@emotion/react`, `@emotion/styled` | Styling engine for Material UI | **Retained** |
| `@fontsource/inter` | Application font | **Retained** |
| `@mui/material`, `@mui/icons-material` | Core component library & icons | **Retained** |
| `axios` | HTTP client for Examination System API calls | **Retained** |
| `react`, `react-dom` | React 18 core framework | **Retained** |
| `react-router-dom` | Application routing | **Retained** |

> **Conclusion for `package.json`**: Zero obsolete dependencies found.

---

## 5. Next Steps for Dependency Management
1. When the independent AI Monitoring Engine is integrated, it should run in its own virtual environment or container with `torch`, `ultralytics`, and `mediapipe`.
2. A separate `requirements-clean.txt` or a virtualenv rebuild can be performed when packaging the Examination System for production deployment.
