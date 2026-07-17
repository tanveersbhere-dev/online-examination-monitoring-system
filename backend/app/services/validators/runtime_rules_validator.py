from typing import Optional
from app.schemas.runtime_rules import RuntimeRulesUpdate

class RuntimeRulesValidator:
    @staticmethod
    def validate(rules: RuntimeRulesUpdate) -> None:
        """
        Validates a complex tree of runtime rules across Assessment, Section, and Question levels.
        Raises ValueError if conflicting configuration is found.
        """
        # Validate Level 1 rules (Implicit via Pydantic types, but complex relationships here if needed)
        
        for section in rules.sections:
            # Validate Section-level combinations
            if section.navigation_policy == "SEQUENTIAL" and section.allow_return_to_previous:
                raise ValueError(f"Section '{section.section_name}' cannot allow return to previous questions under SEQUENTIAL navigation policy.")
            
            for q in section.question_rules:
                # Validate Question-level combinations
                if q.lock_immediately_after_submission and q.editable_after_submission:
                    raise ValueError(f"Question {q.question_index} in Section '{section.section_name}' cannot be both locked immediately and editable after submission.")
                
                if q.individual_submission and not q.autosave:
                    raise ValueError(f"Question {q.question_index} requires autosave to be enabled for individual submission mode.")
                
                if q.allow_multiple_submissions and not q.individual_submission:
                    raise ValueError(f"Question {q.question_index} must have individual_submission enabled to allow multiple submissions.")
                
                if q.max_submission_count is not None and not q.allow_multiple_submissions:
                    raise ValueError(f"Question {q.question_index} has max_submission_count set but allow_multiple_submissions is False.")
