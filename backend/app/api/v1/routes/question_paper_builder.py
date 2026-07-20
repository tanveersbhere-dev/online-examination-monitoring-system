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

async def get_paper_or_404(paper_id: int, db: AsyncSession, user_id: int) -> QuestionPaper:
    query = select(QuestionPaper).options(
        selectinload(QuestionPaper.section_rules).selectinload(ExamSectionRule.question_rules).selectinload(ExamQuestionRule.options)
    ).where(QuestionPaper.id == paper_id)
    
    result = await db.execute(query)
    paper = result.scalar_one_or_none()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Question Paper not found")
        
    if paper.uploaded_by != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    if paper.mode != "STRUCTURED":
        raise HTTPException(status_code=400, detail="Not a STRUCTURED mode Question Paper")
        
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
    paper = await get_paper_or_404(paper_id, db, current_user.id)
    return paper

@router.post("/{paper_id}/groups", response_model=StructuredGroupResponse)
async def add_group(
    paper_id: int,
    group_in: StructuredGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    paper = await get_paper_or_404(paper_id, db, current_user.id)
    
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
    return group

@router.post("/{paper_id}/groups/{group_id}/questions", response_model=StructuredQuestionResponse)
async def add_question(
    paper_id: int,
    group_id: int,
    question_in: StructuredQuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    paper = await get_paper_or_404(paper_id, db, current_user.id)
    
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
    
    if question_in.options:
        for opt_in in question_in.options:
            opt = QuestionOption(
                question_rule=question, # link via relationship
                option_text=opt_in.option_text,
                is_correct=opt_in.is_correct
            )
            db.add(opt)
            
    # bump version
    paper.version += 1
    await db.commit()
    await db.refresh(question)
    
    # reload question with options
    q = await db.execute(select(ExamQuestionRule).options(selectinload(ExamQuestionRule.options)).where(ExamQuestionRule.id == question.id))
    return q.scalar_one()

@router.put("/{paper_id}/groups/{group_id}", response_model=StructuredGroupResponse)
async def update_group(
    paper_id: int,
    group_id: int,
    group_in: StructuredGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    paper = await get_paper_or_404(paper_id, db, current_user.id)
    
    group = await db.get(ExamSectionRule, group_id)
    if not group or group.question_paper_id != paper.id:
        raise HTTPException(status_code=404, detail="Group not found")
        
    group.section_name = group_in.section_name
    
    paper.version += 1
    await db.commit()
    await db.refresh(group)
    return group

@router.put("/{paper_id}/groups/{group_id}/questions/{question_id}", response_model=StructuredQuestionResponse)
async def update_question(
    paper_id: int,
    group_id: int,
    question_id: int,
    question_in: StructuredQuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    paper = await get_paper_or_404(paper_id, db, current_user.id)
    
    question = await db.execute(
        select(ExamQuestionRule).options(selectinload(ExamQuestionRule.options))
        .where(ExamQuestionRule.id == question_id, ExamQuestionRule.section_rule_id == group_id, ExamQuestionRule.question_paper_id == paper.id)
    )
    q_obj = question.scalar_one_or_none()
    
    if not q_obj:
        raise HTTPException(status_code=404, detail="Question not found")
        
    q_obj.question_text = question_in.question_text
    q_obj.marks = question_in.marks
    
    # Update options
    # Simplest approach for options: delete all and recreate
    await db.execute(select(QuestionOption).where(QuestionOption.question_rule_id == q_obj.id))
    for opt in q_obj.options:
        await db.delete(opt)
    await db.flush()
    
    if question_in.options:
        for opt_in in question_in.options:
            new_opt = QuestionOption(
                question_rule_id=q_obj.id,
                option_text=opt_in.option_text,
                is_correct=opt_in.is_correct
            )
            db.add(new_opt)
            
    paper.version += 1
    await db.commit()
    await db.refresh(q_obj)
    
    reloaded = await db.execute(select(ExamQuestionRule).options(selectinload(ExamQuestionRule.options)).where(ExamQuestionRule.id == q_obj.id))
    return reloaded.scalar_one()

