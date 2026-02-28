"""
User Service - manages user data and privacy consent (152-ФЗ compliance).
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import User


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_or_create_user(self, telegram_id: int, full_name: Optional[str] = None) -> User:
        """Get existing user or create new one"""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                telegram_id=telegram_id,
                full_name=full_name
            )
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
        
        return user
    
    async def has_consent(self, telegram_id: int) -> bool:
        """Check if user has given privacy consent"""
        user = await self.get_or_create_user(telegram_id)
        return user.consent_date is not None and user.consent_revoked_at is None
    
    async def give_consent(self, telegram_id: int):
        """Record user consent"""
        user = await self.get_or_create_user(telegram_id)
        user.consent_date = datetime.now()
        user.consent_revoked_at = None
        await self.session.commit()
    
    async def revoke_consent(self, telegram_id: int):
        """Revoke user consent"""
        user = await self.get_or_create_user(telegram_id)
        user.consent_revoked_at = datetime.now()
        await self.session.commit()
    
    @staticmethod
    def get_privacy_policy_text() -> str:
        """Get privacy policy text (152-ФЗ)"""
        return (
            "Политика конфиденциальности\n\n"
            "Мы собираем и обрабатываем ваши персональные данные "
            "(имя, телефон, данные заказа) для выполнения заказа.\n\n"
            "Ваши данные:\n"
            "• Используются только для обработки заказа\n"
            "• Не передаются третьим лицам\n"
            "• Хранятся в защищенной базе данных\n\n"
            "Вы можете отозвать согласие командой /revoke_consent\n\n"
            "Продолжая, вы соглашаетесь на обработку персональных данных "
            "в соответствии с 152-ФЗ."
        )
