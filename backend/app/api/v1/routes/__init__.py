from fastapi import APIRouter
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.exams import router as exams_router
from app.api.v1.routes.monitoring import router as monitoring_router
from app.api.v1.routes.violations import router as violations_router
from app.api.v1.routes.evidence import router as evidence_router
from app.api.v1.routes.reports import router as reports_router
from app.api.v1.routes.students import router as students_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(exams_router, prefix="/exams", tags=["Exams"])
api_router.include_router(monitoring_router, prefix="/monitoring", tags=["Live Monitoring"])
api_router.include_router(violations_router, prefix="/violations", tags=["Violations"])
api_router.include_router(evidence_router, prefix="/evidence", tags=["Evidence"])
api_router.include_router(reports_router, prefix="/reports", tags=["Monitoring Reports"])
api_router.include_router(students_router, prefix="/students", tags=["Candidate Registration"])
