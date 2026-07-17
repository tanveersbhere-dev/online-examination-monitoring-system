import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services.password_service import PasswordService

@pytest_asyncio.fixture(scope="function")
async def setup_qp_data(db_session: AsyncSession):
    role_repo = RoleRepository(db_session)
    examiner_role = await role_repo.create(name="Examiner")
    student_role = await role_repo.create(name="Student")
    
    user_repo = UserRepository(db_session)
    hashed_pwd = PasswordService.hash("password123")
    
    examiner1 = await user_repo.create(
        role_id=examiner_role.id,
        full_name="Examiner One",
        email="examiner1@qp.com",
        password_hash=hashed_pwd,
        is_active=True
    )
    
    examiner2 = await user_repo.create(
        role_id=examiner_role.id,
        full_name="Examiner Two",
        email="examiner2@qp.com",
        password_hash=hashed_pwd,
        is_active=True
    )
    
    student = await user_repo.create(
        role_id=student_role.id,
        full_name="Student",
        email="student@qp.com",
        password_hash=hashed_pwd,
        is_active=True
    )
    
    return examiner1, examiner2, student

@pytest.mark.asyncio
async def test_question_paper_repository_workflow(client: TestClient, setup_qp_data):
    ex1, ex2, student = setup_qp_data
    
    def get_token(email):
        resp = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
        return resp.json()["access_token"]
        
    h_ex1 = {"Authorization": f"Bearer {get_token(ex1.email)}"}
    h_ex2 = {"Authorization": f"Bearer {get_token(ex2.email)}"}
    h_student = {"Authorization": f"Bearer {get_token(student.email)}"}
    
    # 1. Student cannot upload
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    files = {"file": ("test.pdf", valid_pdf, "application/pdf")}
    data = {"title": "Math 101", "course_name": "Math"}
    resp = client.post("/api/v1/question-papers/", data=data, files=files, headers=h_student)
    assert resp.status_code == 403
    
    # 2. Examiner 1 uploads
    files = {"file": ("test.pdf", valid_pdf, "application/pdf")}
    resp = client.post("/api/v1/question-papers/", data=data, files=files, headers=h_ex1)
    assert resp.status_code == 201
    paper_id = resp.json()["id"]
    
    # 3. Read paper
    resp = client.get(f"/api/v1/question-papers/{paper_id}", headers=h_ex1)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Math 101"
    
    # 4. List papers
    resp = client.get("/api/v1/question-papers/", headers=h_student)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    
    # 5. Examiner 2 cannot update Examiner 1's paper
    update_data = {"title": "Updated Title", "description": "Desc"}
    resp = client.put(f"/api/v1/question-papers/{paper_id}", json=update_data, headers=h_ex2)
    assert resp.status_code == 403
    
    # 6. Examiner 1 updates paper
    resp = client.put(f"/api/v1/question-papers/{paper_id}", json=update_data, headers=h_ex1)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"
    
    # 7. Update file
    new_pdf = b"%PDF-1.4\n%New Content"
    files = {"file": ("new.pdf", new_pdf, "application/pdf")}
    resp = client.put(f"/api/v1/question-papers/{paper_id}/file", files=files, headers=h_ex1)
    assert resp.status_code == 200
    assert resp.json()["revision"] == 2
    
    # 8. Examiner 2 cannot delete
    resp = client.delete(f"/api/v1/question-papers/{paper_id}", headers=h_ex2)
    assert resp.status_code == 403
    
    # 9. Examiner 1 deletes
    resp = client.delete(f"/api/v1/question-papers/{paper_id}", headers=h_ex1)
    assert resp.status_code == 204
    
    # Verify deletion
    resp = client.get(f"/api/v1/question-papers/{paper_id}", headers=h_ex1)
    assert resp.status_code == 404
