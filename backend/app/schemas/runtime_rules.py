from pydantic import BaseModel
from typing import Optional, List

class QuestionRuleBase(BaseModel):
    question_index: int
    question_type: str = "MCQ"
    marks: int = 1
    is_required: bool = True
    character_limit: Optional[int] = None
    word_limit: Optional[int] = None
    attachment_allowed: bool = False
    question_timer_seconds: Optional[int] = None
    autosave: bool = True
    individual_submission: bool = False
    editable_after_submission: bool = False
    allow_multiple_submissions: bool = False
    max_submission_count: Optional[int] = None
    allow_editing_until_final: bool = True
    lock_immediately_after_submission: bool = False
    show_correctness_immediately: bool = False
    instructions: Optional[str] = None

class QuestionRuleCreate(QuestionRuleBase):
    pass

class QuestionRuleResponse(QuestionRuleBase):
    id: int
    section_rule_id: int
    exam_id: int

    class Config:
        from_attributes = True

class SectionRuleBase(BaseModel):
    section_index: int
    section_name: str
    section_type: str = "MCQ"
    section_duration_minutes: Optional[int] = None
    navigation_policy: str = "FREE"
    allow_return_to_previous: bool = True
    lock_after_timeout: bool = False
    randomize_questions: bool = False
    require_completion_before_next: bool = False
    section_weight: float = 1.0
    instructions: Optional[str] = None

class SectionRuleCreate(SectionRuleBase):
    question_rules: List[QuestionRuleCreate] = []

class SectionRuleResponse(SectionRuleBase):
    id: int
    exam_id: int
    question_rules: List[QuestionRuleResponse] = []

    class Config:
        from_attributes = True

class RuntimeRulesUpdate(BaseModel):
    allow_resume_after_disconnect: Optional[bool] = None
    global_navigation: Optional[str] = None
    randomize_sections: Optional[bool] = None
    randomize_questions: Optional[bool] = None
    allow_review_before_submit: Optional[bool] = None
    show_remaining_time: Optional[bool] = None
    show_question_numbers: Optional[bool] = None
    show_marks: Optional[bool] = None
    
    sections: List[SectionRuleCreate] = []
