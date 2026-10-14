# Examination System Cleanup Report

**Project**: Final Year Project (FYP) — Online Examination System (`ExamShield`)  
**Audit & Cleanup Execution Date**: October 2026  
**Safety Checkpoint Tag**: `cleanup-before-pruning`  
**Safety Checkpoint Commit**: `e49977e`  
**Working Branch**: `main`  
**Status**: CLEANUP COMPLETE — ZERO REGRESSIONS

---

## 1. Executive Summary

This controlled cleanup phase successfully pruned obsolete, duplicate, experimental, and unmounted files from the historical in-tree AI monitoring implementation while strictly preserving:
1. The **entire working Examination System** (student exam lifecycle, examiner exam creation and monitoring, authentication, and reporting).
2. The **PostgreSQL database schema and data** (all 24 tables, all 99 evidence records, all 15 exam sessions, all migrations intact).
3. The **AI Integration Foundation** (`AIEventProcessor`, event ingestion endpoints, contracts, normalizers, WebSocket broadcaster, adapter interfaces, and student monitoring preview component).
4. All **48 evidence replay clips** actively referenced by the PostgreSQL database.

All automated verification checks passed with 100% parity before and after cleanup:
- **Backend Test Suite**: 73 passed / 73 total in ~37.6s.
- **Frontend Production Build**: `tsc -b && vite build` built cleanly in under 5.0s with zero errors.

---

## 2. Git Checkpoint Verification

Prior to any filesystem deletions or modifications, safety checkpoints were created:

- **Checkpoint Commit Hash**: `e49977e80556f0e3860bb77579ff844ee461f868`
- **Checkpoint Commit Message**: `checkpoint: state before controlled cleanup (cleanup-before-pruning)`
- **Safety Branch**: `cleanup-before-pruning`
- **Safety Git Tag**: `cleanup-before-pruning`

No destructive git operations (`reset --hard`, `checkout`, `rebase`, `stash drop`) were executed. The full historical tree is preserved and recoverable at any time via `git checkout cleanup-before-pruning`.

---

## 3. Inventory of Deleted Files & Directories

A total of **69 obsolete files** and **17 directories** were safely pruned across four main categories:

### A. Obsolete Backend Playground (`backend/app/api/v1/routes/playground/`)
*Rationale*: These endpoints were unmounted, experimental prototypes used during early monitoring experiments. They bypassed the production `AIEventProcessor` and were never registered in `backend/app/main.py`.
- `backend/app/api/v1/routes/playground/__init__.py`
- `backend/app/api/v1/routes/playground/calibration_api.py`
- `backend/app/api/v1/routes/playground/evidence_api.py`
- `backend/app/api/v1/routes/playground/health_api.py`
- `backend/app/api/v1/routes/playground/incidents_api.py`
- `backend/app/api/v1/routes/playground/ws_handler.py`
*(Directory `backend/app/api/v1/routes/playground/` completely removed)*

### B. Orphaned Frontend Monitoring JSX Components (`frontend/src/components/monitoring/`)
*Rationale*: Legacy JSX prototypes not imported by any TypeScript page or component. The production application utilizes TypeScript (`.tsx`) views in `frontend/src/pages/monitoring/` and `StudentLiveMonitoringPreview.tsx`.
- `frontend/src/components/monitoring/BehaviorPanel/BehaviorPanel.jsx` & `.css`
- `frontend/src/components/monitoring/BehaviorTimeline/BehaviorTimeline.jsx` & `.css`
- `frontend/src/components/monitoring/CalibrationDebugOverlay/CalibrationDebugOverlay.jsx` & `.css`
- `frontend/src/components/monitoring/CalibrationModal/CalibrationModal.jsx` & `.css`
- `frontend/src/components/monitoring/CameraPanel/CameraPanel.jsx` & `.css`
- `frontend/src/components/monitoring/EventTimeline/EventTimeline.jsx` & `.css`
- `frontend/src/components/monitoring/EvidenceGallery/EvidenceGallery.jsx` & `.css`
- `frontend/src/components/monitoring/ExportCaseDialog/ExportCaseDialog.jsx` & `.css`
- `frontend/src/components/monitoring/IncidentDashboard/IncidentDashboard.jsx` & `.css`
- `frontend/src/components/monitoring/MonitoringPanel/MonitoringPanel.jsx` & `.css`
- `frontend/src/components/monitoring/PipelineDebug/PipelineDebug.jsx` & `.css`
- `frontend/src/components/monitoring/ProctorReviewModal/ProctorReviewModal.jsx` & `.css`
- `frontend/src/components/monitoring/ReplayViewerModal/ReplayViewerModal.jsx` & `.css`
- `frontend/src/components/monitoring/StatusBar/StatusBar.jsx` & `.css`
*(14 subdirectories removed; `StudentLiveMonitoringPreview.tsx` retained in `frontend/src/components/monitoring/`)*

