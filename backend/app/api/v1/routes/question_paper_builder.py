from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.session import get_db
from app.security.dependencies import get_current_user
from app.models.user import User
from app.models.question_paper import QuestionPaper
from app.models.exam_section_rule import ExamSectionRule
from app.models.exam_question_rule import ExamQuestionRule
from app.models.question_option import QuestionOption
from app.schemas.question_paper_builder import (
    StructuredPaperCreate, StructuredPaperResponse,
    StructuredGroupCreate, StructuredGroupResponse,
    StructuredQuestionCreate, StructuredQuestionResponse,
    QuestionOptionCreate, QuestionOptionResponse
)

router = APIRouter()

async def get_paper_or_404(paper_id: int, db: AsyncSession, user: User, check_mutable: bool = False) -> QuestionPaper:
    query = select(QuestionPaper).options(
        selectinload(QuestionPaper.section_rules).selectinload(ExamSectionRule.question_rules).selectinload(ExamQuestionRule.options)
    ).where(QuestionPaper.id == paper_id)
    
    result = await db.execute(query)
    paper = result.scalar_one_or_none()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Question Paper not found")
        
    is_admin = user.role and user.role.name == "Admin"
    if not is_admin and paper.uploaded_by != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    if paper.mode != "STRUCTURED":
        raise HTTPException(status_code=400, detail="Not a STRUCTURED mode Question Paper")
        
    if check_mutable:
        from app.services.question_paper_service import QuestionPaperService
        qp_service = QuestionPaperService(db)
        if await qp_service.check_paper_in_use(paper):
            raise HTTPException(
                status_code=400,
                detail="This question paper is in active use by an examination attempt and cannot be modified. To make changes, please create a duplicate or new paper."
            )
        
    return paper

