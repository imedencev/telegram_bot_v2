"""
Business messages handler - owner commands and support.
"""
import os
import sqlite3
from datetime import datetime, timedelta
from io import BytesIO
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.database import Order, User, ConversationState
from app.services.calendar_export import generate_ics_content, get_ics_filename

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


@router.message(Command("my_orders"))
async def cmd_my_orders(message: Message, session: AsyncSession):
    """Show user's order history"""
    result = await session.execute(
        select(Order)
        .where(and_(
            Order.customer_telegram_id == message.from_user.id,
            Order.status != "draft"
        ))
        .order_by(Order.created_at.desc())
        .limit(10)
    )
    orders = list(result.scalars().all())
    
    if not orders:
        await message.answer("📋 У вас пока нет завершённых заказов.\n\nНачните новый заказ: /start")
        return
    
    orders_text = f"📋 <b>Ваши заказы</b> (последние {len(orders)}):\n\n"
    
    for i, order in enumerate(orders, 1):
        status_emoji = "✅" if order.status == "completed" else "⏳"
        order_type_emoji = "🎂" if order.order_type == "cake" else "🧁"
        
        orders_text += f"{status_emoji} <b>Заказ #{order.id}</b>\n"
        orders_text += f"{order_type_emoji} {order.cake_flavor or 'Не указано'}\n"
        
        if order.order_type == "cake" and order.weight_kg:
            orders_text += f"⚖️ Вес: {order.weight_kg} кг\n"
        elif order.order_type == "dessert" and order.quantity:
            orders_text += f"🔢 Количество: {order.quantity} шт\n"
        
        if order.pickup_location:
            orders_text += f"📍 {order.pickup_location}\n"
        
        if order.issue_time:
            orders_text += f"🕐 {order.issue_time}\n"
        
        if order.created_at:
            orders_text += f"📅 Заказ от: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        
        orders_text += "\n"
    
    # Add calendar export buttons for orders
    keyboard_buttons = []
    for order in orders[:5]:  # Show buttons for first 5 orders
        keyboard_buttons.append([InlineKeyboardButton(
            text=f"📅 Календарь для заказа #{order.id}",
            callback_data=f"export_calendar:{order.id}"
        )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None
    
    orders_text += "Новый заказ: /start"
    
    await message.answer(orders_text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("export_calendar:"))
async def callback_export_calendar(callback: CallbackQuery, session: AsyncSession):
    """Export order to calendar (ICS file)"""
    await callback.answer()
    
    try:
        order_id = int(callback.data.split(":")[1])
        
        # Get order from database
        result = await session.execute(
            select(Order).where(and_(
                Order.id == order_id,
                Order.customer_telegram_id == callback.from_user.id
            ))
        )
        order = result.scalar_one_or_none()
        
        if not order:
            await callback.message.answer("❌ Заказ не найден")
            return
        
        # Generate ICS file
        ics_content = generate_ics_content(order)
        ics_bytes = ics_content.encode('utf-8')
        ics_file = BufferedInputFile(ics_bytes, filename=get_ics_filename(order))
        
        # Send ICS file
        await callback.message.answer_document(
            ics_file,
            caption=f"📅 Календарь для заказа #{order.id}\n\nОткройте файл, чтобы добавить событие в ваш календарь."
        )
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка экспорта: {str(e)}")
