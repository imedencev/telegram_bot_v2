"""
Notification Service - notifies staff about new orders.
"""
import os
from aiogram import Bot
from app.models.database import Order
from app.services.calendar_export import generate_ics_content, get_ics_filename
from aiogram.types import BufferedInputFile


class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.staff_ids = [int(id.strip()) for id in os.getenv("STAFF_IDS", "").split(",") if id.strip()]
    
    async def notify_new_order(self, order: Order):
        """Send notification to staff about new order"""
        message = self._format_order_message(order)
        
        # Generate calendar file
        ics_content = generate_ics_content(order)
        ics_bytes = ics_content.encode('utf-8')
        ics_file = BufferedInputFile(ics_bytes, filename=get_ics_filename(order))
        
        for staff_id in self.staff_ids:
            try:
                await self.bot.send_message(staff_id, message, parse_mode="HTML")
                # Send calendar file to staff
                await self.bot.send_document(staff_id, ics_file)
            except Exception as e:
                print(f"Failed to notify staff {staff_id}: {e}")
    
    def _format_order_message(self, order: Order) -> str:
        """Format order details for notification"""
        msg = f"🆕 <b>Новый заказ #{order.id}</b>\n\n"
        
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