@router.post("/", response_model=StructuredPaperResponse)
async def create_structured_paper(
    paper_in: StructuredPaperCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    paper = QuestionPaper(
        title=paper_in.title,
        course_name=paper_in.course_name,
        description=paper_in.description,
        uploaded_by=current_user.id,
        mode="STRUCTURED",
        version=1,
        status="DRAFT"
    )
    db.add(paper)
    await db.commit()
    await db.refresh(paper)
    
    return StructuredPaperResponse(
        id=paper.id,
        title=paper.title,
        course_name=paper.course_name,
        description=paper.description,
        uploaded_by=paper.uploaded_by,
        mode=paper.mode,
        version=paper.version,
        status=paper.status,
        created_at=paper.created_at,
        updated_at=paper.updated_at,
        section_rules=[]
    )

@router.get("/{paper_id}/full", response_model=StructuredPaperResponse)
async def get_structured_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    paper = await get_paper_or_404(paper_id, db, current_user)
    
    formatted_groups = []
    total_paper_marks = 0.0
    total_questions_count = 0
    total_academic_duration = 0

    for g in paper.section_rules:
        q_rules = g.question_rules or []
        q_count = len(q_rules)
        
        # Calculate true section marks by summing actual marks of all questions
        if q_rules:
            sec_marks = sum(float(q.marks if (q.marks is not None and q.marks > 0) else 1) for q in q_rules)
        else:
            sec_marks = float(g.section_weight) if g.section_weight else 0.0
            
        calculated_weight = round(sec_marks / q_count, 4) if q_count > 0 else 0.0
        
        total_paper_marks += sec_marks
        total_questions_count += q_count
        if g.section_duration_minutes and g.section_duration_minutes > 0:
            total_academic_duration += g.section_duration_minutes

        formatted_questions = []
        for q in q_rules:
            opts = [QuestionOptionResponse.model_validate(opt) for opt in (q.options or [])]
            q_marks = q.marks if (q.marks is not None and q.marks > 0) else 1
            formatted_questions.append(
                StructuredQuestionResponse(
                    id=q.id,
                    section_rule_id=q.section_rule_id,
                    question_index=q.question_index,
                    question_type=q.question_type,
                    marks=q_marks,
                    calculated_marks=float(q_marks),
                    is_required=q.is_required,
                    question_text=q.question_text or "",
                    image_url=q.image_url,
                    explanation=q.explanation,
                    difficulty=q.difficulty,
                    options=opts
                )
            )

        formatted_groups.append(
            StructuredGroupResponse(
                id=g.id,
                question_paper_id=g.question_paper_id,
                section_index=g.section_index,
                section_name=g.section_name,
                section_type=g.section_type,
                section_duration_minutes=g.section_duration_minutes,
                navigation_policy=g.navigation_policy,
                allow_return_to_previous=g.allow_return_to_previous,
                lock_after_timeout=g.lock_after_timeout,
                randomize_questions=g.randomize_questions,
                require_completion_before_next=g.require_completion_before_next,
                section_weight=sec_marks,
                instructions=g.instructions,
                question_count=q_count,
                total_section_marks=round(sec_marks, 2),
                calculated_weight_per_question=calculated_weight,
                question_rules=formatted_questions
            )
        )

    academic_duration = total_academic_duration if total_academic_duration > 0 else 50
    recovery_buffer = 10
    recommended_schedule_window = academic_duration + recovery_buffer

    return StructuredPaperResponse(
        id=paper.id,
        title=paper.title,
        course_name=paper.course_name,
        description=paper.description,
        mode=paper.mode,
        version=paper.version,
        status=paper.status,
        total_marks=round(total_paper_marks, 2),
        total_questions=total_questions_count,
        paper_academic_duration_minutes=academic_duration,
        recommended_recovery_buffer_minutes=recovery_buffer,
        recommended_schedule_window_minutes=recommended_schedule_window,
        section_rules=formatted_groups
    )

@router.post("/{paper_id}/groups", response_model=StructuredGroupResponse)
async def add_group(
    paper_id: int,
    group_in: StructuredGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    paper = await get_paper_or_404(paper_id, db, current_user, check_mutable=True)
    
    group = ExamSectionRule(
        question_paper_id=paper.id,
        section_index=group_in.section_index,
        section_name=group_in.section_name,
        section_type=group_in.section_type,
        section_duration_minutes=group_in.section_duration_minutes,
        navigation_policy=group_in.navigation_policy,
        allow_return_to_previous=group_in.allow_return_to_previous,
        lock_after_timeout=group_in.lock_after_timeout,
        randomize_questions=group_in.randomize_questions,
        require_completion_before_next=group_in.require_completion_before_next,
        section_weight=group_in.section_weight,
        instructions=group_in.instructions
    )
    db.add(group)
    
    # bump version
    paper.version += 1
    await db.commit()
    await db.refresh(group)
    
    return StructuredGroupResponse(
        id=group.id,
        question_paper_id=group.question_paper_id,
        section_index=group.section_index,
        section_name=group.section_name,
        section_type=group.section_type,
        section_duration_minutes=group.section_duration_minutes,
        navigation_policy=group.navigation_policy,
        allow_return_to_previous=group.allow_return_to_previous,
        lock_after_timeout=group.lock_after_timeout,
        randomize_questions=group.randomize_questions,
        require_completion_before_next=group.require_completion_before_next,
        section_weight=group.section_weight,
        instructions=group.instructions,
        question_rules=[]
    )

@router.post("/{paper_id}/groups/{group_id}/questions", response_model=StructuredQuestionResponse)
async def add_question(
    paper_id: int,
    group_id: int,
    question_in: StructuredQuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    paper = await get_paper_or_404(paper_id, db, current_user, check_mutable=True)
    
    # verify group belongs to paper
    group = await db.get(ExamSectionRule, group_id)
    if not group or group.question_paper_id != paper.id:
        raise HTTPException(status_code=404, detail="Group not found or unauthorized")
        
    question = ExamQuestionRule(
        question_paper_id=paper.id,
        section_rule_id=group.id,
        question_index=question_in.question_index,
        question_type=question_in.question_type,
        marks=question_in.marks,
        is_required=question_in.is_required,
        question_text=question_in.question_text,
        image_url=question_in.image_url,
        explanation=question_in.explanation,
        difficulty=question_in.difficulty
    )
    db.add(question)
    await db.flush()
    
    options_list = []
    if question_in.options:
        for opt_in in question_in.options:
            opt = QuestionOption(
                question_rule_id=question.id,
                option_text=opt_in.option_text,
                is_correct=opt_in.is_correct
            )
            db.add(opt)
            options_list.append(opt)
            
    # bump version
    paper.version += 1
    await db.commit()
    await db.refresh(question)
    
    return StructuredQuestionResponse(
        id=question.id,
        section_rule_id=question.section_rule_id,
        question_index=question.question_index,
        question_type=question.question_type,
        marks=question.marks,
        is_required=question.is_required,
        question_text=question.question_text,
        image_url=question.image_url,
        explanation=question.explanation,
        difficulty=question.difficulty,
        options=[
            QuestionOptionResponse(
                id=opt.id,
                question_rule_id=opt.question_rule_id,
                option_text=opt.option_text,
                is_correct=opt.is_correct
            )
            for opt in options_list
        ]
    )

@router.put("/{paper_id}/groups/{group_id}", response_model=StructuredGroupResponse)
async def update_group(
    paper_id: int,
    group_id: int,
    group_in: StructuredGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    paper = await get_paper_or_404(paper_id, db, current_user, check_mutable=True)
    
    group = await db.get(ExamSectionRule, group_id)
    if not group or group.question_paper_id != paper.id:
        raise HTTPException(status_code=404, detail="Group not found")
        
    group.section_name = group_in.section_name
    group.section_type = group_in.section_type
    group.section_duration_minutes = group_in.section_duration_minutes
    group.navigation_policy = group_in.navigation_policy
    group.allow_return_to_previous = group_in.allow_return_to_previous
    group.lock_after_timeout = group_in.lock_after_timeout
    group.randomize_questions = group_in.randomize_questions
    group.require_completion_before_next = group_in.require_completion_before_next
    group.section_weight = group_in.section_weight
    group.instructions = group_in.instructions
    
    paper.version += 1
    await db.commit()
    
    result = await db.execute(
        select(ExamSectionRule)
        .options(selectinload(ExamSectionRule.question_rules).selectinload(ExamQuestionRule.options))
        .where(ExamSectionRule.id == group_id)
    )
    return result.scalar_one()

@router.put("/{paper_id}/groups/{group_id}/questions/{question_id}", response_model=StructuredQuestionResponse)
async def update_question(
    paper_id: int,
    group_id: int,
    question_id: int,
    question_in: StructuredQuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    paper = await get_paper_or_404(paper_id, db, current_user, check_mutable=True)
    
    question = await db.execute(
        select(ExamQuestionRule).options(selectinload(ExamQuestionRule.options))
        .where(ExamQuestionRule.id == question_id, ExamQuestionRule.section_rule_id == group_id, ExamQuestionRule.question_paper_id == paper.id)
    )
    q_obj = question.scalar_one_or_none()
    
    if not q_obj:
        raise HTTPException(status_code=404, detail="Question not found")
        
    q_obj.question_text = question_in.question_text
    q_obj.marks = question_in.marks
    q_obj.question_type = question_in.question_type
    q_obj.is_required = question_in.is_required
    q_obj.explanation = question_in.explanation
    q_obj.difficulty = question_in.difficulty
    
    # Update options
    opts_to_delete = list(q_obj.options)
    for opt in opts_to_delete:
        await db.delete(opt)
    await db.flush()
    
    options_list = []
    if question_in.options:
        for opt_in in question_in.options:
            new_opt = QuestionOption(
                question_rule_id=q_obj.id,
                option_text=opt_in.option_text,
                is_correct=opt_in.is_correct
            )
            db.add(new_opt)
            options_list.append(new_opt)
            
    paper.version += 1
    await db.commit()
    await db.refresh(q_obj)
    
    return StructuredQuestionResponse(
        id=q_obj.id,
        section_rule_id=q_obj.section_rule_id,
        question_index=q_obj.question_index,
        question_type=q_obj.question_type,
        marks=q_obj.marks,
        is_required=q_obj.is_required,
        question_text=q_obj.question_text,
        image_url=q_obj.image_url,
        explanation=q_obj.explanation,
        difficulty=q_obj.difficulty,
        options=[
            QuestionOptionResponse(
                id=opt.id,
                question_rule_id=opt.question_rule_id,
                option_text=opt.option_text,
                is_correct=opt.is_correct
            )
            for opt in options_list
        ]
    )

