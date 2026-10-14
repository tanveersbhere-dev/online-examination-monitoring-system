import pytest
from unittest.mock import patch, AsyncMock
from email.message import EmailMessage
from datetime import datetime

import aiosmtplib
from app.core.config import Settings, settings
from app.services.email_service import EmailService
from app.services.exceptions import EmailDeliveryError

def test_smtp_configuration_loading():
    """Verify that SMTP settings properly load from environment and resolve sender."""
    s1 = Settings(
        _env_file=None,
        SMTP_HOST="smtp.gmail.com",
        SMTP_PORT=587,
        SMTP_USERNAME="authorized@gmail.com",
        SMTP_PASSWORD="sample_app_password_16ch",
        SMTP_FROM="custom_from@onlinesystem.com",
        TESTING=True
    )
    assert s1.SMTP_HOST == "smtp.gmail.com"
    assert s1.SMTP_PORT == 587
    assert s1.SMTP_USERNAME == "authorized@gmail.com"
    assert s1.SMTP_PASSWORD == "sample_app_password_16ch"
    assert s1.SMTP_FROM == "custom_from@onlinesystem.com"

    # Test SMTP_FROM_EMAIL takes precedence
    s2 = Settings(
        _env_file=None,
        SMTP_HOST="smtp.gmail.com",
        SMTP_PORT=587,
        SMTP_USERNAME="authorized@gmail.com",
        SMTP_PASSWORD="sample_app_password_16ch",
        SMTP_FROM="fallback@onlinesystem.com",
        SMTP_FROM_EMAIL="sender_verified@gmail.com",
        TESTING=True
    )
    assert s2.SMTP_FROM == "sender_verified@gmail.com"

    # Test fallback to SMTP_USERNAME when SMTP_FROM is empty
    s3 = Settings(
        _env_file=None,
        SMTP_HOST="smtp.gmail.com",
        SMTP_PORT=587,
        SMTP_USERNAME="authorized@gmail.com",
        SMTP_PASSWORD="sample_app_password_16ch",
        SMTP_FROM="",
        TESTING=True
    )
    assert s3.SMTP_FROM == "authorized@gmail.com"

@pytest.mark.asyncio
async def test_dispatch_smtp_missing_host():
    """Verify error when SMTP_HOST is empty."""
    msg = EmailMessage()
    msg["To"] = "candidate@example.com"
    msg["From"] = "system@example.com"

    original_testing = settings.TESTING
    original_host = settings.SMTP_HOST
    try:
        settings.TESTING = False
        settings.SMTP_HOST = ""
        with pytest.raises(EmailDeliveryError) as exc_info:
            await EmailService._dispatch_smtp(msg, "candidate@example.com")
        assert "SMTP_HOST is not configured" in str(exc_info.value)
    finally:
        settings.TESTING = original_testing
        settings.SMTP_HOST = original_host

@pytest.mark.asyncio
async def test_dispatch_smtp_missing_credentials():
    """Verify clear error when SMTP credentials are not configured."""
    msg = EmailMessage()
    msg["To"] = "candidate@example.com"
    msg["From"] = "system@example.com"

    original_testing = settings.TESTING
    original_user = settings.SMTP_USERNAME
    original_pass = settings.SMTP_PASSWORD
    try:
        settings.TESTING = False
        settings.SMTP_USERNAME = ""
        settings.SMTP_PASSWORD = ""
        with pytest.raises(EmailDeliveryError) as exc_info:
            await EmailService._dispatch_smtp(msg, "candidate@example.com")
        assert "SMTP credentials are not configured" in str(exc_info.value)
    finally:
        settings.TESTING = original_testing
        settings.SMTP_USERNAME = original_user
        settings.SMTP_PASSWORD = original_pass

@pytest.mark.asyncio
async def test_dispatch_smtp_success():
    """Verify that _dispatch_smtp sends email via aiosmtplib.send with STARTTLS."""
    msg = EmailMessage()
    msg["To"] = "student@university.edu"
    msg["From"] = "proctor@gmail.com"
    msg["Subject"] = "Test Subject"
    msg.set_content("Hello World")

    original_testing = settings.TESTING
    original_host = settings.SMTP_HOST
    original_port = settings.SMTP_PORT
    original_user = settings.SMTP_USERNAME
    original_pass = settings.SMTP_PASSWORD

    try:
        settings.TESTING = False
        settings.SMTP_HOST = "smtp.gmail.com"
        settings.SMTP_PORT = 587
        settings.SMTP_USERNAME = "proctor@gmail.com"
        settings.SMTP_PASSWORD = "mock_app_password"

        with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            await EmailService._dispatch_smtp(msg, "student@university.edu")

            mock_send.assert_awaited_once_with(
                msg,
                hostname="smtp.gmail.com",
                port=587,
                username="proctor@gmail.com",
                password="mock_app_password",
                start_tls=True
            )
    finally:
        settings.TESTING = original_testing
        settings.SMTP_HOST = original_host
        settings.SMTP_PORT = original_port
        settings.SMTP_USERNAME = original_user
        settings.SMTP_PASSWORD = original_pass

