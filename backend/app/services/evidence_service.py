from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.exceptions import EntityNotFoundError
from app.schemas.evidence import EvidenceResponse
from app.services.exceptions import EvidenceNotFoundError

class EvidenceService:
    def __init__(self, db: AsyncSession):
        self.repo = EvidenceRepository(db)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[EvidenceResponse]:
        evidences = await self.repo.get_all(skip=skip, limit=limit)
        return [EvidenceResponse.model_validate(e) for e in evidences]

    async def get_by_id(self, evidence_id: int) -> EvidenceResponse:
        try:
            evidence = await self.repo.get_by_id(evidence_id)
            if not evidence:
                raise EvidenceNotFoundError(f"Evidence {evidence_id} not found.")
            return EvidenceResponse.model_validate(evidence)
        except EntityNotFoundError:
            raise EvidenceNotFoundError(f"Evidence {evidence_id} not found.")
