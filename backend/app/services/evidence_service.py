from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.evidence import EvidenceCreate, EvidenceUpdate, EvidenceResponse
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.violation_repository import ViolationRepository
from app.repositories.exceptions import EntityNotFoundError
from app.services.exceptions import AuthorizationError

class EvidenceNotFoundError(Exception):
    pass

class EvidenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EvidenceRepository(db)
        self.violation_repo = ViolationRepository(db)

    async def create_evidence(self, evidence_in: EvidenceCreate) -> EvidenceResponse:
        # Validate Violation
        violation = await self.violation_repo.get_by_id(evidence_in.violation_id)
        if not violation:
            raise EntityNotFoundError(f"Violation {evidence_in.violation_id} not found.")

        # Evidence linked to CONFIRMED violations must remain immutable (cannot add new evidence)
        if violation.status == "CONFIRMED":
            raise ValueError("Cannot add evidence to a confirmed violation.")

        timestamp = evidence_in.timestamp or datetime.now(timezone.utc)

        db_evidence = await self.repo.create(
            violation_id=evidence_in.violation_id,
            file_path=evidence_in.file_path,
            evidence_type=evidence_in.evidence_type,
            timestamp=timestamp,
            metadata_payload=evidence_in.metadata_payload,
            confidence_score=evidence_in.confidence_score
        )
        return EvidenceResponse.model_validate(db_evidence)

    async def get_by_id(self, evidence_id: int) -> EvidenceResponse:
        evidence = await self.repo.get_by_id(evidence_id)
        if not evidence:
            raise EvidenceNotFoundError(f"Evidence {evidence_id} not found.")
        return EvidenceResponse.model_validate(evidence)

    async def update_evidence(self, evidence_id: int, update_data: EvidenceUpdate) -> EvidenceResponse:
        evidence = await self.repo.get_by_id(evidence_id)
        if not evidence:
            raise EvidenceNotFoundError(f"Evidence {evidence_id} not found.")

        # Evidence linked to CONFIRMED violations must remain immutable
        if evidence.violation.status == "CONFIRMED":
            raise ValueError("Cannot modify evidence linked to a confirmed violation.")

        update_dict = update_data.model_dump(exclude_unset=True)
        updated_obj = await self.repo.update(evidence, **update_dict)
        return EvidenceResponse.model_validate(updated_obj)

    async def delete_evidence(self, evidence_id: int) -> None:
        evidence = await self.repo.get_by_id(evidence_id)
        if not evidence:
            raise EvidenceNotFoundError(f"Evidence {evidence_id} not found.")
        
        # Evidence linked to CONFIRMED violations must remain immutable
        if evidence.violation.status == "CONFIRMED":
            raise ValueError("Cannot delete evidence linked to a confirmed violation.")
            
        await self.repo.delete(evidence_id)

    async def filter_evidence(
        self,
        violation_id: Optional[int] = None,
        evidence_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[EvidenceResponse]:
        evidences = await self.repo.filter_evidence(
            violation_id=violation_id,
            evidence_type=evidence_type,
            skip=skip,
            limit=limit
        )
        return [EvidenceResponse.model_validate(e) for e in evidences]
