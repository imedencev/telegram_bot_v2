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
from app.services.settings_service import SettingsService
from app.services.admin_service import AdminService

router = Router()

OWNER_ID = 747102879  # Owner's Telegram ID


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    """Show order statistics (owner and admins)"""
    admin_service = AdminService(session)
    if not await admin_service.is_admin_or_owner(message.from_user.id):
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
    """Show user order history"""
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
    
    keyboard_buttons = []
    for order in orders[:5]:
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
        
        ics_content = generate_ics_content(order)
        ics_bytes = ics_content.encode('utf-8')
        ics_file = BufferedInputFile(ics_bytes, filename=get_ics_filename(order))
        
        await callback.message.answer_document(
            ics_file,
            caption=f"📅 Календарь для заказа #{order.id}\n\nОткройте файл, чтобы добавить событие в ваш календарь."
        )
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка экспорта: {str(e)}")


@router.message(Command("set_notification_group"))
async def cmd_set_notification_group(message: Message, session: AsyncSession):
    """Set notification group for order alerts (owner only)"""
    if message.from_user.id != OWNER_ID:
        return
    
    settings_service = SettingsService(session)
    
    if message.chat.type in ["group", "supergroup"]:
        group_id = str(message.chat.id)
        await settings_service.set_setting("notification_group_id", group_id)
        
        # Get topic ID if message is in a topic
        topic_id = message.message_thread_id
        if topic_id:
            await settings_service.set_setting("notification_topic_id", str(topic_id))
            await message.answer(f"✅ Группа уведомлений установлена\n\nID группы: {group_id}\nID темы: {topic_id}\n\nВсе новые заказы будут отправляться в эту тему.")
        else:
            # Clear topic_id if set in general chat
            await settings_service.set_setting("notification_topic_id", "")
            await message.answer(f"✅ Группа уведомлений установлена\n\nID группы: {group_id}\n\nВсе новые заказы будут отправляться в общий чат группы.")
    else:
        await message.answer("❌ Эту команду нужно использовать в группе, куда должны приходить уведомления.\n\nДобавьте бота в группу и используйте команду там.")


@router.message(Command("add_admin"))
async def cmd_add_admin(message: Message, session: AsyncSession):
    """Add admin (owner only, reply to user message)"""
    if message.from_user.id != OWNER_ID:
        return
    
    if not message.reply_to_message:
        await message.answer("❌ Ответьте на сообщение пользователя, которого хотите сделать админом")
        return
    
    admin_service = AdminService(session)
    target_id = message.reply_to_message.from_user.id
    
    if admin_service.is_owner(target_id):
        await message.answer("❌ Владелец уже имеет все права")
        return
    
    try:
        await admin_service.add_admin(target_id, message.from_user.id)
        target_name = message.reply_to_message.from_user.full_name or "Пользователь"
        await message.answer(f"✅ Админ добавлен\n\n{target_name} (ID: {target_id})\n\nТеперь может использовать команды бота.")
    except ValueError as e:
        await message.answer(f"❌ {str(e)}")


@router.message(Command("remove_admin"))
async def cmd_remove_admin(message: Message, session: AsyncSession):
    """Remove admin (owner only)"""
    if message.from_user.id != OWNER_ID:
        return
    
    admin_service = AdminService(session)
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    else:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("❌ Ответьте на сообщение админа или укажите его ID\n\nПример: /remove_admin 123456789")
            return
        try:
            target_id = int(args[1])
        except ValueError:
            await message.answer("❌ Неверный формат ID")
            return
    
    try:
        await admin_service.remove_admin(target_id)
        await message.answer(f"✅ Админ удален\n\nID: {target_id}")
    except ValueError as e:
        await message.answer(f"❌ {str(e)}")


@router.message(Command("list_admins"))
async def cmd_list_admins(message: Message, session: AsyncSession):
    """List all admins (owner and admins can use)"""
    admin_service = AdminService(session)
    
    if not await admin_service.is_admin_or_owner(message.from_user.id):
        return
    
    admins = await admin_service.list_admins()
    
    if not admins:
        await message.answer(f"📋 Список админов пуст\n\nВладелец: {OWNER_ID}")
        return
    
    admins_text = f"📋 <b>Список админов</b>\n\n<b>Владелец:</b> {OWNER_ID}\n\n<b>Админы:</b>\n"
    
    for admin in admins:
        added_date = admin.added_at.strftime("%d.%m.%Y %H:%M")
        admins_text += f"\n• ID: {admin.telegram_id}\n  Добавлен: {added_date}\n  Кем: {admin.added_by}"
    
    await message.answer(admins_text)