@pytest.mark.asyncio
async def test_dispatch_smtp_authentication_failure():
    """Verify handling of SMTPAuthenticationError without leaking secret values."""
    msg = EmailMessage()
    msg["To"] = "student@university.edu"
    msg["From"] = "proctor@gmail.com"

    original_testing = settings.TESTING
    original_host = settings.SMTP_HOST
    original_user = settings.SMTP_USERNAME
    original_pass = settings.SMTP_PASSWORD

    secret_val = "super_secret_app_pw"
    try:
        settings.TESTING = False
        settings.SMTP_HOST = "smtp.gmail.com"
        settings.SMTP_USERNAME = "proctor@gmail.com"
        settings.SMTP_PASSWORD = secret_val

        with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = aiosmtplib.SMTPAuthenticationError(535, "5.7.8 Username and Password not accepted")
            with pytest.raises(EmailDeliveryError) as exc_info:
                await EmailService._dispatch_smtp(msg, "student@university.edu")

            error_msg = str(exc_info.value)
            assert "SMTP authentication failed" in error_msg
            assert secret_val not in error_msg
    finally:
        settings.TESTING = original_testing
        settings.SMTP_HOST = original_host
        settings.SMTP_USERNAME = original_user
        settings.SMTP_PASSWORD = original_pass

@pytest.mark.asyncio
async def test_dispatch_smtp_connect_failure():
    """Verify handling of SMTPConnectError without leaking secret values."""
    msg = EmailMessage()
    msg["To"] = "student@university.edu"
    msg["From"] = "proctor@gmail.com"

    original_testing = settings.TESTING
    original_host = settings.SMTP_HOST
    original_user = settings.SMTP_USERNAME
    original_pass = settings.SMTP_PASSWORD

    try:
        settings.TESTING = False
        settings.SMTP_HOST = "smtp.gmail.com"
        settings.SMTP_USERNAME = "proctor@gmail.com"
        settings.SMTP_PASSWORD = "mock_password"

        with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = aiosmtplib.SMTPConnectError("Connection refused")
            with pytest.raises(EmailDeliveryError) as exc_info:
                await EmailService._dispatch_smtp(msg, "student@university.edu")

            assert "SMTP connection failed" in str(exc_info.value)
    finally:
        settings.TESTING = original_testing
        settings.SMTP_HOST = original_host
        settings.SMTP_USERNAME = original_user
        settings.SMTP_PASSWORD = original_pass

@pytest.mark.asyncio
async def test_send_otp_email_in_testing_mode():
    """Verify that send_otp_email skips SMTP delivery when TESTING=True."""
    original_testing = settings.TESTING
    try:
        settings.TESTING = True
        with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            await EmailService.send_otp_email("recipient@example.com", "987654", "REGISTRATION")
            mock_send.assert_not_called()
    finally:
        settings.TESTING = original_testing

@pytest.mark.asyncio
async def test_send_otp_email_active_dispatch():
    """Verify that send_otp_email dispatches OTP to recipients different from sender."""
    original_testing = settings.TESTING
    original_user = settings.SMTP_USERNAME
    original_pass = settings.SMTP_PASSWORD
    original_from = settings.SMTP_FROM

    try:
        settings.TESTING = False
        settings.SMTP_USERNAME = "authorized_sender@gmail.com"
        settings.SMTP_PASSWORD = "mock_app_password"
        settings.SMTP_FROM = "authorized_sender@gmail.com"

        with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            # Recipient is a student with a different email domain
            await EmailService.send_otp_email("external_student@student.edu", "654321", "PASSWORD_RESET")

            mock_send.assert_awaited_once()
            call_args = mock_send.await_args[0]
            sent_message = call_args[0]
            assert sent_message["To"] == "external_student@student.edu"
            assert sent_message["From"] == "authorized_sender@gmail.com"
            assert "Password Reset Verification Code" in sent_message["Subject"]
            assert "654321" in sent_message.get_payload()[1].get_payload()
    finally:
        settings.TESTING = original_testing
        settings.SMTP_USERNAME = original_user
        settings.SMTP_PASSWORD = original_pass
        settings.SMTP_FROM = original_from

@pytest.mark.asyncio
async def test_send_registration_email_active_dispatch():
    """Verify send_registration_email dispatches correctly."""
    original_testing = settings.TESTING
    original_user = settings.SMTP_USERNAME
    original_pass = settings.SMTP_PASSWORD
    original_from = settings.SMTP_FROM

    try:
        settings.TESTING = False
        settings.SMTP_USERNAME = "authorized_sender@gmail.com"
        settings.SMTP_PASSWORD = "mock_app_password"
        settings.SMTP_FROM = "authorized_sender@gmail.com"

        with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            await EmailService.send_registration_email(
                recipient_email="student@univ.edu",
                student_name="Alice Smith",
                exam_name="Computer Vision Final",
                password_plain="TempPass123!",
                exam_date=datetime(2026, 11, 1, 9, 0),
                expiry_date=None
            )

            mock_send.assert_awaited_once()
            call_args = mock_send.await_args[0]
            sent_message = call_args[0]
            assert sent_message["To"] == "student@univ.edu"
            assert "Online Examination Credentials" in sent_message["Subject"]
    finally:
        settings.TESTING = original_testing
        settings.SMTP_USERNAME = original_user
        settings.SMTP_PASSWORD = original_pass
        settings.SMTP_FROM = original_from

