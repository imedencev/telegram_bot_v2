"""
Response variations - human-like varied responses for V2 bot.
"""
import random
from datetime import datetime


class ResponseVariations:
    """Provides varied, human-like responses"""
    
    # Time-based greetings
    MORNING_GREETINGS = [
        "Доброе утро! ☀️",
        "Привет! Как начинается день?",
        "Здравствуйте! Чем могу помочь?",
    ]
    
    AFTERNOON_GREETINGS = [
        "Добрый день! 👋",
        "Привет! Как дела?",
        "Здравствуйте! Рад вас видеть!",
    ]
    
    EVENING_GREETINGS = [
        "Добрый вечер! 🌙",
        "Привет! Как прошёл день?",
        "Здравствуйте! Чем могу помочь?",
    ]
    
    # Confirmation messages
    CONFIRMATIONS = [
        "Отлично! ✅",
        "Понял вас! 👍",
        "Записал! ✓",
        "Хорошо! 👌",
        "Принято! ✅",
    ]
    
    # Thanks responses
    THANKS_RESPONSES = [
        "Пожалуйста! 😊",
        "Всегда рад помочь!",
        "Обращайтесь! 👋",
        "Рад был помочь!",
    ]
    
    # Apology responses
    APOLOGY_RESPONSES = [
        "Всё в порядке! 😊",
        "Ничего страшного!",
        "Не переживайте!",
        "Всё хорошо! 👍",
    ]
    
    # Order completion messages
    ORDER_COMPLETED = [
        "✅ Отлично! Ваш заказ принят.\nМы свяжемся с вами для подтверждения.",
        "✅ Спасибо! Заказ оформлен.\nСкоро с вами свяжемся!",
        "✅ Замечательно! Заказ получен.\nОжидайте звонка для подтверждения.",
    ]
    
    @staticmethod
    def get_greeting():
        """Get time-appropriate greeting"""
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            return random.choice(ResponseVariations.MORNING_GREETINGS)
        elif 12 <= hour < 18:
            return random.choice(ResponseVariations.AFTERNOON_GREETINGS)
        else:
            return random.choice(ResponseVariations.EVENING_GREETINGS)
    
    @staticmethod
    def get_confirmation():
        """Get random confirmation message"""
        return random.choice(ResponseVariations.CONFIRMATIONS)
    
    @staticmethod
    def get_thanks_response():
        """Get random thanks response"""
        return random.choice(ResponseVariations.THANKS_RESPONSES)
    
    @staticmethod
    def get_apology_response():
        """Get random apology response"""
        return random.choice(ResponseVariations.APOLOGY_RESPONSES)
    
    @staticmethod
    def get_order_completed():
        """Get random order completion message"""
        return random.choice(ResponseVariations.ORDER_COMPLETED)
    
    @staticmethod
    def detect_thanks(text: str) -> bool:
        """Detect if message contains thanks"""
        thanks_words = ['спасибо', 'благодарю', 'thanks', 'thx']
        text_lower = text.lower()
        return any(word in text_lower for word in thanks_words)
    
    @staticmethod
    def detect_apology(text: str) -> bool:
        """Detect if message contains apology"""
        apology_words = ['извините', 'прости', 'sorry', 'простите']
        text_lower = text.lower()
        return any(word in text_lower for word in apology_words)
