import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from app.database.base import Base
from app.models.role import Role
from app.models.user import User
from app.repositories.exceptions import EntityNotFoundError, TransactionError
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository

# Use an in-memory SQLite database for testing, adapted for async driver aiosqlite
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with TestingSessionLocal() as session:
        yield session
        
    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_crud_operations(db_session: AsyncSession):
    repo = RoleRepository(db_session)
    
    # Test Create
    role = await repo.create(name="ADMIN", description="Administrator")
    assert role.id is not None
    assert role.name == "ADMIN"
    
    # Test Read (get_by_id)
    fetched = await repo.get_by_id(role.id)
    assert fetched is not None
    assert fetched.name == "ADMIN"
    
    # Test Exists
    exists = await repo.exists(role.id)
    assert exists is True
    
    # Test Update
    updated = await repo.update(fetched, description="Updated description")
    assert updated.description == "Updated description"
    
    # Test Count and Get All
    await repo.create(name="STUDENT", description="Student")
    count = await repo.count()
    assert count == 2
    
    all_roles = await repo.get_all()
    assert len(all_roles) == 2
    
    # Test Delete
    result = await repo.delete(role.id)
    assert result is True
    assert await repo.exists(role.id) is False
    
    # Test Delete Non-existent
    with pytest.raises(EntityNotFoundError):
        await repo.delete(999)

@pytest.mark.asyncio
async def test_user_repository_filtering(db_session: AsyncSession):
    role_repo = RoleRepository(db_session)
    user_repo = UserRepository(db_session)
    
    role = await role_repo.create(name="TEACHER")
    
    # Create user
    user = await user_repo.create(
        role_id=role.id,
        full_name="John",
        email="john@example.com",
        password_hash="hash",
        is_active=True
    )
    
    # Test specific filter
    fetched = await user_repo.get_by_email("john@example.com")
    assert fetched is not None
    assert fetched.full_name == "John"
    
    # Test active filter
    active = await user_repo.get_active_users()
    assert len(active) == 1
    
    # Deactivate
    await user_repo.update(user, is_active=False)
    active2 = await user_repo.get_active_users()
    assert len(active2) == 0

@pytest.mark.asyncio
async def test_transaction_rollback(db_session: AsyncSession):
    role_repo = RoleRepository(db_session)
    await role_repo.create(name="UNIQUE")
    
    # Attempting to create duplicate unique constraint should rollback
    with pytest.raises(TransactionError):
        await role_repo.create(name="UNIQUE")
        
    # Verify session is still valid by creating something else
    new_role = await role_repo.create(name="OTHER")
    assert new_role.id is not None
