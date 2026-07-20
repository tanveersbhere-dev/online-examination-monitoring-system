from typing import List, Optional
from pydantic import BaseModel, Field

class QuestionOptionBase(BaseModel):
    option_text: str
    is_correct: bool = False

class QuestionOptionCreate(QuestionOptionBase):
    pass

class QuestionOptionResponse(QuestionOptionBase):
    id: int
    question_rule_id: int

    class Config:
        from_attributes = True

class StructuredQuestionBase(BaseModel):
    question_index: int
    question_type: str = "MCQ"
    marks: int = 1
    is_required: bool = True
    question_text: str
    image_url: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = None

class StructuredQuestionCreate(StructuredQuestionBase):
    options: Optional[List[QuestionOptionCreate]] = []

class StructuredQuestionResponse(StructuredQuestionBase):
    id: int
    section_rule_id: int
    options: List[QuestionOptionResponse]

    class Config:
        from_attributes = True

class StructuredGroupBase(BaseModel):
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

class StructuredGroupCreate(StructuredGroupBase):
    questions: Optional[List[StructuredQuestionCreate]] = []

class StructuredGroupResponse(StructuredGroupBase):
    id: int
    question_paper_id: int
    question_rules: List[StructuredQuestionResponse]

    class Config:
        from_attributes = True

class StructuredPaperCreate(BaseModel):
    title: str
    course_name: str
    description: Optional[str] = None

class StructuredPaperResponse(BaseModel):
    id: int
    title: str
    course_name: str
    description: Optional[str]
    mode: str
    version: int
    status: str
    section_rules: List[StructuredGroupResponse]

    class Config:
        from_attributes = True