### C. Orphaned Frontend State Stores & Scratch Test Scripts
*Rationale*: Temporary debugging scripts and an unused Zustand-style store unreferenced by the build pipeline.
- `frontend/src/store/useIncidentStore.js` *(and empty `frontend/src/store/` directory)*
- `frontend/test_router.js`
- `frontend/test_router_2.js`
- `frontend/test_ui.js`
- `frontend/tsc_errors.log`

### D. Stray Files & Stale Log Files
*Rationale*: Accidental zero-byte artifacts and stale log files created during previous testing.
- `file` (root directory, 0 bytes)
- `backend/file` (backend directory, 0 bytes)
- `logs/camera.log`
- `logs/errors.log`
- `logs/events.log`
- `logs/system.log`

### E. Unreferenced Test Replay Files (`backend/uploads/replays/session_9999/`)
*Rationale*: 24 mock `.mp4` test clips created during synthetic pipeline testing. Cross-referencing against the live database confirmed zero references in `evidence.replay_clip_path`.
- 24 `.mp4` test files under `backend/uploads/replays/session_9999/`
*(Directory `backend/uploads/replays/session_9999/` removed)*

---

## 4. Replay Files Audit & Verification (Group 2)

Per instructions, all video replays were audited and cross-referenced with PostgreSQL table `evidence` before taking action:

| Metric | Count | Details |
|:---|:---:|:---|
| **Total Replay Files Found** | **72** | In `backend/uploads/replays/` across 9 session folders |
| **Database-Referenced Replays** | **48** | Actively linked in `evidence.replay_clip_path` (`session_265` to `session_274`) |
| **Referenced Replays Preserved** | **48 (100%)** | All 48 files verified to physically exist on disk and link to DB rows |
| **Unreferenced Test Replays** | **24** | Synthetic mock clips located in `session_9999/` with 0 references in DB |
| **Unreferenced Replays Pruned** | **24** | Safely deleted (`backend/uploads/replays/session_9999/`) |

---

## 5. Preserved AI Integration Foundation

The architecture is cleanly prepared to ingest events from the separate, independent AI Monitoring Engine (Phase 2) and Audio Device Detector (Phase 3). The following integration components were strictly preserved:

1. **AI Event Ingestion Endpoint** (`backend/app/api/v1/routes/ai_events.py`):
   - POST `/api/v1/ai-events/ingest`
   - POST `/api/v1/ai-events/batch`
   - Real-time ingestion contract supporting standard violation payloads.
2. **AI Event Processor & Risk Engine** (`backend/app/services/ai_event_processor.py`):
   - Decoupled event normalizer, deduplication window, risk score aggregator, and database persisting pipeline.
3. **Formal Monitoring Contracts** (`backend/app/schemas/monitoring_contracts.py`):
   - Type-safe schemas defining external event schemas (`CanonicalMonitoringEvent`, `EventBatchEnvelope`, `SeverityLevel`, `ConfidenceScore`).
4. **Adapter Layer Stubs** (`backend/app/adapters/__init__.py`, `backend/app/ai/__init__.py`, `backend/app/monitoring_integration/monitoring_session_adapter.py`):
   - Clean package entry points to host adapters for the independent AI engine and audio detector.
5. **Real-time Live WebSocket Broadcaster** (`backend/app/websocket/connection_manager.py` & `/api/v1/ws/{exam_session_id}`):
   - Streams live monitoring alerts and health status directly to examiner dashboards.
6. **Frontend Student Monitoring Preview** (`frontend/src/components/monitoring/StudentLiveMonitoringPreview.tsx`):
   - Production component providing candidate camera preview, permission status, and connection health during active examinations.
7. **Examiner Monitoring Views** (`frontend/src/pages/monitoring/`):
   - `ExamMonitoringPage.tsx`, `CandidateMonitoringPage.tsx`, `IncidentLogPage.tsx`, `AnalyticsDashboardPage.tsx`.

---

## 6. Live Database Preservation Verification

The PostgreSQL database (`exam_db` on `localhost:5432`) was verified directly using SQLAlchemy and asyncpg:

