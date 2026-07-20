from fastapi import APIRouter
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.exams import router as exams_router
from app.api.v1.routes.monitoring import router as monitoring_router
from app.api.v1.routes.exam_sessions import router as exam_sessions_router
from app.api.v1.routes.ai_sessions import router as ai_sessions_router
from app.api.v1.routes.violations import router as violations_router
from app.api.v1.routes.evidence import router as evidence_router
from app.api.v1.routes.reports import router as reports_router
from app.api.v1.routes.students import router as students_router
from app.api.v1.routes.question_papers import router as question_papers_router
from app.api.v1.routes.ws import router as ws_router
from app.api.v1.routes.ai_events import router as ai_events_router
from app.api.v1.routes.workspace import router as workspace_router
from app.api.v1.routes.student_repository import router as student_repository_router
from app.api.v1.routes.workspace_exams import router as workspace_exams_router
from app.api.v1.routes.candidate_runtime import router as candidate_runtime_router
from app.api.v1.routes.admin import router as admin_router
from app.api.v1.routes.question_paper_builder import router as question_paper_builder_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(exams_router, prefix="/exams", tags=["Exams"])
api_router.include_router(monitoring_router, prefix="/monitoring", tags=["System Monitoring"])
api_router.include_router(exam_sessions_router, prefix="/exam-sessions", tags=["Exam Sessions"])
api_router.include_router(ai_sessions_router, prefix="/ai-sessions", tags=["AI Sessions"])
api_router.include_router(violations_router, prefix="/violations", tags=["Violations"])
api_router.include_router(evidence_router, prefix="/evidence", tags=["Evidence"])
api_router.include_router(reports_router, prefix="/reports", tags=["Monitoring Reports"])
api_router.include_router(students_router, prefix="/students", tags=["Candidate Registration"])
api_router.include_router(question_papers_router, prefix="/question-papers", tags=["Question Papers"])
api_router.include_router(ws_router, prefix="/ws", tags=["WebSockets"])
api_router.include_router(ai_events_router, prefix="/ai-events", tags=["Computer Vision Integration"])
api_router.include_router(question_paper_builder_router, prefix="/question-paper-builder", tags=["Question Paper Builder"])
api_router.include_router(workspace_router, prefix="/workspace", tags=["Examiner Workspace"])
api_router.include_router(student_repository_router, prefix="/workspace/students", tags=["Student Repository"])
api_router.include_router(workspace_exams_router, prefix="/workspace/exams", tags=["Workspace Exams"])
api_router.include_router(candidate_runtime_router, prefix="/runtime", tags=["Candidate Runtime"])
api_router.include_router(admin_router, prefix="/admin", tags=["Platform Administration"])
