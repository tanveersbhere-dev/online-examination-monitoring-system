from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.models.runtime_state import RuntimeState
from app.repositories.runtime_state_repository import RuntimeStateRepository
from app.repositories.exam_session_repository import ExamSessionRepository
from app.schemas.runtime_state import RuntimeStateResponse, RuntimeStateUpdate
from app.repositories.exceptions import EntityNotFoundError

logger = logging.getLogger(__name__)

class RuntimeStateService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RuntimeStateRepository(db)
        self.session_repo = ExamSessionRepository(db)

    async def initialize_state(self, exam_session_id: int) -> RuntimeStateResponse:
        existing = await self.repo.get_by_session_id(exam_session_id)
        if existing:
            return RuntimeStateResponse.model_validate(existing)
            
        new_state = await self.repo.create(
            exam_session_id=exam_session_id,
            current_section_index=0,
            current_question_index=0,
            navigation_history=[],
            completed_sections=[],
            locked_sections=[],
            locked_questions=[],
            execution_flags={}
        )
        return RuntimeStateResponse.model_validate(new_state)

    async def get_state(self, exam_session_id: int) -> RuntimeStateResponse:
        state = await self.repo.get_by_session_id(exam_session_id)
        if not state:
            raise EntityNotFoundError(f"RuntimeState for session {exam_session_id} not found.")
        return RuntimeStateResponse.model_validate(state)

    async def update_position(self, exam_session_id: int, section_index: int, question_index: int) -> RuntimeStateResponse:
        state = await self.repo.get_by_session_id(exam_session_id)
        if not state:
            raise EntityNotFoundError(f"RuntimeState for session {exam_session_id} not found.")
            
        session = await self.session_repo.get_by_id(exam_session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {exam_session_id} not found.")

        from app.services.runtime_rule_evaluator import RuntimeRuleEvaluator
        # This will raise ValueError if navigation is not allowed
        RuntimeRuleEvaluator.evaluate_navigation(session, state, section_index, question_index)
            
        state.current_section_index = section_index
        state.current_question_index = question_index
        
        # Simple navigation tracking
        nav_entry = {"section": section_index, "question": question_index}
        if nav_entry not in state.navigation_history:
            state.navigation_history = state.navigation_history + [nav_entry] # reassign to trigger SQLAlchemy JSON change
            
        await self.db.commit()
        await self.db.refresh(state)
        return RuntimeStateResponse.model_validate(state)

    async def complete_section(self, exam_session_id: int, section_index: int) -> RuntimeStateResponse:
        state = await self.repo.get_by_session_id(exam_session_id)
        if not state:
            raise EntityNotFoundError(f"RuntimeState for session {exam_session_id} not found.")

        session = await self.session_repo.get_by_id(exam_session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {exam_session_id} not found.")

        # Mark section as completed
        completed = list(state.completed_sections or [])
        if section_index not in completed:
            completed.append(section_index)
        state.completed_sections = completed

        # Check section rule for locking
        exam = session.exam
        locked = list(state.locked_sections or [])
        if exam:
            rules_source = exam.section_rules if exam.section_rules else (exam.question_paper.section_rules if exam.question_paper else [])
            sec_rule = next((r for r in rules_source if r.section_index == section_index), None)
            if sec_rule and (sec_rule.lock_after_timeout or not sec_rule.allow_return_to_previous or sec_rule.require_completion_before_next):
                if section_index not in locked:
                    locked.append(section_index)
        state.locked_sections = locked

        # Advance to next section if exists
        next_sec_index = section_index + 1
        state.current_section_index = next_sec_index
        state.current_question_index = 0

        nav_entry = {"section": next_sec_index, "question": 0}
        state.navigation_history = (state.navigation_history or []) + [nav_entry]

        await self.db.commit()
        await self.db.refresh(state)
        return RuntimeStateResponse.model_validate(state)
