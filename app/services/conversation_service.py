"""
Conversation Service - manages conversation state and order flow.
"""
import json
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import ConversationState, Order
from app.states.order_flow import OrderState, OrderFlowStateMachine


class ConversationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.state_machine = OrderFlowStateMachine()
    
    async def get_or_create_state(self, telegram_id: int) -> ConversationState:
        """Get existing conversation state or create new one"""
        result = await self.session.execute(
            select(ConversationState).where(
                ConversationState.telegram_user_id == telegram_id
            )
        )
        state = result.scalar_one_or_none()
        
        if not state:
            state = ConversationState(
                telegram_user_id=telegram_id,
                current_state=OrderState.START.value,
                context_data=json.dumps({})
            )
            self.session.add(state)
            await self.session.commit()
        
        return state
    
    async def update_state(self, telegram_id: int, new_state: OrderState, 
                          context: Dict[str, Any], order_id: Optional[int] = None):
        """Update conversation state"""
        state = await self.get_or_create_state(telegram_id)
        state.current_state = new_state.value
        state.context_data = json.dumps(context)
        if order_id:
            state.active_order_id = order_id
        await self.session.commit()
    
    async def get_context(self, telegram_id: int) -> Dict[str, Any]:
        """Get conversation context"""
        state = await self.get_or_create_state(telegram_id)
        return json.loads(state.context_data) if state.context_data else {}
    
    async def clear_state(self, telegram_id: int):
        """Clear conversation state"""
        result = await self.session.execute(
            select(ConversationState).where(
                ConversationState.telegram_user_id == telegram_id
            )
        )
        state = result.scalar_one_or_none()
        if state:
            await self.session.delete(state)
            await self.session.commit()
