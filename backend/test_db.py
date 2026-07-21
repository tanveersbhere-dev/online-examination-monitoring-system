import asyncio
from app.database.session import async_session_factory
from app.models.user import User
from app.models.role import Role
from sqlalchemy.future import select

async def run():
    async with async_session_factory() as s:
        res = await s.execute(select(Role))
        roles = res.scalars().all()
        for r in roles:
            print(f'Role: id={r.id}, name={r.name}')
            
        res2 = await s.execute(select(User))
        users = res2.scalars().all()
        for u in users:
            print(f'User: email={u.email}, role_id={u.role_id}')

asyncio.run(run())
