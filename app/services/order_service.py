"""
Order Service - manages order creation and completion.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import Order, User


class OrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_order(self, telegram_id: int, order_type: str) -> Order:
        """Create new order"""
        order = Order(
            customer_telegram_id=telegram_id,
            order_type=order_type,
            status="draft"
        )
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)
        return order
    
    async def update_order(self, order_id: int, **kwargs):
        """Update order fields"""
        result = await self.session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one()
        
        for key, value in kwargs.items():
            if hasattr(order, key):
                setattr(order, key, value)
        
        await self.session.commit()
    
    async def complete_order(self, order_id: int) -> Order:
        """Mark order as completed"""
        result = await self.session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one()
        order.status = "completed"
        order.completed_at = datetime.now()
        await self.session.commit()
        return order
    
    async def get_order(self, order_id: int) -> Optional[Order]:
        """Get order by ID"""
        result = await self.session.execute(
            select(Order).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()
