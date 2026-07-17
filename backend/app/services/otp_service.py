import random
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.otp import OTP
from app.services.exceptions import AuthorizationError

logger = logging.getLogger(__name__)

class OTPService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.OTP_EXPIRY_MINUTES = 10
        self.MAX_FAILED_ATTEMPTS = 3
        self.MAX_RESENDS = 3

    async def generate_otp(self, user_id: int, purpose: str, new_email: str = None) -> str:
        # Check if user has exceeded resend limits recently
        # For simplicity, we just count active OTPs generated in the last hour
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        query = select(OTP).where(
            OTP.user_id == user_id,
            OTP.purpose == purpose,
            OTP.created_at >= one_hour_ago
        )
        result = await self.db.execute(query)
        recent_otps = result.scalars().all()
        
        if len(recent_otps) >= self.MAX_RESENDS:
            raise AuthorizationError("Maximum OTP request limit reached. Please try again later.")

        # Invalidate previous unexpired OTPs for this purpose
        invalidate_query = select(OTP).where(
            OTP.user_id == user_id,
            OTP.purpose == purpose,
            OTP.is_used == False,
            OTP.expires_at > datetime.now(timezone.utc)
        )
        result = await self.db.execute(invalidate_query)
        old_otps = result.scalars().all()
        for old_otp in old_otps:
            old_otp.is_used = True # Mark as used/invalidated
            
        # Generate new OTP
        otp_code = str(random.randint(100000, 999999))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.OTP_EXPIRY_MINUTES)
        
        new_otp = OTP(
            user_id=user_id,
            otp_code=otp_code,
            purpose=purpose,
            expires_at=expires_at,
            new_email=new_email
        )
        self.db.add(new_otp)
        await self.db.commit()
        return otp_code

    async def verify_otp(self, user_id: int, purpose: str, otp_code: str) -> OTP:
        query = select(OTP).where(
            OTP.user_id == user_id,
            OTP.purpose == purpose,
            OTP.is_used == False
        ).order_by(OTP.created_at.desc()).limit(1)
        
        result = await self.db.execute(query)
        otp_record = result.scalars().first()

        if not otp_record:
            raise AuthorizationError("No active OTP found. Please request a new one.")

        if otp_record.failed_attempts >= self.MAX_FAILED_ATTEMPTS:
            otp_record.is_used = True
            await self.db.commit()
            raise AuthorizationError("Maximum OTP verification attempts reached. Please request a new one.")

        # If using naive datetime, handle appropriately. Since we used timezone=True in models
        now = datetime.now(timezone.utc)
        # Check if expires_at is naive and add tzinfo if needed
        expires_at = otp_record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            
        if expires_at < now:
            otp_record.is_used = True
            await self.db.commit()
            raise AuthorizationError("OTP has expired. Please request a new one.")

        if otp_record.otp_code != otp_code:
            otp_record.failed_attempts += 1
            await self.db.commit()
            raise AuthorizationError("Invalid OTP code.")

        # Success
        otp_record.is_used = True
        await self.db.commit()
        return otp_record
