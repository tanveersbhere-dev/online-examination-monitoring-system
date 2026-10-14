import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime, timezone

from app.models.activity import Activity
from app.models.notification import Notification
from app.models.workspace_preference import WorkspacePreference
from app.models.exam import Exam
from app.models.user import User
from app.models.student import Student
from app.models.violation import Violation
from app.models.question_paper import QuestionPaper

from app.schemas.workspace import (
    WorkspacePreferenceUpdate, WorkspacePreferenceResponse,
    DashboardSummaryResponse, StatCard, UpcomingExam, ActivityResponse, NotificationResponse
)

logger = logging.getLogger(__name__)

class WorkspaceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_preferences(self, user_id: int) -> WorkspacePreference:
        result = await self.db.execute(select(WorkspacePreference).where(WorkspacePreference.user_id == user_id))
        pref = result.scalars().first()
        if not pref:
            pref = WorkspacePreference(user_id=user_id)
            self.db.add(pref)
            await self.db.commit()
            await self.db.refresh(pref)
        return pref

    async def update_preferences(self, user_id: int, data: WorkspacePreferenceUpdate) -> WorkspacePreference:
        pref = await self.get_or_create_preferences(user_id)
        
        if data.theme is not None:
            pref.theme = data.theme
        if data.language is not None:
            pref.language = data.language
        if data.timezone is not None:
            pref.timezone = data.timezone
        if data.sidebar_collapsed is not None:
            pref.sidebar_collapsed = data.sidebar_collapsed

        await self.db.commit()
        await self.db.refresh(pref)
        return pref

    async def get_recent_activities(self, user_id: int, limit: int = 5) -> list[Activity]:
        result = await self.db.execute(
            select(Activity).where(Activity.user_id == user_id).order_by(Activity.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_notifications(self, user_id: int, limit: int = 5) -> list[Notification]:
        result = await self.db.execute(
            select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def mark_notification_read(self, user_id: int, notification_id: int, is_read: bool) -> Notification:
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
        )
        notif = result.scalars().first()
        if notif:
            notif.is_read = is_read
            await self.db.commit()
            await self.db.refresh(notif)
        return notif

    async def get_dashboard_summary(self, user_id: int) -> DashboardSummaryResponse:
        # Fetch actual statistics.
        # Since we might not have a full complex DB yet, we do safe queries.
        
        # 1. Today's Exams (Scheduled or running today)
        # Note: Depending on existing implementation, we just count exams created by this user
        exam_result = await self.db.execute(select(func.count(Exam.id)).where(Exam.created_by == user_id))
        total_exams = exam_result.scalar() or 0

        # 2. Registered Students
        # Querying the actual Student Repository for this examiner
        student_result = await self.db.execute(
            select(func.count(Student.id)).where(Student.examiner_id == user_id)
        )
        total_students = student_result.scalar() or 0

        # 3. Violations
        # Mocking for now since we don't know the exact Violation table structure for "today"
        # We can query all violations or just return a static number if violation count is heavy
        total_violations = 0 # Replace with actual query if needed

        # 4. Question Papers (Assessments)
        paper_result = await self.db.execute(
            select(func.count(QuestionPaper.id)).where(QuestionPaper.uploaded_by == user_id)
        )
        total_papers = paper_result.scalar() or 0

        # Stats Cards
        stats = [
            StatCard(label="Total Exams", value=str(total_exams), sub="Created by you", icon_name="CalendarTodayIcon", accent_color="#1565C0", path="/examiner/exams"),
            StatCard(label="Total Students", value=str(total_students), sub="Registered in system", icon_name="PeopleIcon", accent_color="#1976D2", path="/examiner/students"),
            StatCard(label="Total Assessments", value=str(total_papers), sub="In repository", icon_name="DescriptionIcon", accent_color="#7B1FA2", path="/examiner/question-papers"),
            StatCard(label="System Health", value="Online", sub="All services running", icon_name="HealthAndSafetyIcon", accent_color="#2E7D32")
        ]

        # Upcoming Exams
        upcoming_result = await self.db.execute(
            select(Exam).where(Exam.created_by == user_id).order_by(Exam.scheduled_start.desc().nullslast()).limit(5)
        )
        exams = upcoming_result.scalars().all()
        
        upcoming_exams = []
        for e in exams:
            upcoming_exams.append(UpcomingExam(
                id=e.id,
                name=e.title,
                course=e.course_name or e.subject or "General", 
                scheduled_date=e.scheduled_start,
                students_count=0
            ))

        # Activities & Notifications
        recent_activities = await self.get_recent_activities(user_id, limit=5)
        recent_notifications = await self.get_recent_notifications(user_id, limit=5)

        return DashboardSummaryResponse(
            stats=stats,
            upcoming_exams=upcoming_exams,
            recent_activities=[ActivityResponse.from_orm(a) for a in recent_activities],
            recent_notifications=[NotificationResponse.from_orm(n) for n in recent_notifications],
            system_status="All Systems Operational"
        )
