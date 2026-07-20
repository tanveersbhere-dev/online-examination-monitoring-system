import asyncio, sys
import os
from datetime import datetime, timezone
sys.path.insert(0, '.')
from app.database.session import async_session_factory
from app.models.otp import OTP
from sqlalchemy import select

async def run():
    async with async_session_factory() as db:
        res = await db.execute(select(OTP).order_by(OTP.created_at.desc()).limit(1))
        otp = res.scalars().first()
        if otp:
            print(otp.otp_code)

if __name__ == "__main__":
    asyncio.run(run())
