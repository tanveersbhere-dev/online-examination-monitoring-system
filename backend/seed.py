import asyncio
import logging
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.session import async_session_factory
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services.password_service import PasswordService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_database() -> None:
    logger.info("Starting database seed...")
    
    async with async_session_factory() as db:
        role_repo = RoleRepository(db)
        user_repo = UserRepository(db)
        
        # 1. Detect whether the Roles table is empty
        role_count = await role_repo.count()
        if role_count == 0:
            logger.info("Roles table is empty. Inserting default roles...")
            roles_to_seed = ["Admin", "Examiner", "Student"]
            for role_name in roles_to_seed:
                await role_repo.create(
                    name=role_name, 
                    description=f"Default {role_name} role"
                )
            logger.info("Default roles created successfully.")
        else:
            logger.info("Roles table is not empty. Skipping roles insertion.")
                
        # 2. Detect whether an administrator already exists
        admin_email = "admin@onlinesystem.com"
        admin_user = await user_repo.get_by_email(admin_email)
        
        if not admin_user:
            logger.info("Default administrator not found. Creating...")
            admin_role = await role_repo.get_by_name("Admin")
            if admin_role:
                hashed_password = PasswordService.hash("Admin@123")
                await user_repo.create(
                    role_id=admin_role.id,
                    full_name="System Administrator",
                    email=admin_email,
                    username="admin",
                    password_hash=hashed_password,
                    is_active=True,
                    account_status="ACTIVE"
                )
                logger.info("Created default administrator.")
            else:
                logger.error("Admin role not found. Cannot create default administrator.")
        else:
            logger.info("Default administrator already exists. Skipping administrator creation.")
            
    logger.info("Database seeding completed.")

if __name__ == "__main__":
    asyncio.run(seed_database())
