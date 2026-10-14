from typing import List, Optional
from pydantic import BaseModel, Field, validator

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
    question_index: int = Field(..., ge=0)
    question_type: str = "MCQ"
    marks: int = 1
    is_required: bool = True
    question_text: str
    image_url: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = None

    @validator('marks', pre=True, always=True)
    def validate_marks(cls, v):
        if v is None or v == '':
            raise ValueError("Question marks cannot be empty.")
        if isinstance(v, float) and not v.is_integer():
            raise ValueError("Question marks must be a positive integer without fractional decimals.")
        if isinstance(v, str):
            if '.' in v:
                try:
                    f_val = float(v)
                    if not f_val.is_integer():
                        raise ValueError("Question marks must be a positive integer without fractional decimals.")
                    v = int(f_val)
                except ValueError:
                    raise ValueError("Question marks must be a positive integer.")
            elif not v.isdigit():
                raise ValueError("Question marks must be a positive integer.")
            else:
                v = int(v)
        if not isinstance(v, int) or isinstance(v, bool) or v < 1:
            raise ValueError("Question marks must be a positive integer greater than or equal to 1.")
        return v

class StructuredQuestionCreate(StructuredQuestionBase):
    options: Optional[List[QuestionOptionCreate]] = []

class StructuredQuestionResponse(StructuredQuestionBase):
    id: int
    section_rule_id: int
    options: List[QuestionOptionResponse]
    calculated_marks: Optional[float] = 1.0

    class Config:
        from_attributes = True

class StructuredGroupBase(BaseModel):
    section_index: int = Field(..., ge=0)
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

    @validator('section_duration_minutes', pre=True)
    def validate_section_duration(cls, v):
        if v is None or v == '':
            return None
        if isinstance(v, float) and not v.is_integer():
            raise ValueError("Section duration must be an integer without decimals.")
        if isinstance(v, str):
            if not v.isdigit():
                raise ValueError("Section duration must be a positive integer greater than 0.")
            v = int(v)
        if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
            raise ValueError("Section duration must be a positive integer greater than 0.")
        return v

    @validator('section_weight', pre=True, always=True)
    def validate_section_weight(cls, v):
        if v is None or v == '':
            return 1.0
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if v <= 0:
                raise ValueError("Section weight must be a positive number greater than 0.")
            return float(v)
        if isinstance(v, str):
            try:
                f_val = float(v)
                if f_val <= 0:
                    raise ValueError("Section weight must be a positive number greater than 0.")
                return f_val
            except ValueError:
                raise ValueError("Section weight must be a valid positive number.")
        raise ValueError("Section weight must be a positive number greater than 0.")

class StructuredGroupCreate(StructuredGroupBase):
    questions: Optional[List[StructuredQuestionCreate]] = []

class StructuredGroupResponse(StructuredGroupBase):
    id: int
    question_paper_id: int
    question_rules: List[StructuredQuestionResponse]
    question_count: Optional[int] = 0
    total_section_marks: Optional[float] = 1.0
    calculated_weight_per_question: Optional[float] = 1.0

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
    total_marks: Optional[float] = 0.0
    total_questions: Optional[int] = 0
    paper_academic_duration_minutes: Optional[int] = 50
    recommended_recovery_buffer_minutes: Optional[int] = 10
    recommended_schedule_window_minutes: Optional[int] = 60
    section_rules: List[StructuredGroupResponse]

    class Config:
        from_attributes = True
