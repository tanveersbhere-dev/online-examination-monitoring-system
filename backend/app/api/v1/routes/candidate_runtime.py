from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.security.dependencies import get_current_user
from app.schemas.user_auth import UserResponse
from app.services.exam_session_service import ExamSessionService
from app.repositories.exceptions import EntityNotFoundError

from pydantic import BaseModel
import base64
import cv2
import numpy as np
import time
import json
import logging
from ai_engine.camera.frame import Frame
from app.services.ai_session_manager import AISessionManager
from ai_engine.features.face_identity.embedding_processor import EmbeddingIdentityProcessor
from ai_engine.features.face_identity.models import FaceIdentityConfig

router = APIRouter()

class IdentityVerificationRequest(BaseModel):
    exam_id: int
    image_base64: str

class FrameIngestRequest(BaseModel):
    image_base64: str

@router.post("/verify-identity")
async def verify_identity(
    request: IdentityVerificationRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify candidate identity against enrolled face embedding."""
    try:
        header, encoded = request.image_base64.split(",", 1) if "," in request.image_base64 else ("", request.image_base64)
        image_bytes = base64.b64decode(encoded)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image data")
            
        from app.repositories.user_repository import UserRepository
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(current_user.id)
        if not user or not user.face_embedding:
            raise HTTPException(status_code=400, detail="No enrolled face found for this user.")
            
        reference_embedding = json.loads(user.face_embedding)
        
        config = FaceIdentityConfig(embedding_model_name="buffalo_l")
        processor = EmbeddingIdentityProcessor(config)
        processor.initialize()
        
        current_embedding = processor._extract_embedding(img, bbox=None)
        if not current_embedding:
            raise HTTPException(status_code=400, detail="No face detected in the frame.")
            
        from numpy.linalg import norm
        ref = np.array(reference_embedding)
        curr = np.array(current_embedding)
        similarity = np.dot(ref, curr) / (norm(ref) * norm(curr))
        
        verified = bool(similarity >= config.similarity_threshold)
        return {"verified": verified, "confidence": float(similarity)}
    except Exception as e:
        logging.error(f"Identity verification failed: {e}")
        raise HTTPException(status_code=500, detail="Identity verification failed")

@router.post("/frame")
async def ingest_frame(
    exam_id: int,
    request: FrameIngestRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Ingest WebRTC frame from candidate browser and push to AIEngineThread."""
    try:
        service = ExamSessionService(db)
        session = await service.enforce_active_runtime(exam_id, current_user.id)
        
        header, encoded = request.image_base64.split(",", 1) if "," in request.image_base64 else ("", request.image_base64)
        image_bytes = base64.b64decode(encoded)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if img is not None:
            thread = AISessionManager._active_threads.get(session.id)
            if thread and thread.context:
                frame = Frame(original_frame=img, timestamp=time.time())
                thread.context.current_frame = frame
                
        return {"status": "accepted"}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logging.error(f"Frame ingestion failed: {e}")
        return {"status": "error"}

@router.post("/start", response_model=Dict[str, Any])
async def start_runtime_session(
    exam_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize or resume an exam runtime session.
    """
    try:
        service = ExamSessionService(db)
        result = await service.start_runtime_session(exam_id, current_user.id)
        

        
        return result
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

import os
from fastapi.responses import FileResponse

@router.get("/file")
async def get_runtime_file(
    exam_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Securely serve the FILE mode question paper for the active session."""
    service = ExamSessionService(db)
    session = await service.session_repo.get_by_student_and_exam(current_user.id, exam_id)
    if not session or session.status != "RUNNING":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active running session found.")
        
    exam = await service.exam_repo.get_by_id(exam_id)
    if not exam or not exam.question_paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question paper not found.")
        
    if exam.question_paper.mode != "FILE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam is not in FILE mode.")
        
    file_path = exam.question_paper.file_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File physically missing on server.")
        
    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type=exam.question_paper.mime_type or "application/pdf",
        headers={"Content-Disposition": f'inline; filename="{os.path.basename(file_path)}"'}
    )

@router.post("/heartbeat", status_code=status.HTTP_200_OK)
async def runtime_heartbeat(
    exam_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Heartbeat to keep session alive and sync state.
    """
    # Just verify session is active, no heavy writes to avoid DB locks
    service = ExamSessionService(db)
    existing = await service.session_repo.get_by_student_and_exam(current_user.id, exam_id)
    if not existing or existing.status != "RUNNING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No running session found.")
    return {"status": "ok"}


@router.post("/submit", status_code=status.HTTP_200_OK)
async def submit_runtime_session(
    exam_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit and conclude the exam session.
    """
    try:
        service = ExamSessionService(db)
        session_obj = await service.submit_runtime_session(exam_id, current_user.id)
        return {"detail": "Exam submitted successfully", "session_id": session_obj.id}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


from app.schemas.runtime_state import RuntimeStateResponse

@router.get("/state", response_model=RuntimeStateResponse)
async def get_runtime_state(
    exam_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current runtime state for the active session"""
    try:
        service = ExamSessionService(db)
        session = await service.enforce_active_runtime(exam_id, current_user.id)
            
        from app.services.runtime_state_service import RuntimeStateService
        state_service = RuntimeStateService(db)
        return await state_service.get_state(session.id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.put("/state/position", response_model=RuntimeStateResponse)
async def update_runtime_position(
    exam_id: int,
    section_index: int,
    question_index: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current execution position in the runtime state"""
    try:
        service = ExamSessionService(db)
        session = await service.enforce_active_runtime(exam_id, current_user.id)
            
        from app.services.runtime_state_service import RuntimeStateService
        state_service = RuntimeStateService(db)
        return await state_service.update_position(session.id, section_index, question_index)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


from app.schemas.candidate_answer import CandidateAnswerResponse, CandidateAnswerUpdate
from typing import List

@router.get("/answers", response_model=List[CandidateAnswerResponse])
async def get_candidate_answers(
    exam_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all saved answers for the active exam session."""
    try:
        service = ExamSessionService(db)
        session = await service.enforce_active_runtime(exam_id, current_user.id)
            
        from app.services.candidate_answer_service import CandidateAnswerService
        ans_service = CandidateAnswerService(db)
        return await ans_service.get_session_answers(session.id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.post("/answers/{section_index}/{question_index}", response_model=CandidateAnswerResponse)
async def save_candidate_answer(
    exam_id: int,
    section_index: int,
    question_index: int,
    answer_in: CandidateAnswerUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Save or update a candidate's answer for a specific question."""
    try:
        service = ExamSessionService(db)
        session = await service.enforce_active_runtime(exam_id, current_user.id)
            
        from app.services.candidate_answer_service import CandidateAnswerService
        ans_service = CandidateAnswerService(db)
        return await ans_service.save_answer(session.id, section_index, question_index, answer_in)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
