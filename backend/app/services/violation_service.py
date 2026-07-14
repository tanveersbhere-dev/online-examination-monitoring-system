from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.violation import ViolationCreate, ViolationUpdate, ViolationResponse
from app.repositories.violation_repository import ViolationRepository
from app.repositories.exam_session_repository import ExamSessionRepository
from app.repositories.exceptions import EntityNotFoundError
from app.services.exceptions import ViolationNotFoundError, AuthorizationError

class ViolationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ViolationRepository(db)
        self.exam_session_repo = ExamSessionRepository(db)

    async def create_violation(self, violation_in: ViolationCreate) -> ViolationResponse:
        # Validate ExamSession
        exam_session = await self.exam_session_repo.get_by_id(violation_in.exam_session_id)
        if not exam_session:
            raise EntityNotFoundError(f"ExamSession {violation_in.exam_session_id} not found.")

        # Let backend define timestamp if not provided
        timestamp = violation_in.timestamp or datetime.now(timezone.utc)

        db_violation = await self.repo.create(
            exam_session_id=violation_in.exam_session_id,
            ai_session_id=violation_in.ai_session_id,
            violation_type=violation_in.violation_type,
            category=violation_in.category,
            severity=violation_in.severity,
            risk_score=violation_in.risk_score,
            timestamp=timestamp,
            description=violation_in.description,
            status="PENDING"
        )
        return ViolationResponse.model_validate(db_violation)

    async def get_by_id(self, violation_id: int) -> ViolationResponse:
        violation = await self.repo.get_by_id(violation_id)
        if not violation:
            raise ViolationNotFoundError(f"Violation {violation_id} not found.")
        return ViolationResponse.model_validate(violation)

    async def update_violation(self, violation_id: int, update_data: ViolationUpdate) -> ViolationResponse:
        violation = await self.repo.get_by_id(violation_id)
        if not violation:
            raise ViolationNotFoundError(f"Violation {violation_id} not found.")

        valid_transitions = {
            "PENDING": ["REVIEWED", "CONFIRMED", "DISMISSED"],
            "REVIEWED": ["CONFIRMED", "DISMISSED"],
            "CONFIRMED": ["DISMISSED"],
            "DISMISSED": ["CONFIRMED"]
        }

        # Validate status transition if status is being updated
        if update_data.status and update_data.status != violation.status:
            if update_data.status not in valid_transitions.get(violation.status, []):
                raise ValueError(f"Invalid violation status transition from {violation.status} to {update_data.status}")

        update_dict = update_data.model_dump(exclude_unset=True)
        updated_obj = await self.repo.update(violation, **update_dict)
        return ViolationResponse.model_validate(updated_obj)

    async def delete_violation(self, violation_id: int) -> None:
        violation = await self.repo.get_by_id(violation_id)
        if not violation:
            raise ViolationNotFoundError(f"Violation {violation_id} not found.")
        
        if violation.status in ["CONFIRMED"]:
            raise ValueError("Cannot delete a confirmed violation.")
            
        await self.repo.delete(violation_id)

    async def filter_violations(
        self,
        exam_id: Optional[int] = None,
        student_id: Optional[int] = None,
        severity: Optional[str] = None,
        violation_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ViolationResponse]:
        violations = await self.repo.filter_violations(
            exam_id=exam_id,
            student_id=student_id,
            severity=severity,
            violation_type=violation_type,
            status=status,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit
        )
        return [ViolationResponse.model_validate(v) for v in violations]
