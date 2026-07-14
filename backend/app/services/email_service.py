import aiosmtplib
import logging
from email.message import EmailMessage
from typing import Optional
from datetime import datetime

from app.core.config import settings
from app.services.exceptions import EmailDeliveryError

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    async def send_registration_email(
        recipient_email: str,
        student_name: str,
        exam_name: str,
        username: str,
        password_plain: str,
        exam_date: datetime,
        expiry_date: Optional[datetime]
    ):
        if settings.TESTING:
            logger.info("TESTING mode: Skipping actual SMTP delivery.")
            return

        subject = "Online Examination Credentials"
        
        expiry_str = expiry_date.strftime('%Y-%m-%d %H:%M:%S UTC') if expiry_date else "Never"
        exam_date_str = exam_date.strftime('%Y-%m-%d %H:%M:%S UTC')
        
        html_body = f"""
        <html>
            <body>
                <p>Dear {student_name},</p>
                <p>You have been successfully registered for the examination.</p>
                <p><strong>Exam:</strong> {exam_name}</p>
                <p><strong>Username:</strong> {username}</p>
                <p><strong>Password:</strong> {password_plain}</p>
                <p><strong>Exam Date:</strong> {exam_date_str}</p>
                <p><strong>Credential Expiry:</strong> {expiry_str}</p>
                <br>
                <p>Please keep these credentials secure.</p>
                <p>Regards,<br>Online Examination System</p>
            </body>
        </html>
        """

        message = EmailMessage()
        message["From"] = settings.SMTP_FROM
        message["To"] = recipient_email
        message["Subject"] = subject
        message.set_content("Please enable HTML to view this message.")
        message.add_alternative(html_body, subtype="html")

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                start_tls=True
            )
            logger.info(f"Credentials emailed to {recipient_email}")
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}")
            raise EmailDeliveryError("SMTP dispatch failed.") from e
