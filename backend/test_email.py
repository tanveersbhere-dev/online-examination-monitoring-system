import asyncio
from datetime import datetime
from app.services.email_service import EmailService

async def main():
    print("Testing Email Delivery...")
    try:
        await EmailService.send_registration_email(
            recipient_email="test_student@example.com",
            student_name="Test Student",
            exam_name="Final Exam",
            username="STU-2026-0000",
            password_plain="TestPass123!",
            exam_date=datetime.utcnow(),
            expiry_date=None
        )
        print("SUCCESS")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(main())
