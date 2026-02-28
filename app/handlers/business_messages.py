"""
Business messages handler - owner commands and support.
"""
import os
import sqlite3
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.database import Order, User, ConversationState

router = Router()

OWNER_ID = 747102879  # Owner's Telegram ID


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    """Show order statistics (owner only)"""
    if message.from_user.id != OWNER_ID:
        return
    
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)
    
    # Orders today
    result = await session.execute(
        select(func.count(Order.id), func.sum(Order.weight_kg))
        .where(and_(Order.created_at >= today_start, Order.status != "draft"))
    )
    today_count, today_weight = result.one()
    today_count = today_count or 0
    today_weight = today_weight or 0
    
    # Orders this week
    result = await session.execute(
        select(func.count(Order.id))
        .where(and_(Order.created_at >= week_start, Order.status != "draft"))
    )
    week_count = result.scalar() or 0
    
    # Orders this month
    result = await session.execute(
        select(func.count(Order.id))
        .where(and_(Order.created_at >= month_start, Order.status != "draft"))
    )
    month_count = result.scalar() or 0
    
    # Active orders
    result = await session.execute(
        select(func.count(Order.id))
        .where(Order.status.in_(["draft", "confirmed"]))
    )
    active_count = result.scalar() or 0
    
    # Top items this week
    result = await session.execute(
        select(Order.cake_flavor, func.count(Order.id).label("cnt"))
        .where(and_(
            Order.created_at >= week_start,
            Order.status != "draft",
            Order.cake_flavor.isnot(None)
        ))
        .group_by(Order.cake_flavor)
        .order_by(func.count(Order.id).desc())
        .limit(5)
    )
    top_items = result.all()
    
    stats_text = f"""📊 <b>Статистика заказов</b>

<b>Сегодня:</b>
• Заказов: {today_count}
• Вес тортов: {today_weight:.1f} кг

<b>За неделю:</b> {week_count} заказов
<b>За месяц:</b> {month_count} заказов
<b>Активных:</b> {active_count}

<b>Топ-5 за неделю:</b>"""
    
    if top_items:
        for item, count in top_items:
            stats_text += f"\n• {item}: {count}"
    else:
        stats_text += "\n(нет данных)"
    
    await message.answer(stats_text)


@router.message(Command("health"))
async def cmd_health(message: Message, session: AsyncSession):
    """Show bot health status (owner only)"""
    if message.from_user.id != OWNER_ID:
        return
    
    # Total orders
    result = await session.execute(select(func.count(Order.id)))
    total_orders = result.scalar() or 0
    
    # Active orders
    result = await session.execute(
        select(func.count(Order.id))
        .where(Order.status.in_(["draft", "confirmed"]))
    )
    active_orders = result.scalar() or 0
    
    # Stuck conversation states (older than 24 hours)
    day_ago = datetime.now() - timedelta(hours=24)
    result = await session.execute(
        select(func.count(ConversationState.id))
        .where(ConversationState.updated_at < day_ago)
    )
    stuck_states = result.scalar() or 0
    
    # Database size
    db_path = "/app/data/orders.db"
    try:
        db_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
        db_size_text = f"{db_size:.2f} MB"
    except:
        db_size_text = "unknown"
    
    health_text = f"""🏥 <b>Состояние бота</b>

<b>База данных:</b>
• Всего заказов: {total_orders}
• Активных: {active_orders}
• Застрявших состояний: {stuck_states}
• Размер БД: {db_size_text}

<b>Время проверки:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
"""
    
    if stuck_states > 0:
        health_text += "\n⚠️ Есть застрявшие состояния (старше 24ч)"
    else:
        health_text += "\n✅ Все системы в норме"
    
    await message.answer(health_text)


@router.message(Command("backup_now"))
async def cmd_backup_now(message: Message):
    """Create immediate database backup (owner only)"""
    if message.from_user.id != OWNER_ID:
        return
    
    try:
        source_db = "/app/data/orders.db"
        backup_dir = "/app/data/backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/orders_manual_{timestamp}.db"
        
        # Use SQLite backup API for safe backup
        source_conn = sqlite3.connect(source_db)
        backup_conn = sqlite3.connect(backup_file)
        source_conn.backup(backup_conn)
        source_conn.close()
        backup_conn.close()
        
        backup_size = os.path.getsize(backup_file) / (1024 * 1024)  # MB
        
        await message.answer(
            f"✅ Бэкап создан успешно\n\n"
            f"Файл: orders_manual_{timestamp}.db\n"
            f"Размер: {backup_size:.2f} MB"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка создания бэкапа: {str(e)}")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Show help message"""
    help_text = """🤖 <b>Помощь по боту</b>

<b>Команды:</b>
/start - Начать новый заказ
/help - Показать эту справку
/revoke_consent - Отозвать согласие на обработку данных

<b>Как заказать:</b>
1. Нажмите /start
2. Выберите торт или десерт
3. Выберите позицию из каталога
4. Ответьте на вопросы бота
5. Подтвердите заказ

<b>Вопросы?</b>
Напишите нам: @imedencev
"""
    await message.answer(help_text)


@router.message(Command("support"))
async def cmd_support(message: Message):
    """Contact support"""
    support_text = """📞 <b>Связь с нами</b>

Если у вас есть вопросы или нужна помощь:

• Telegram: @imedencev
• Телефон: +7 (XXX) XXX-XX-XX

Мы работаем с 08:00 до 20:00
"""
    await message.answer(support_text)