- **Database Alterations**: **0 (ZERO)**. No tables dropped, no columns modified, no constraints altered.
- **Total Tables in Public Schema**: **24 tables intact**:
  `activities`, `ai_events`, `ai_sessions`, `alembic_version`, `candidate_answers`, `evidence`, `exam_assignments`, `exam_question_rules`, `exam_section_rules`, `exam_sessions`, `exam_supervisors`, `exams`, `notifications`, `otps`, `question_options`, `question_papers`, `roles`, `runtime_states`, `students`, `system_logs`, `system_settings`, `users`, `violations`, `workspace_preferences`.
- **Alembic Revision**: `e8bc34567890` (Head, perfectly synchronized).
- **Migration Files**: All 11 Alembic versions in `backend/alembic/versions/` preserved without modification.
- **Database Records Preserved**:
  - `evidence`: 99 rows intact (48 containing active replay links).
  - `exam_sessions`: 15 rows intact.
  - All users, exams, question papers, and assignments 100% intact.

---

## 7. Deferred Items (Model Weights & Training Runs)

Per instructions, large model weight files and training runs were deferred from automated deletion. They are documented below for tracking:

| File / Directory | Size | Origin / Phase | Rationale for Deferral |
|:---|:---:|:---:|:---|
| `models/yoloe/` | ~825 MB | Phase 2 / Experimental | Contains `mobileclip2_b.ts` (768MB), `mobileclip_blt.ts` (49.8MB), and `yoloe-26n-seg.pt` (7MB). Belongs to open-vocabulary segmentation experiments. Deferred until confirmed archived in independent AI repository. |
| `weights/clip/ViT-B-32.pt` | ~338 MB | Phase 2 / Experimental | OpenAI CLIP vision transformer checkpoint used for zero-shot image classification. Deferred until confirmed archived in independent AI repository. |
| `models/wearable_audio/` | ~48.7 MB | Phase 3 / Wearable Audio | Contains `candidate_v3.pt` (6.2MB) and `yolov8s-worldv2.pt` (42.5MB). Baseline models for earphone detection. Deferred until confirmed backed up in Phase 3 repository. |
| `runs/detect/runs/detect/` | ~31 MB | Phase 3 / Training Runs | Contains training curves, confusion matrices, and `best.pt` / `last.pt` checkpoints for `audio_device_poc_v1` and `v2`. Deferred until confirmed backed up in Phase 3 repository. |

---

## 8. Verification Results: Before vs. After

### Backend Pytest Suite
- **Command**: `pytest -q`
- **Before Cleanup**: `73 passed, 82 warnings in 38.43s`
- **After Cleanup**: `73 passed, 82 warnings in 37.67s`
- **Delta**: 0 regressions, 100% pass rate.

### Frontend TypeScript & Vite Production Build
- **Command**: `tsc -b && vite build`
- **Before Cleanup**: `✓ built in 5.60s` (0 errors)
- **After Cleanup**: `✓ built in 4.97s` (0 errors)
- **Delta**: 0 regressions, clean compile.

---

## 9. Core Examination System Functional Status

The Examination System core features were thoroughly audited and verified:

1. **Authentication & RBAC**:
   - JWT token issuance, refresh tokens, role-based access control (`student`, `examiner`, `admin`) operational.
2. **Student Flow**:
   - Student dashboard, exam registration, face enrollment capture, session launching, question paper delivery, answer auto-saving, fullscreen departure detection, and exam final submission intact.
3. **Examiner Flow**:
   - Examiner dashboard, exam creation, question paper rule configuration, student scheduling, supervisor assignments, live exam monitoring, and report generation intact.
4. **Storage & Assets**:
   - Student face enrollment photos (`backend/uploads/faces/`) and active evidence images/replays (`backend/uploads/evidence/`, `backend/uploads/replays/`) accessible and intact.

---

## 10. Remaining Technical Debt & Next Steps

1. **Virtual Environment Pruning**:
   - As documented in `DEPENDENCY_CLEANUP_CANDIDATES.md`, heavy ML packages (`torch`, `ultralytics`, `mediapipe`) in `backend/venv` can be pruned in a future packaging step once the independent AI engine runs in its dedicated container.
2. **Model Files Archival**:
   - Once the user confirms that `models/`, `weights/`, and `runs/` are archived in the standalone Phase 2 and Phase 3 repositories, these folders (~1.24 GB) can be deleted from this repository.
3. **Phase 2 & Phase 3 Integration Readiness**:
   - The Examination System is now clean, lean, and structurally prepared to receive external HTTP/WebSocket event streams from the independent AI Monitoring Engine (Phase 2) and Audio Device Detector (Phase 3) via the preserved `/api/v1/ai-events/ingest` interface.
