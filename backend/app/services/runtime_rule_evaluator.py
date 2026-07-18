from typing import Optional
import logging

from app.models.exam_session import ExamSession
from app.models.runtime_state import RuntimeState
from app.models.exam_section_rule import ExamSectionRule
from app.models.exam_question_rule import ExamQuestionRule

logger = logging.getLogger(__name__)

class RuntimeRuleEvaluator:
    """
    Evaluates Candidate Actions against RuntimeRules.
    """

    @staticmethod
    def evaluate_navigation(session: ExamSession, state: RuntimeState, target_section_index: int, target_question_index: int) -> bool:
        """
        Determines if navigating to the target section and question is permitted.
        Raises ValueError if not permitted.
        """
        exam = session.exam
        if not exam:
            raise ValueError("Exam configuration missing.")
            
        # If moving to the same place, allow
        if state.current_section_index == target_section_index and state.current_question_index == target_question_index:
            return True

        # Find section rule
        section_rule = next((r for r in exam.section_rules if r.section_index == state.current_section_index), None)
        target_section_rule = next((r for r in exam.section_rules if r.section_index == target_section_index), None)
        
        # Cross-section navigation checks
        if state.current_section_index != target_section_index:
            if section_rule and section_rule.require_completion_before_next:
                # We would need to check if all questions in section are submitted.
                # For now, we trust CandidateAnswer logic or assume lock arrays.
                if state.current_section_index not in state.completed_sections:
                    raise ValueError(f"Must complete section {state.current_section_index} before navigating away.")
            
            # Going backward across sections
            if target_section_index < state.current_section_index:
                # Based on exam.global_navigation
                if exam.global_navigation == "SEQUENTIAL":
                    raise ValueError("Exam enforces sequential section navigation. Cannot return to previous sections.")
        
        # Intra-section navigation checks
        if section_rule and section_rule.navigation_policy == "SEQUENTIAL":
            if target_question_index < state.current_question_index:
                if not section_rule.allow_return_to_previous:
                    raise ValueError("Sequential navigation enforced. Cannot return to previous questions in this section.")
                    
            if target_question_index > state.current_question_index + 1:
                raise ValueError("Sequential navigation enforced. Cannot skip questions.")

        # Finally, check if the target is locked
        if target_section_index in state.locked_sections:
            raise ValueError(f"Section {target_section_index} is locked.")
            
        if target_question_index in state.locked_questions:
            raise ValueError(f"Question {target_question_index} is locked.")

        return True

    @staticmethod
    def evaluate_submission_lock(session: ExamSession, state: RuntimeState, section_index: int, question_index: int, submission_count: int) -> bool:
        """
        Evaluates whether a question should be locked after a submission.
        Returns True if it should be locked, False otherwise.
        """
        exam = session.exam
        if not exam:
            return False
            
        section_rule = next((r for r in exam.section_rules if r.section_index == section_index), None)
        if not section_rule:
            return False
            
        question_rule = next((q for q in section_rule.question_rules if q.question_index == question_index), None)
        if not question_rule:
            return False
            
        if question_rule.lock_immediately_after_submission:
            return True
            
        if question_rule.allow_multiple_submissions and question_rule.max_submission_count:
            if submission_count >= question_rule.max_submission_count:
                return True
                
        return False