@router.message(Command("orders_tomorrow"))
async def cmd_orders_tomorrow(message: Message, session: AsyncSession):
    """Show orders for tomorrow (owner and admins)"""
    admin_service = AdminService(session)
    if not await admin_service.is_admin_or_owner(message.from_user.id):
        return
    
    from datetime import datetime, timedelta
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
    
    # Get all confirmed orders
    result = await session.execute(
        select(Order)
        .where(Order.status.in_(["confirmed", "completed"]))
        .order_by(Order.issue_time)
    )
    orders = list(result.scalars().all())
    
    # Filter orders for tomorrow (issue_time contains tomorrow's date)
    tomorrow_orders = [o for o in orders if o.issue_time and tomorrow in o.issue_time]
    
    if not tomorrow_orders:
        await message.answer(f"📋 Заказов на завтра ({tomorrow}) нет")
        return
    
    orders_text = f"📋 <b>Заказы на завтра ({tomorrow})</b>\n\n"
    
    for order in tomorrow_orders:
        orders_text += f"🎂 <b>Заказ #{order.id}</b>\n"
        orders_text += f"🕐 {order.issue_time}\n"
        
        if order.customer_phone:
            orders_text += f"📞 {order.customer_phone}\n"
        
        # Show calendar notes if imported from calendar
        if order.calendar_notes:
            orders_text += f"📝 {order.calendar_notes}\n"
        else:
            # Show regular order details
            if order.cake_flavor:
                orders_text += f"🎂 {order.cake_flavor}\n"
            if order.weight_kg:
                orders_text += f"⚖️ {order.weight_kg} кг\n"
            if order.quantity:
                orders_text += f"🔢 {order.quantity} шт\n"
            if order.inscription:
                orders_text += f"✍️ Надпись: {order.inscription}\n"
            if order.pickup_location:
                orders_text += f"📍 {order.pickup_location}\n"
        
        orders_text += "\n"
    
    await message.answer(orders_text)


@router.message(Command("import_calendar"))
async def cmd_import_calendar(message: Message, session: AsyncSession):
    """Import orders from iPhone calendar .ics file (owner only)"""
    if message.from_user.id != OWNER_ID:
        return
    
    await message.answer(
        "📅 <b>Импорт из календаря</b>\n\n"
        "Отправьте .ics файл с вашего iPhone календаря.\n\n"
        "Бот создаст заказы из событий календаря:\n"
        "• Дата/время - из времени начала события\n"
        "• Телефон - найдёт в тексте события\n"
        "• Описание - сохранит весь текст события\n\n"
        "Отправьте файл ответом на это сообщение."
    )


@router.message(F.document)
async def handle_calendar_file(message: Message, session: AsyncSession):
    """Handle .ics file upload for calendar import"""
    if message.from_user.id != OWNER_ID:
        return
    
    # Check if it's an .ics file
    if not message.document.file_name.endswith('.ics'):
        return
    
    try:
        from icalendar import Calendar
        import re
        from datetime import datetime
        
        # Download file
        file = await message.bot.download(message.document.file_id)
        ics_content = file.read().decode('utf-8')
        
        # Parse calendar
        cal = Calendar.from_ical(ics_content)
        
        imported_count = 0
        failed_count = 0
        
        for component in cal.walk():
            if component.name == "VEVENT":
                try:
                    # Extract event data
                    summary = str(component.get('summary', ''))
                    description = str(component.get('description', ''))
                    dtstart = component.get('dtstart')
                    
                    if not dtstart:
                        failed_count += 1
                        continue
                    
                    # Get event start time
                    if hasattr(dtstart.dt, 'strftime'):
                        event_time = dtstart.dt.strftime("%d.%m.%Y %H:%M")
                    else:
                        event_time = str(dtstart.dt)
                    
                    # Combine summary and description
                    full_text = summary
                    if description and description != summary:
                        full_text += f"\n{description}"
                    
                    # Extract phone number using regex
                    phone_pattern = r'(\+?[78][\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2})'
                    phone_match = re.search(phone_pattern, full_text)
                    phone = phone_match.group(1) if phone_match else None
                    
                    # Create order
                    order = Order(
                        customer_telegram_id=message.from_user.id,
                        order_type="imported",
                        issue_time=event_time,
                        customer_phone=phone,
                        calendar_notes=full_text,
                        status="confirmed"
                    )
                    session.add(order)
                    imported_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    print(f"Failed to import event: {e}")
        
        await session.flush()
        
        result_text = f"✅ <b>Импорт завершён</b>\n\n"
        result_text += f"Импортировано: {imported_count} заказов\n"
        if failed_count > 0:
            result_text += f"Не удалось импортировать: {failed_count}\n"
        result_text += f"\nИспользуйте /orders_tomorrow для просмотра"
        
        await message.answer(result_text)
        
    except ImportError:
        await message.answer(
            "❌ Библиотека icalendar не установлена.\n\n"
            "Необходимо добавить в requirements.txt и пересобрать контейнер."
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка импорта: {str(e)}")
