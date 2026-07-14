from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.violation_repository import ViolationRepository
from app.repositories.exceptions import EntityNotFoundError
from app.schemas.violation import ViolationResponse
from app.services.exceptions import ViolationNotFoundError

class ViolationService:
    def __init__(self, db: AsyncSession):
        self.repo = ViolationRepository(db)

    async def get_all_by_session(self, exam_session_id: int, skip: int = 0, limit: int = 100) -> List[ViolationResponse]:
        # Using get_all for simplicity; ideally we'd filter by exam_session_id natively in repo
        violations = await self.repo.get_all(skip=skip, limit=limit)
        filtered = [v for v in violations if v.exam_session_id == exam_session_id]
        return [ViolationResponse.model_validate(v) for v in filtered]

    async def get_by_id(self, violation_id: int) -> ViolationResponse:
        try:
            violation = await self.repo.get_by_id(violation_id)
            if not violation:
                raise ViolationNotFoundError(f"Violation {violation_id} not found.")
            return ViolationResponse.model_validate(violation)
        except EntityNotFoundError:
            raise ViolationNotFoundError(f"Violation {violation_id} not found.")
