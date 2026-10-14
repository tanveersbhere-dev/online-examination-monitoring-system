from sqlalchemy.ext.asyncio import AsyncSession
import logging
from typing import List

from app.schemas.candidate_answer import CandidateAnswerResponse, CandidateAnswerUpdate, CandidateAnswerCreate
from app.repositories.candidate_answer_repository import CandidateAnswerRepository
from app.services.runtime_state_service import RuntimeStateService
from app.repositories.exceptions import EntityNotFoundError

logger = logging.getLogger(__name__)

class CandidateAnswerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CandidateAnswerRepository(db)
        self.state_service = RuntimeStateService(db)

    async def get_session_answers(self, exam_session_id: int) -> List[CandidateAnswerResponse]:
        answers = await self.repo.get_all_for_session(exam_session_id)
        return [CandidateAnswerResponse.model_validate(ans) for ans in answers]

    async def save_answer(self, exam_session_id: int, section_index: int, question_index: int, answer_in: CandidateAnswerUpdate) -> CandidateAnswerResponse:
        # Consult Runtime State Engine for permission
        state = await self.state_service.get_state(exam_session_id)
        
        if section_index in state.locked_sections:
            raise ValueError(f"Section {section_index} is locked.")
            
        if question_index in state.locked_questions:
            raise ValueError(f"Question {question_index} in section {section_index} is locked.")

        # If not locked, proceed to upsert
        existing = await self.repo.get_by_question(exam_session_id, section_index, question_index)
        
        updated_sub_count = 0
        if existing:
            update_data = answer_in.model_dump(exclude_unset=True)
            if update_data.get("is_submitted", False) and not existing.is_submitted:
                existing.submission_count += 1
                updated_sub_count = existing.submission_count
            updated = await self.repo.update(existing, **update_data)
            ans_response = CandidateAnswerResponse.model_validate(updated)
        else:
            is_sub = answer_in.is_submitted if answer_in.is_submitted is not None else False
            sub_count = 1 if is_sub else 0
            updated_sub_count = sub_count
            
            ans_status = answer_in.answer_status or ("ANSWERED" if answer_in.answer_data else "NOT_ANSWERED")
            new_ans = await self.repo.create(
                exam_session_id=exam_session_id,
                section_index=section_index,
                question_index=question_index,
                answer_data=answer_in.answer_data or {},
                answer_status=ans_status,
                is_submitted=is_sub,
                submission_count=sub_count
            )
            ans_response = CandidateAnswerResponse.model_validate(new_ans)

        # Check if this submission triggered a lock
        if updated_sub_count > 0:
            session = await self.state_service.session_repo.get_by_id(exam_session_id)
            if session:
                from app.services.runtime_rule_evaluator import RuntimeRuleEvaluator
                should_lock = RuntimeRuleEvaluator.evaluate_submission_lock(session, state, section_index, question_index, updated_sub_count)
                if should_lock:
                    if question_index not in state.locked_questions:
                        state.locked_questions = state.locked_questions + [question_index]
                        await self.db.commit()

        return ans_response
