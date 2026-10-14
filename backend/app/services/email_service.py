import aiosmtplib
import logging
from email.message import EmailMessage
from typing import Optional
from datetime import datetime

from app.core.config import settings
from app.services.exceptions import EmailDeliveryError
from app.utils.timezone import to_presentation_tz

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    async def _dispatch_smtp(message: EmailMessage, recipient_email: str):
        if settings.TESTING:
            logger.info(f"TESTING mode: Skipping actual SMTP delivery to {recipient_email}.")
            return

        if not settings.SMTP_HOST or not settings.SMTP_HOST.strip():
            logger.error("SMTP configuration error: SMTP_HOST is not configured.")
            raise EmailDeliveryError("Email delivery failed: SMTP_HOST is not configured.")

        if not settings.SMTP_USERNAME or not settings.SMTP_USERNAME.strip() or not settings.SMTP_PASSWORD or not settings.SMTP_PASSWORD.strip():
            logger.error(f"SMTP configuration error: SMTP_USERNAME or SMTP_PASSWORD is not configured. Cannot dispatch email to {recipient_email}.")
            raise EmailDeliveryError("Email delivery failed: SMTP credentials are not configured.")

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                start_tls=True
            )
            logger.info(f"Email successfully delivered to {recipient_email}")
        except aiosmtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed when sending email to {recipient_email}. Please check SMTP credentials.")
            raise EmailDeliveryError("SMTP authentication failed. Please verify SMTP_USERNAME and SMTP_PASSWORD.") from e
        except aiosmtplib.SMTPConnectError as e:
            logger.error(f"SMTP connection failed to server at {settings.SMTP_HOST}:{settings.SMTP_PORT}.")
            raise EmailDeliveryError(f"SMTP connection failed to server at {settings.SMTP_HOST}:{settings.SMTP_PORT}.") from e
        except aiosmtplib.SMTPException as e:
            logger.error(f"SMTP protocol error dispatching to {recipient_email}: {type(e).__name__}")
            raise EmailDeliveryError("SMTP dispatch failed.") from e
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {type(e).__name__}")
            raise EmailDeliveryError("Email delivery failed due to an unexpected error.") from e

    @staticmethod
    async def send_registration_email(
        recipient_email: str,
        student_name: str,
        exam_name: str,
        password_plain: str,
        exam_date: datetime,
        expiry_date: Optional[datetime]
    ):
        subject = "Online Examination Credentials"
        
        expiry_str = to_presentation_tz(expiry_date).strftime(f'%Y-%m-%d %H:%M:%S {settings.APP_TIMEZONE}') if expiry_date else "Never"
        exam_date_str = to_presentation_tz(exam_date).strftime(f'%Y-%m-%d %H:%M:%S {settings.APP_TIMEZONE}')
        
        html_body = f"""
        <html>
            <body>
                <p>Dear {student_name},</p>
                <p>You have been successfully registered for the examination.</p>
                <p><strong>Exam:</strong> {exam_name}</p>
                <p><strong>Email Address:</strong> {recipient_email}</p>
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

        await EmailService._dispatch_smtp(message, recipient_email)

    @staticmethod
    async def send_otp_email(recipient_email: str, otp_code: str, purpose: str):
        if settings.TESTING:
            logger.info(f"TESTING mode: Skipping actual SMTP delivery for OTP. Code: {otp_code}, Purpose: {purpose}")
            return

        subject = "Your Verification Code"
        if purpose == "PASSWORD_RESET":
            subject = "Password Reset Verification Code"
        elif purpose == "REGISTRATION":
            subject = "Account Verification Code"
        elif purpose == "EMAIL_CHANGE":
            subject = "Email Change Verification Code"

        html_body = f"""
        <html>
            <body>
                <p>Hello,</p>
                <p>Your verification code is: <strong>{otp_code}</strong></p>
                <p>This code will expire in 10 minutes.</p>
                <p>If you did not request this, please ignore this email.</p>
                <br>
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

        await EmailService._dispatch_smtp(message, recipient_email)

    @staticmethod
    async def send_account_provisioning_email(
        recipient_email: str,
        student_name: str,
        password_plain: str,
        login_url: str = None
    ):
        """Sent ONCE when a student's login account is provisioned."""
        if not login_url:
            login_url = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')}/student/login"

        subject = "Your Online Examination Student Account Credentials"
        html_body = f"""
        <html>
            <body>
                <p>Dear {student_name},</p>
                <p>Your student login account has been provisioned for the Online Examination System.</p>
                <p><strong>Email Address:</strong> {recipient_email}</p>
                <p><strong>Temporary Password:</strong> {password_plain}</p>
                <p><strong>Login Portal URL:</strong> <a href="{login_url}">{login_url}</a></p>
                <br>
                <p><strong>Instructions:</strong></p>
                <ul>
                    <li>Please keep your login credentials confidential.</li>
                    <li>Log in to view scheduled examinations.</li>
                    <li>If an examination requires identity verification, make sure your face is visible on camera during the attempt.</li>
                </ul>
                <br>
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

        await EmailService._dispatch_smtp(message, recipient_email)

    @staticmethod
    async def send_exam_notification_email(
        recipient_email: str,
        student_name: str,
        exam_name: str,
        scheduled_start: Optional[datetime],
        duration_minutes: Optional[int],
        instructions: Optional[str] = None
    ):
        """Sent whenever a student is assigned to an exam. Does NOT include credentials."""
        start_dt = to_presentation_tz(scheduled_start) if scheduled_start else None
        start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S PKT') if start_dt else "TBD"
        duration_str = f"{duration_minutes} minutes" if duration_minutes else "N/A"

        subject = f"New Examination Assignment: {exam_name}"
        html_body = f"""
        <html>
            <body>
                <p>Dear {student_name},</p>
                <p>You have been assigned to a new examination.</p>
                <p><strong>Examination:</strong> {exam_name}</p>
                <p><strong>Scheduled Start:</strong> {start_str}</p>
                <p><strong>Duration:</strong> {duration_str}</p>
                {f'<p><strong>Instructions:</strong> {instructions}</p>' if instructions else ''}
                <br>
                <p>Please log in to your student dashboard at the scheduled time to take the examination.</p>
                <br>
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

        await EmailService._dispatch_smtp(message, recipient_email)

