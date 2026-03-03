"""
Admin Service - manages bot administrators.
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import Admin

OWNER_ID = 747102879  # Owner telegram ID


class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def is_owner(self, telegram_id: int) -> bool:
        """Check if user is the owner"""
        return telegram_id == OWNER_ID
    
    async def is_admin(self, telegram_id: int) -> bool:
        """Check if user is an admin"""
        result = await self.session.execute(
            select(Admin).where(Admin.telegram_id == telegram_id)
        )
        admin = result.scalar_one_or_none()
        return admin is not None
    
    async def is_admin_or_owner(self, telegram_id: int) -> bool:
        """Check if user is admin or owner"""
        if self.is_owner(telegram_id):
            return True
        return await self.is_admin(telegram_id)
    
    async def add_admin(self, telegram_id: int, added_by: int) -> Admin:
        """Add a new admin"""
        # Check if already admin
        existing = await self.session.execute(
            select(Admin).where(Admin.telegram_id == telegram_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("User is already an admin")
        
        admin = Admin(telegram_id=telegram_id, added_by=added_by)
        self.session.add(admin)
        await self.session.flush()
        return admin
    
    async def remove_admin(self, telegram_id: int):
        """Remove an admin"""
        result = await self.session.execute(
            select(Admin).where(Admin.telegram_id == telegram_id)
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            raise ValueError("User is not an admin")
        
        await self.session.delete(admin)
        await self.session.flush()
    
    async def list_admins(self) -> List[Admin]:
        """Get all admins"""
        result = await self.session.execute(select(Admin))
        return list(result.scalars().all())
