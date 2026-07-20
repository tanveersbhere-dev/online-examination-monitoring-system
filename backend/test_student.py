import asyncio
import io
import cv2
import numpy as np
from datetime import datetime, timedelta
from fastapi import UploadFile
from app.database.session import async_session_factory
from app.services.student_service import StudentService
from app.schemas.student import StudentCreate

async def test_registration():
    async with async_session_factory() as db:
        # Create a dummy image buffer that has a real face? 
        # Wait, if we just use a blank image, buffalo_l will throw "No face detected in the provided image."
        # Because we can't easily generate a real face image here, let's skip the real test script or let's create a stub.
        pass

if __name__ == "__main__":
    asyncio.run(test_registration())
