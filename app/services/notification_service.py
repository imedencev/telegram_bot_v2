"""
Notification Service - notifies staff about new orders.
"""
import os
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import Order, User
from app.services.calendar_export import generate_ics_content, get_ics_filename
from app.services.settings_service import SettingsService
from aiogram.types import BufferedInputFile


class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.staff_ids = [int(id.strip()) for id in os.getenv("STAFF_IDS", "").split(",") if id.strip()]
    
    async def notify_new_order(self, order: Order, session: AsyncSession):
        """Send notification to staff about new order"""
        settings_service = SettingsService(session)
        notification_group_id = await settings_service.get_setting("notification_group_id")
        
        # Get customer name
        result = await session.execute(
            select(User).where(User.telegram_id == order.customer_telegram_id)
        )
        user = result.scalar_one_or_none()
        customer_name = user.full_name if user and user.full_name else None
        
        message = self._format_order_message(order, customer_name)
        
        # Generate calendar file
        ics_content = generate_ics_content(order)
        ics_bytes = ics_content.encode('utf-8')
        ics_file = BufferedInputFile(ics_bytes, filename=get_ics_filename(order))
        
        if notification_group_id:
            # Send to configured group
            try:
                await self.bot.send_message(int(notification_group_id), message, parse_mode="HTML")
                await self.bot.send_document(int(notification_group_id), ics_file)
            except Exception as e:
                print(f"Failed to notify group {notification_group_id}: {e}")
        else:
            # Fall back to STAFF_IDS if no group configured
            for staff_id in self.staff_ids:
                try:
                    await self.bot.send_message(staff_id, message, parse_mode="HTML")
                    await self.bot.send_document(staff_id, ics_file)
                except Exception as e:
                    print(f"Failed to notify staff {staff_id}: {e}")
    
    def _format_order_message(self, order: Order, customer_name: str = None) -> str:
        """Format order details for notification"""
        msg = f"🆕 <b>Новый заказ #{order.id}</b>\n\n"
        
        # Add customer name if available
        if customer_name:
            msg += f"👤 Заказчик: {customer_name}\n"
        
        if order.order_type == "cake":
            msg += f"🎂 Торт: {order.cake_flavor}\n"
            msg += f"⚖️ Вес: {order.weight_kg} кг\n"
        else:
            msg += f"🧁 Десерт: {order.cake_flavor}\n"
            msg += f"📦 Количество: {order.quantity} шт\n"
        
        msg += f"📍 Самовывоз: {order.pickup_location}\n"
        msg += f"🕐 Время: {order.issue_time}\n"
        msg += f"📞 Телефон: {order.customer_phone}\n"
        
        return msg
