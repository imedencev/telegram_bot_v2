"""
Settings Service - manages bot configuration settings.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import Settings


class SettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value by key"""
        result = await self.session.execute(
            select(Settings).where(Settings.key == key)
        )
        setting = result.scalar_one_or_none()
        return setting.value if setting else None
    
    async def set_setting(self, key: str, value: str):
        """Set a setting value (create or update)"""
        result = await self.session.execute(
            select(Settings).where(Settings.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if setting:
            setting.value = value
        else:
            setting = Settings(key=key, value=value)
            self.session.add(setting)
        
        await self.session.flush()
    
    async def delete_setting(self, key: str):
        """Delete a setting"""
        result = await self.session.execute(
            select(Settings).where(Settings.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if setting:
            await self.session.delete(setting)
            await self.session.flush()
