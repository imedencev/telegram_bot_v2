"""Order handlers - complete version"""
import re
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.order_service import OrderService
from app.services.conversation_service import ConversationService
from app.services.notification_service import NotificationService
from app.services.catalog_service import CatalogService
from app.services.user_service import UserService
from app.services.response_variations import ResponseVariations
from app.states.order_flow import OrderState

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    conv_service = ConversationService(session)
    await conv_service.clear_state(message.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎂 Торт", callback_data="order_type:cake"),InlineKeyboardButton(text="🧁 Десерт", callback_data="order_type:dessert")]])
    greeting = ResponseVariations.get_greeting() + " Что хотите заказать?"
    await message.answer(greeting, reply_markup=keyboard)

@router.message(Command("revoke_consent"))
async def cmd_revoke_consent(message: Message, session: AsyncSession):
    user_service = UserService(session)
    await user_service.revoke_consent(message.from_user.id)
    await message.answer("Ваше согласие на обработку персональных данных отозвано.\nДля оформления новых заказов потребуется дать согласие снова.")

@router.callback_query(F.data.startswith("order_type:"))
async def callback_order_type(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    order_type = callback.data.split(":")[1]
    conv_service = ConversationService(session)
    order_service = OrderService(session)
    catalog_service = CatalogService(session)
    user_service = UserService(session)
    
    order = await order_service.create_order(callback.from_user.id, order_type)
    context = {"order_id": order.id, "order_type": order_type}
    
    # Check consent first
    has_consent = await user_service.has_consent(callback.from_user.id)
    if not has_consent:
        await conv_service.update_state(callback.from_user.id, OrderState.SHOW_PRIVACY_POLICY, context, order.id)
        policy_text = UserService.get_privacy_policy_text()
        keyboard = build_consent_keyboard()
        await callback.message.answer(policy_text, reply_markup=keyboard)
        return
    
    # Check name second
    has_name = await user_service.has_name(callback.from_user.id)
    if not has_name:
        await conv_service.update_state(callback.from_user.id, OrderState.ASK_NAME, context, order.id)
        await callback.message.answer("Как вас зовут?")
        return
    
    # Check phone third
    from sqlalchemy import select
    from app.models.database import User
    result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
    user = result.scalar_one_or_none()
    
    if not user or not user.phone:
        await conv_service.update_state(callback.from_user.id, OrderState.ASK_PHONE, context, order.id)
        await callback.message.answer("Ваш номер телефона для связи?")
        return
    
    # If has all three (consent, name, phone), show catalog
    await conv_service.update_state(callback.from_user.id, OrderState.SHOW_CATALOG, context, order.id)
    items = await catalog_service.get_items_by_type(order_type)
    if not items:
        await callback.message.answer("К сожалению, сейчас нет доступных позиций.")
        return
    keyboard_buttons = []
    for item in items[:10]:
        price_text = f" - {int(item.price)}₽" if item.price else ""
        keyboard_buttons.append([InlineKeyboardButton(text=f"{item.title}{price_text}", callback_data=f"catalog:{item.id}")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    type_name = "торты" if order_type == "cake" else "десерты"
    await callback.message.answer(f"Выберите {type_name}:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("catalog:"))
async def callback_catalog_item(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    item_id = int(callback.data.split(":")[1])
    conv_service = ConversationService(session)
    order_service = OrderService(session)
    catalog_service = CatalogService(session)
    item = await catalog_service.get_item_by_id(item_id)
    if not item:
        await callback.message.answer("Позиция не найдена.")
        return
    context = await conv_service.get_context(callback.from_user.id)
    order_id = context.get("order_id")
    order_type = context.get("order_type")
    await order_service.update_order(order_id, cake_flavor=item.title)
    context["cake_flavor"] = item.title
    context["item_id"] = item.id
    context["last_shown_cake"] = {"id": item.id, "title": item.title, "type": item.type}
    
    if item.image_link:
        try:
            await callback.message.answer_photo(photo=item.image_link, caption=f"Вы выбрали: {item.title}")
        except:
            await callback.message.answer(f"Вы выбрали: {item.title}")
    else:
        await callback.message.answer(f"Вы выбрали: {item.title}")
    if order_type == "cake":
        if "1.5кг к празднику" in item.title:
            await order_service.update_order(order_id, weight_kg=1.5, decor_type="berries")
            context["weight_kg"] = 1.5
            context["decor_type"] = "berries"
            await conv_service.update_state(callback.from_user.id, OrderState.ASK_INSCRIPTION, context)
            await callback.message.answer("Какую надпись сделать на торте?\n(Напишите текст или отправьте '-' если надпись не нужна)")
        elif "Бенто торт" in item.title:
            await order_service.update_order(order_id, weight_kg=0.3, decor_type="berries")
            context["weight_kg"] = 0.3
            context["decor_type"] = "berries"
            await conv_service.update_state(callback.from_user.id, OrderState.ASK_INSCRIPTION, context)
            await callback.message.answer("Какую надпись сделать на торте?\n(Напишите текст или отправьте '-' если надпись не нужна)")
        else:
            await conv_service.update_state(callback.from_user.id, OrderState.ASK_WEIGHT, context)
            await callback.message.answer("Какой вес торта? (минимум 2 кг, например: 2 или 2.5)")
    else:
        await conv_service.update_state(callback.from_user.id, OrderState.ASK_QUANTITY, context)
        await callback.message.answer("Сколько десертов? (например: 6)")

@router.callback_query(F.data.startswith("decor:"))
async def callback_decor_type(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    decor_type = callback.data.split(":")[1]
    conv_service = ConversationService(session)
    order_service = OrderService(session)
    context = await conv_service.get_context(callback.from_user.id)
    order_id = context.get("order_id")
    await order_service.update_order(order_id, decor_type=decor_type)
    context["decor_type"] = decor_type
    await conv_service.update_state(callback.from_user.id, OrderState.ASK_INSCRIPTION, context)
    await callback.message.answer("Какую надпись сделать на торте?\n(Напишите текст или отправьте '-' если надпись не нужна)")

@router.callback_query(F.data.startswith("addon:"))
async def callback_addon_toggle(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    addon_type = callback.data.split(":")[1]
    conv_service = ConversationService(session)
    order_service = OrderService(session)
    context = await conv_service.get_context(callback.from_user.id)
    order_id = context.get("order_id")
    addon_key = f"addon_{addon_type}"
    current_value = context.get(addon_key, False)
    new_value = not current_value
    context[addon_key] = new_value
    await order_service.update_order(order_id, **{addon_key: new_value})
    await conv_service.update_state(callback.from_user.id, OrderState.ASK_ADDONS, context)
    keyboard = build_addons_keyboard(context)
    await callback.message.edit_reply_markup(reply_markup=keyboard)

@router.callback_query(F.data == "addons_done")
async def callback_addons_done(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    conv_service = ConversationService(session)
    context = await conv_service.get_context(callback.from_user.id)
    await conv_service.update_state(callback.from_user.id, OrderState.ASK_PICKUP_LOCATION, context)
    keyboard = build_location_keyboard()
    await callback.message.answer("Где будете забирать заказ?", reply_markup=keyboard)

@router.callback_query(F.data.startswith("location:"))
async def callback_location(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    location = callback.data.split(":")[1]
    conv_service = ConversationService(session)
    order_service = OrderService(session)
    context = await conv_service.get_context(callback.from_user.id)
    order_id = context.get("order_id")
    await order_service.update_order(order_id, pickup_location=location)
    context["pickup_location"] = location
    await conv_service.update_state(callback.from_user.id, OrderState.ASK_ISSUE_TIME, context)
    await callback.message.answer("Когда нужен заказ?\nНапишите дату и время (например: завтра в 15:00 или 01.03 в 18:00)")

@router.callback_query(F.data.startswith("consent:"))
async def callback_consent(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    consent = callback.data.split(":")[1] == "yes"
    conv_service = ConversationService(session)
    user_service = UserService(session)
    catalog_service = CatalogService(session)
    context = await conv_service.get_context(callback.from_user.id)
    
    if consent:
        await user_service.give_consent(callback.from_user.id)
        
        # Check if user has name
        has_name = await user_service.has_name(callback.from_user.id)
        if not has_name:
            await conv_service.update_state(callback.from_user.id, OrderState.ASK_NAME, context)
            await callback.message.answer("Как вас зовут?")
            return
        
        # Check if user has phone
        from sqlalchemy import select
        from app.models.database import User
        result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = result.scalar_one_or_none()
        
        if not user or not user.phone:
            await conv_service.update_state(callback.from_user.id, OrderState.ASK_PHONE, context)
            await callback.message.answer("Ваш номер телефона для связи?")
            return
        
        # If has name and phone, show catalog
        order_type = context.get("order_type")
        await conv_service.update_state(callback.from_user.id, OrderState.SHOW_CATALOG, context)
        items = await catalog_service.get_items_by_type(order_type)
        if not items:
            await callback.message.answer("К сожалению, сейчас нет доступных позиций.")
            return
        keyboard_buttons = []
        for item in items[:10]:
            price_text = f" - {int(item.price)}₽" if item.price else ""
            keyboard_buttons.append([InlineKeyboardButton(text=f"{item.title}{price_text}", callback_data=f"catalog:{item.id}")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        type_name = "торты" if order_type == "cake" else "десерты"
        await callback.message.answer(f"Выберите {type_name}:", reply_markup=keyboard)
    else:
        await conv_service.clear_state(callback.from_user.id)
        await callback.message.answer("Без согласия на обработку персональных данных мы не можем принять заказ.\nЕсли передумаете, начните заново с /start")

@router.message(F.text)
async def handle_text_message(message: Message, session: AsyncSession, bot):
    conv_service = ConversationService(session)
    order_service = OrderService(session)
    user_service = UserService(session)
    catalog_service = CatalogService(session)
    state = await conv_service.get_or_create_state(message.from_user.id)
    current_state = OrderState(state.current_state)
    context = await conv_service.get_context(message.from_user.id)
    order_id = context.get("order_id")
    order_type = context.get("order_type")
    
    # Detect greetings and order keywords only when user is not in active order flow
    if not order_id:
        text_lower = message.text.lower().strip()
        greeting_words = ['привет', 'здравствуйте', 'здравствуй', 'здорово', 'приветствую', 'hi', 'hello', 'hey']
        
        if any(text_lower.startswith(word) or text_lower == word for word in greeting_words):
            await conv_service.clear_state(message.from_user.id)
            greeting = ResponseVariations.get_greeting() + " Что хотите заказать?"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🎂 Торт", callback_data="order_type:cake"),
                InlineKeyboardButton(text="🧁 Десерт", callback_data="order_type:dessert")
            ]])
            await message.answer(greeting, reply_markup=keyboard)
            return
        
        # Detect order keywords
        order_keywords = ['торт', 'тортик', 'десерт', 'заказ', 'заказать', 'хочу заказать', 'мой заказ']
        if any(keyword in text_lower for keyword in order_keywords):
            await conv_service.clear_state(message.from_user.id)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🎂 Торт", callback_data="order_type:cake"),
                InlineKeyboardButton(text="🧁 Десерт", callback_data="order_type:dessert")
            ]])
            await message.answer("Что хотите заказать?", reply_markup=keyboard)
            return
    
    # Detect "I want it" phrases
    text_lower = message.text.lower().strip()
    want_it_phrases = ['хочу его', 'хочу её', 'хочу этот', 'хочу эту', 'беру его', 'беру её', 'возьму его', 'возьму её']
    
    if any(phrase in text_lower for phrase in want_it_phrases):
        last_shown_cake = context.get("last_shown_cake")
        if last_shown_cake and order_id:
            await message.answer(f"Отлично! {ResponseVariations.get_confirmation()}")
            return
    
    if current_state == OrderState.ASK_NAME:
        full_name = message.text.strip()
        if len(full_name) < 2:
            await message.answer("Пожалуйста, введите ваше имя")
            return
        
        await user_service.update_name(message.from_user.id, full_name)
        
        # Check if user has phone
        from sqlalchemy import select
        from app.models.database import User
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        
        if not user or not user.phone:
            await conv_service.update_state(message.from_user.id, OrderState.ASK_PHONE, context)
            await message.answer("Ваш номер телефона для связи?")
            return
        
        # If has phone, show catalog
        order_type = context.get("order_type")
        await conv_service.update_state(message.from_user.id, OrderState.SHOW_CATALOG, context)
        items = await catalog_service.get_items_by_type(order_type)
        if not items:
            await message.answer("К сожалению, сейчас нет доступных позиций.")
            return
        keyboard_buttons = []
        for item in items[:10]:
            price_text = f" - {int(item.price)}₽" if item.price else ""
            keyboard_buttons.append([InlineKeyboardButton(text=f"{item.title}{price_text}", callback_data=f"catalog:{item.id}")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        type_name = "торты" if order_type == "cake" else "десерты"
        await message.answer(f"Спасибо, {full_name}! Выберите {type_name}:", reply_markup=keyboard)
    elif current_state == OrderState.ASK_PHONE:
        phone = message.text.strip()
        if not validate_phone(phone):
            await message.answer("Пожалуйста, введите корректный номер телефона\n(например: 89123456789 или +79123456789)")
            return
        
        await user_service.update_phone(message.from_user.id, phone)
        
        # Show catalog after phone is saved
        order_type = context.get("order_type")
        await conv_service.update_state(message.from_user.id, OrderState.SHOW_CATALOG, context)
        items = await catalog_service.get_items_by_type(order_type)
        if not items:
            await message.answer("К сожалению, сейчас нет доступных позиций.")
            return
        keyboard_buttons = []
        for item in items[:10]:
            price_text = f" - {int(item.price)}₽" if item.price else ""
            keyboard_buttons.append([InlineKeyboardButton(text=f"{item.title}{price_text}", callback_data=f"catalog:{item.id}")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        type_name = "торты" if order_type == "cake" else "десерты"
        await message.answer(f"Отлично! Выберите {type_name}:", reply_markup=keyboard)
    elif current_state == OrderState.ASK_WEIGHT:
        try:
            weight = float(message.text.replace(",", "."))
            if weight < 2 or weight > 20:
                await message.answer("Пожалуйста, укажите вес от 2 до 20 кг")
                return
            await order_service.update_order(order_id, weight_kg=weight, decor_type="berries")
            context["weight_kg"] = weight
            context["decor_type"] = "berries"
            await conv_service.update_state(message.from_user.id, OrderState.ASK_INSCRIPTION, context)
            await message.answer("Какую надпись сделать на торте?\n(Напишите текст или отправьте '-' если надпись не нужна)")
        except ValueError:
            await message.answer("Пожалуйста, введите число (например: 1.5 или 2)")
    elif current_state == OrderState.ASK_QUANTITY:
        try:
            quantity = int(message.text)
            if quantity <= 0 or quantity > 100:
                await message.answer("Пожалуйста, укажите количество от 1 до 100")
                return
            await order_service.update_order(order_id, quantity=quantity)
            context["quantity"] = quantity
            await conv_service.update_state(message.from_user.id, OrderState.ASK_PICKUP_LOCATION, context)
            keyboard = build_location_keyboard()
            await message.answer("Где будете забирать заказ?", reply_markup=keyboard)
        except ValueError:
            await message.answer("Пожалуйста, введите целое число (например: 6)")
    elif current_state == OrderState.ASK_INSCRIPTION:
        inscription = message.text if message.text != "-" else ""
        await order_service.update_order(order_id, inscription=inscription)
        context["inscription"] = inscription
        await conv_service.update_state(message.from_user.id, OrderState.ASK_ADDONS, context)
        keyboard = build_addons_keyboard(context)
        await message.answer("Выберите дополнения к торту:\n\n🎭 Топпер - 200₽\n🎆 Свеча-фейерверк - 150₽\n📸 Фотопечать - бесплатно", reply_markup=keyboard)
    elif current_state == OrderState.ASK_ISSUE_TIME:
        if len(message.text.strip()) < 3:
            await message.answer("Пожалуйста, укажите дату и время")
            return
        await order_service.update_order(order_id, issue_time=message.text)
        context["issue_time"] = message.text
        
        # Get phone from user record (it should always exist at this point)
        from sqlalchemy import select
        from app.models.database import User
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        
        if user and user.phone:
            await order_service.update_order(order_id, customer_phone=user.phone)
            order = await order_service.complete_order(order_id)
            notification_service = NotificationService(bot)
            await notification_service.notify_new_order(order)
            await conv_service.clear_state(message.from_user.id)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="📅 Добавить в календарь", callback_data=f"export_calendar:{order.id}")
            ]])
            await message.answer(ResponseVariations.get_order_completed(), reply_markup=keyboard)
        else:
            # This shouldn't happen, but handle it gracefully
            await message.answer("Произошла ошибка. Пожалуйста, начните заново с /start")
            await conv_service.clear_state(message.from_user.id)

def build_decor_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎨 Крем", callback_data="decor:cream")],[InlineKeyboardButton(text="🍫 Шоколад", callback_data="decor:chocolate")],[InlineKeyboardButton(text="🍓 Ягоды", callback_data="decor:berries")],[InlineKeyboardButton(text="🌸 Мастика", callback_data="decor:fondant")]])

def build_addons_keyboard(context: dict):
    topper = context.get("addon_topper", False)
    sparkler = context.get("addon_sparkler", False)
    photo = context.get("addon_photo_print", False)
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{'✅' if topper else '⬜'} Топпер (200₽)", callback_data="addon:topper")],[InlineKeyboardButton(text=f"{'✅' if sparkler else '⬜'} Свеча-фейерверк (150₽)", callback_data="addon:sparkler")],[InlineKeyboardButton(text=f"{'✅' if photo else '⬜'} Фотопечать (бесплатно)", callback_data="addon:photo_print")],[InlineKeyboardButton(text="✔️ Готово", callback_data="addons_done")]])

def build_location_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📍 Тольятти 11", callback_data="location:Тольятти 11")],[InlineKeyboardButton(text="📍 Циолковского 36", callback_data="location:Циолковского 36")]])

def build_consent_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Согласен", callback_data="consent:yes"),InlineKeyboardButton(text="❌ Не согласен", callback_data="consent:no")]])

def validate_phone(phone: str):
    phone = re.sub(r'[\s\-\(\)]', '', phone)
    pattern = r'^(\+7|8|7)?[0-9]{10}$'
    return bool(re.match(pattern, phone))
