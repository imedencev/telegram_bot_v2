"""
Calendar ICS export functionality for orders.
Allows users to add order pickup time to their calendar.
"""
from datetime import datetime, timedelta
import re
from typing import Optional


def parse_issue_time(issue_time_text: str) -> Optional[datetime]:
    """
    Parse issue_time text into datetime.
    Handles common formats like:
    - "завтра в 15:00"
    - "01.03 в 18:00"
    - "15:00"
    """
    if not issue_time_text:
        return None
    
    text = issue_time_text.lower().strip()
    now = datetime.now()
    
    # Try to extract time (HH:MM format)
    time_match = re.search(r'(\d{1,2}):(\d{2})', text)
    if not time_match:
        return None
    
    hour = int(time_match.group(1))
    minute = int(time_match.group(2))
    
    # Try to extract date (DD.MM format)
    date_match = re.search(r'(\d{1,2})\.(\d{1,2})', text)
    
    if date_match:
        day = int(date_match.group(1))
        month = int(date_match.group(2))
        year = now.year
        
        # If the month has passed, assume next year
        if month < now.month or (month == now.month and day < now.day):
            year += 1
        
        try:
            return datetime(year, month, day, hour, minute)
        except ValueError:
            pass
    
    # Check for "завтра" (tomorrow)
    if 'завтра' in text or 'tomorrow' in text:
        tomorrow = now + timedelta(days=1)
        return datetime(tomorrow.year, tomorrow.month, tomorrow.day, hour, minute)
    
    # Check for "сегодня" (today)
    if 'сегодня' in text or 'today' in text:
        return datetime(now.year, now.month, now.day, hour, minute)
    
    # Check for day of week abbreviations (????, ????, ????, ????, ????, ????, ????)
    weekday_map = {
        '????': 0, '??????????????????????': 0,
        '????': 1, '??????????????': 1,
        '????': 2, '??????????': 2, '??????????': 2,
        '????': 3, '??????????????': 3,
        '????': 4, '??????????????': 4, '??????????????': 4,
        '????': 5, '??????????????': 5, '??????????????': 5,
        '????': 6, '??????????????????????': 6
    }
    
    for day_name, target_weekday in weekday_map.items():
        if day_name in text:
            # Calculate days until target weekday
            current_weekday = now.weekday()
            days_ahead = target_weekday - current_weekday
            
            # If the day has passed this week, schedule for next week
            if days_ahead <= 0:
                days_ahead += 7
            
            target_date = now + timedelta(days=days_ahead)
            return datetime(target_date.year, target_date.month, target_date.day, hour, minute)
    
    # Default: assume tomorrow at specified time
    tomorrow = now + timedelta(days=1)
    return datetime(tomorrow.year, tomorrow.month, tomorrow.day, hour, minute)


def generate_ics_content(order) -> str:
    """
    Generate ICS (iCalendar) file content for an order.
    
    Args:
        order: Order object with details
    
    Returns:
        str: ICS file content
    """
    # Parse pickup time
    pickup_dt = parse_issue_time(order.issue_time)
    
    if not pickup_dt:
        # Default to tomorrow at noon if parsing fails
        pickup_dt = datetime.now() + timedelta(days=1)
        pickup_dt = pickup_dt.replace(hour=12, minute=0, second=0, microsecond=0)
    
    # End time: 30 minutes after start
    end_dt = pickup_dt + timedelta(minutes=30)
    
    # Format datetime for ICS (YYYYMMDDTHHMMSS)
    dtstart = pickup_dt.strftime('%Y%m%dT%H%M%S')
    dtend = end_dt.strftime('%Y%m%dT%H%M%S')
    dtstamp = datetime.now().strftime('%Y%m%dT%H%M%SZ')
    
    # Build event summary
    order_type_text = "Торт" if order.order_type == "cake" else "Десерт"
    summary = f"Забрать заказ #{order.id}: {order.cake_flavor or order_type_text}"
    
    # Build description
    description_parts = [f"Заказ #{order.id}"]
    
    if order.cake_flavor:
        description_parts.append(f"Позиция: {order.cake_flavor}")
    
    if order.order_type == "cake" and order.weight_kg:
        description_parts.append(f"Вес: {order.weight_kg} кг")
    elif order.order_type == "dessert" and order.quantity:
        description_parts.append(f"Количество: {order.quantity} шт")
    
    if order.customer_phone:
        description_parts.append(f"Телефон: {order.customer_phone}")
    
    if order.issue_time:
        description_parts.append(f"Время выдачи: {order.issue_time}")
    
    description = "\\n".join(description_parts)
    
    # Location
    location = order.pickup_location or "Кондитерская"
    
    # Generate ICS content
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Telegram Order Bot//Order #{order.id}//RU
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:order-{order.id}@telegram-bot
DTSTAMP:{dtstamp}
DTSTART:{dtstart}
DTEND:{dtend}
SUMMARY:{summary}
DESCRIPTION:{description}
LOCATION:{location}
STATUS:CONFIRMED
SEQUENCE:0
END:VEVENT
END:VCALENDAR"""
    
    return ics_content


def get_ics_filename(order) -> str:
    """Generate filename for ICS file"""
    return f"order_{order.id}_pickup.ics"
